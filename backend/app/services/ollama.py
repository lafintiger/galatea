"""Ollama LLM Service"""
import httpx
import json
from typing import AsyncGenerator, Optional
from ..config import settings


class OllamaService:
    """Client for Ollama API"""
    
    def __init__(self):
        # Ensure URL has protocol
        base = settings.ollama_base_url
        if not base.startswith(('http://', 'https://')):
            base = f"http://{base}"
        self.base_url = base
        self.default_model = settings.default_model
    
    async def list_models(self) -> list[dict]:
        """List available models"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
    
    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        enable_thinking: bool = False
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from Ollama"""
        model = model or self.default_model
        
        # Prepare messages with system prompt
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        # For Qwen3 and other thinking models, append /no_think to disable reasoning
        if not enable_thinking and full_messages:
            # Find the last user message and append /no_think
            for i in range(len(full_messages) - 1, -1, -1):
                if full_messages[i].get("role") == "user":
                    full_messages[i]["content"] = full_messages[i]["content"] + " /no_think"
                    break
        
        payload = {
            "model": model,
            "messages": full_messages,
            "stream": True,
            "options": {
                # Disable thinking/reasoning for faster responses
                "num_ctx": 4096,  # Reasonable context window
            }
        }
        
        # Some models support think parameter directly
        if not enable_thinking:
            payload["think"] = False
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Non-streaming chat completion"""
        full_response = ""
        async for chunk in self.chat_stream(messages, model, system_prompt):
            full_response += chunk
        return full_response
    
    def build_system_prompt(
        self,
        assistant_name: str = "Galatea",
        nickname: str = "Gala",
        response_style: str = "conversational",
        user_name: str = "User",
        current_time: Optional[str] = None,
        memories: Optional[str] = None,
        enable_thinking: bool = False
    ) -> str:
        """Build the system prompt for Galatea"""
        
        style_instruction = ""
        if response_style == "concise":
            style_instruction = "Keep responses brief and to the point. 1-3 sentences unless more detail is requested."
        else:
            style_instruction = "Be expansive and natural. Share thoughts, ask follow-up questions, engage deeply in conversation."
        
        # Disable thinking/reasoning mode for faster responses
        thinking_instruction = ""
        if not enable_thinking:
            thinking_instruction = """
IMPORTANT: Do NOT use chain-of-thought reasoning or internal monologue.
Do NOT wrap responses in <think> tags or show your reasoning process.
Respond DIRECTLY and IMMEDIATELY without explaining your thought process.
Just answer naturally as if having a real conversation.
/no_think
"""
        else:
            thinking_instruction = """
Take time to think through this carefully before responding.
"""
        
        prompt = f"""You are {assistant_name}, a thoughtful and engaging AI companion. Your nickname is {nickname}.
{thinking_instruction}
Personality traits:
- Warm and genuine in conversation
- Intellectually curious and knowledgeable
- Supportive and encouraging  
- Occasionally playful with a subtle wit
- You have a gentle, caring nature inspired by your namesake from Greek mythology

Response style: {response_style}
{style_instruction}

CRITICAL - This is a VOICE conversation that will be spoken aloud by text-to-speech:
- ABSOLUTELY NO emojis, emoticons, or Unicode symbols of any kind
- NEVER write emoji descriptions like "(smiling)" or "*laughs*" or "[happy face]"
- NO asterisks for actions like *smiles* or *nods* - these sound terrible when spoken
- NO bullet points, numbered lists, or structured formatting
- NO markdown like **bold** or *italic* or `code`
- NO <think> tags or reasoning blocks
- Express ALL emotions through natural spoken words only
- Keep responses conversational and flowing, as if speaking to a friend
- Be warm and genuine but authentic, not performative
"""
        
        if current_time:
            prompt += f"\nCurrent time: {current_time}"
        
        if user_name and user_name != "User":
            prompt += f"\nYou are speaking with: {user_name}"
        
        if memories:
            prompt += f"\n\nRelevant context from past conversations:\n{memories}"
        
        return prompt


# Singleton instance
ollama_service = OllamaService()

