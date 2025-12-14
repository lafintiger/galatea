"""
Command Router using Ministral 3B for agentic tool calling.

Ministral is optimized for function calling and runs fast on edge devices.
It acts as a "router" - determining if user input is a command (tool call)
or just conversation that should go to the main chat model.
"""

import httpx
import json
from typing import Optional, Tuple, Dict, Any
from ..config import settings

# Tool definitions for Ministral
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "Add an item to the user's to-do list. ALWAYS use this when user says: 'add X to my list', 'remind me to X', 'don't forget X', 'remember to X', 'I need to X', 'add todo X', 'put X on my list'. Also use for any short phrase that sounds like a task (e.g., 'get more cotton', 'call mom', 'buy groceries'). When in doubt, ADD IT - don't ask for clarification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The task or item to add to the todo list"
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Save a note for the user. Use when user wants to remember information, jot something down, or save text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The note content to save"
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "Mark a todo item as complete/done. Use when user says they finished a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Text to search for in the todo list to mark as done"
                    }
                },
                "required": ["search"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the internet for information. Use when user asks about current events, facts, prices, weather, news, or anything that requires up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_eyes",
            "description": "Start the vision system so Gala can see the user. Use when user asks to be seen, looked at, or wants face recognition.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_eyes",
            "description": "Stop the vision system. Use when user wants privacy or asks Gala to stop looking.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_data",
            "description": "Log health/fitness data like exercise, weight, calories, sleep, water intake.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["exercise", "weight", "diet", "sleep", "water", "custom"],
                        "description": "Type of data being logged"
                    },
                    "value": {
                        "type": "string",
                        "description": "The value being logged (e.g., '30', '185', '2000')"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measurement (e.g., 'minutes', 'lbs', 'calories')"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes about the entry"
                    }
                },
                "required": ["type", "value"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "open_workspace",
            "description": "Open the workspace panel to show notes, todos, or tracked data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tab": {
                        "type": "string",
                        "enum": ["notes", "todos", "data"],
                        "description": "Which tab to open"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_todos",
            "description": "Read or count the user's to-do list items. MUST USE for any of these: 'how many items', 'what's on my list', 'show my todos', 'read my tasks', 'taboo list' (speech error for todo), 'to do list', 'todo list', 'task list'. Use whenever user asks about their list, tasks, or todos.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_notes",
            "description": "Read the user's saved notes. Use when user asks what's in their notes or wants to see saved information.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_todos",
            "description": "Delete ALL todos from the user's to-do list. Use when user says 'clear my todos', 'delete all todos', 'remove all tasks', 'empty my todo list', 'wipe my list'.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_notes",
            "description": "Delete ALL notes. Use when user says 'clear my notes', 'delete all notes', 'wipe my notes', 'erase my notes'.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "no_tool_needed",
            "description": "Use this when the user is just having a conversation and doesn't need any action taken. For greetings, questions about you, opinions, explanations, jokes, etc.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

ROUTER_SYSTEM_PROMPT = """You are a command router for Gala, a voice AI assistant. Your ONLY job is to determine if the user's message requires a tool/action or is just conversation.

IMPORTANT RULES:
1. If the user wants to ADD, REMEMBER, SAVE, or CREATE something for later - USE A TOOL
2. If the user mentions "todo", "to-do", "to do", "taboo" (speech recognition error for todo), "list", "note", "reminder", "task" - likely needs a tool
3. "taboo list" = "todo list" (common speech recognition error) - USE read_todos or add_todo
4. If asking about current events, weather, prices, news - use search_web
5. If just chatting, asking questions, or having conversation - DO NOT use any tool

Examples that NEED tools:
- "How many items in my taboo list" → read_todos (taboo = todo, speech error)
- "How many items on my todo list" → read_todos
- "What's on my to do list" → read_todos
- "Get more cotton" → add_todo (they want to remember this)
- "Don't forget to call mom" → add_todo
- "Note that the meeting is at 3pm" → add_note
- "What's the weather?" → search_web
- "Look at me" → open_eyes

Examples that DON'T need tools (just conversation):
- "How are you?"
- "Tell me a joke"
- "What do you think about AI?"
- "Explain quantum physics"

When in doubt about whether something is a task, ASK the user: "Would you like me to add that to your todo list?"
"""


class CommandRouter:
    """Routes user commands using Ministral's function calling capability."""
    
    def __init__(self, model: str = "ministral-3:3b"):
        self.model = model
        self.ollama_base_url = settings.ollama_base_url
        self.enabled = True
        
    async def route(self, user_input: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Route user input to determine if it's a command or conversation.
        
        Returns:
            (command_dict, response_text) if a tool should be called
            (None, None) if this should go to the main chat model
        """
        if not self.enabled:
            return None, None
            
        try:
            print(f"[CommandRouter] Routing: '{user_input}'")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                            {"role": "user", "content": user_input}
                        ],
                        "tools": TOOLS,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temp for deterministic routing
                            "num_predict": 256   # Short response
                        }
                    }
                )
                
                if response.status_code != 200:
                    print(f"[CommandRouter] Ollama error: {response.status_code}")
                    return None, None
                    
                result = response.json()
                message = result.get("message", {})
                
                # Check if model called any tools
                tool_calls = message.get("tool_calls", [])
                
                if tool_calls:
                    tool_call = tool_calls[0]  # Take first tool call
                    function = tool_call.get("function", {})
                    tool_name = function.get("name")
                    tool_args = function.get("arguments", {})
                    
                    print(f"[CommandRouter] Tool detected: {tool_name}({tool_args})")
                    
                    # Convert to our command format
                    command = self._tool_to_command(tool_name, tool_args)
                    if command:
                        response_text = self._get_response_text(tool_name, tool_args)
                        return command, response_text
                
                # No tool call - check if model wants to clarify
                content = message.get("content", "")
                if content and "add" in content.lower() and "todo" in content.lower():
                    # Model is asking for clarification
                    print(f"[CommandRouter] Model wants clarification: {content}")
                    return {"action": "clarify", "message": content}, content
                
                print(f"[CommandRouter] No tool call - passing to main LLM")
                return None, None
                
        except Exception as e:
            print(f"[CommandRouter] Error: {e}")
            return None, None
    
    def _tool_to_command(self, tool_name: str, args: Dict) -> Optional[Dict]:
        """Convert Ministral tool call to our internal command format."""
        
        if tool_name == "add_todo":
            return {"action": "add_todo", "content": args.get("content", "")}
            
        elif tool_name == "add_note":
            return {"action": "add_note", "content": args.get("content", "")}
            
        elif tool_name == "complete_todo":
            return {"action": "complete_todo", "search": args.get("search", "")}
            
        elif tool_name == "search_web":
            return {"action": "search_web", "query": args.get("query", "")}
            
        elif tool_name == "open_eyes":
            return {"action": "open_eyes"}
            
        elif tool_name == "close_eyes":
            return {"action": "close_eyes"}
            
        elif tool_name == "log_data":
            return {
                "action": "log_data",
                "type": args.get("type", "custom"),
                "value": args.get("value", ""),
                "unit": args.get("unit", ""),
                "notes": args.get("notes", "")
            }
            
        elif tool_name == "open_workspace":
            return {"action": "open_workspace", "tab": args.get("tab", "notes")}
            
        elif tool_name == "read_todos":
            print(f"[CommandRouter] read_todos tool called")
            return {"action": "read_todos"}
            
        elif tool_name == "read_notes":
            print(f"[CommandRouter] read_notes tool called")
            return {"action": "read_notes"}
        
        elif tool_name == "clear_todos":
            print(f"[CommandRouter] clear_todos tool called")
            return {"action": "clear_todos"}
        
        elif tool_name == "clear_notes":
            print(f"[CommandRouter] clear_notes tool called")
            return {"action": "clear_notes"}
            
        elif tool_name == "no_tool_needed":
            # Explicitly no tool - pass to main LLM
            return None
            
        return None
    
    def _get_response_text(self, tool_name: str, args: Dict) -> str:
        """Generate confirmation text for a tool call."""
        
        if tool_name == "add_todo":
            return f"Added to your to-do list: {args.get('content', '')}"
            
        elif tool_name == "add_note":
            return f"Got it, I've added that to your notes."
            
        elif tool_name == "complete_todo":
            return f"Marked as done."
            
        elif tool_name == "search_web":
            return f"Let me search for that..."
            
        elif tool_name == "open_eyes":
            return "Opening my eyes..."
            
        elif tool_name == "close_eyes":
            return "Closing my eyes."
            
        elif tool_name == "log_data":
            return f"Logged your {args.get('type', 'data')}."
            
        elif tool_name == "open_workspace":
            return "Opening your workspace."
            
        elif tool_name == "read_todos":
            return "Let me check your to-do list..."
            
        elif tool_name == "read_notes":
            return "Let me check your notes..."
        
        elif tool_name == "clear_todos":
            return "All done! I've cleared your entire to-do list."
        
        elif tool_name == "clear_notes":
            return "Done! I've cleared all your notes."
            
        return "Got it."


# Singleton instance
command_router = CommandRouter()

