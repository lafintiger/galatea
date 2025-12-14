"""Intent detection for user input.

Detects search requests, vision commands, workspace commands, etc.
This provides regex-based fallback when the LLM router doesn't match.
"""
import re
from typing import Optional

from .logging import get_logger

logger = get_logger(__name__)


def detect_search_intent(text: str) -> tuple[bool, str]:
    """Detect if the user is asking for a web search and extract the query.
    
    This detects both explicit search requests AND questions that need 
    real-time information (weather, news, prices, etc.)
    
    Args:
        text: User input text
        
    Returns:
        (is_search_request, extracted_query)
    """
    text_lower = text.lower().strip()
    
    # Topics that ALWAYS need real-time data (use full question as query)
    realtime_topics = [
        # Weather
        r"weather",
        r"temperature",
        r"forecast",
        r"rain(?:ing)?",
        r"snow(?:ing)?",
        r"humid",
        # News & Current Events  
        r"latest news",
        r"current (?:news|events)",
        r"recent (?:news|developments)",
        r"what(?:'s| is) happening",
        r"breaking news",
        r"today(?:'s)? news",
        r"this week",
        r"this month",
        # Financial/Prices
        r"stock price",
        r"share price", 
        r"how much (?:does|is|are|do)",
        r"price of",
        r"cost of",
        r"bitcoin|crypto|ethereum",
        r"market",
        # Sports
        r"(?:game|match) score",
        r"who won",
        r"standings",
        r"playoffs",
        r"championship",
        # Time-sensitive
        r"release date",
        r"when (?:does|is|will|did)",
        r"hours of",
        r"open(?:ing)? hours",
        r"schedule",
        r"next (?:week|month|year)",
        # Product/Tech info
        r"specs",
        r"specifications",
        r"features of",
        r"review(?:s)? (?:of|for)",
        r"compare|comparison",
        r"best (?:\w+ )?(?:for|to|in)",
        r"top \d+",
        r"recommended",
        # Location/Business
        r"near(?:by| me)",
        r"directions to",
        r"address of",
        r"phone number",
        r"contact",
        # Events/Entertainment
        r"movie(?:s)?",
        r"playing (?:tonight|today|now)",
        r"showing (?:tonight|today|now)",
        r"concert(?:s)?",
        r"event(?:s)?",
        r"ticket(?:s)?",
        # Research queries
        r"what is (?:a |an |the )?(?:\w+ ){0,3}(?:and|or) how",
        r"explain (?:what|how|why)",
        r"definition of",
        r"meaning of",
    ]
    
    for topic in realtime_topics:
        if re.search(topic, text_lower):
            # Use the full question as search query
            query = text.rstrip('?.!').strip()
            if len(query) > 5:
                logger.debug(f"Auto-search triggered by realtime topic: {topic}")
                return True, query
    
    # Patterns that indicate explicit search request
    search_patterns = [
        # Direct search commands
        (r"^(?:please\s+)?(?:can you\s+)?(?:web\s+)?search\s+(?:for\s+)?(?:the\s+)?(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^(?:please\s+)?look\s+up\s+(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^(?:please\s+)?find\s+(?:out\s+)?(?:about\s+)?(?:information\s+(?:on|about)\s+)?(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^(?:please\s+)?google\s+(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^(?:please\s+)?check\s+(?:the\s+)?(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^what(?:'s| is) the latest (?:news |info(?:rmation)? )?(?:on|about) (.+?)[\?\.]?$", 1),
        
        # "What is X" questions about real things (not conversational)
        (r"^what(?:'s| is| are) (?:the )?(?:current |latest |new )(.+?)[\?\.]?$", 1),
        
        # Explicit search triggers
        (r"^search[:\s]+(.+)$", 1),
        (r"^look up[:\s]+(.+)$", 1),
    ]
    
    for pattern, group in search_patterns:
        match = re.match(pattern, text_lower)
        if match:
            if group == 0:
                query = text  # Use full text
            else:
                query = match.group(group).strip()
            # Clean up query
            query = re.sub(r'^(the|a|an)\s+', '', query)
            query = query.rstrip('?.!')
            if len(query) > 3:  # Minimum query length
                return True, query
    
    # Check for keywords that strongly suggest search need
    search_keywords = [
        'search for', 'look up', 'find out', 'google', 
        'what is the latest', 'current news', 'recent news',
        'search the web', 'web search', 'check the',
        'look into', 'research'
    ]
    
    for keyword in search_keywords:
        if keyword in text_lower:
            # Extract query after the keyword
            idx = text_lower.find(keyword)
            query = text[idx + len(keyword):].strip()
            query = re.sub(r'^(for|about|on)\s+', '', query, flags=re.IGNORECASE)
            query = query.rstrip('?.!')
            if len(query) > 3:
                return True, query
    
    return False, ""


def detect_vision_command(text: str) -> tuple[Optional[str], str]:
    """Detect if the user is asking to open/close Gala's eyes.
    
    Args:
        text: User input text
        
    Returns:
        (command, response_text) where command is 'open', 'close', or None
    """
    text_lower = text.lower().strip()
    
    # Open eyes patterns
    open_patterns = [
        r"open\s+(?:your\s+)?eyes",
        r"(?:can you\s+)?see\s+me",
        r"look\s+at\s+me",
        r"(?:start|enable|turn on)\s+(?:your\s+)?(?:vision|eyes|camera|webcam)",
        r"(?:i\s+)?want\s+you\s+to\s+see",
        r"watch\s+me",
        r"eyes\s+open",
    ]
    
    for pattern in open_patterns:
        if re.search(pattern, text_lower):
            return "open", "Opening my eyes... I can see you now."
    
    # Close eyes patterns
    close_patterns = [
        r"close\s+(?:your\s+)?eyes",
        r"(?:stop|disable|turn off)\s+(?:your\s+)?(?:vision|eyes|camera|webcam)",
        r"(?:don't|do not)\s+(?:look|watch|see)",
        r"(?:stop\s+)?look(?:ing)?\s+at\s+me",
        r"eyes\s+(?:closed|shut)",
        r"shut\s+(?:your\s+)?eyes",
        r"(?:i\s+)?(?:don't\s+)?want\s+(?:you\s+to\s+)?(?:stop\s+)?see(?:ing)?",
    ]
    
    for pattern in close_patterns:
        if re.search(pattern, text_lower):
            return "close", "Closing my eyes. I can no longer see."
    
    return None, ""


def detect_workspace_command(text: str) -> tuple[Optional[dict], str]:
    """Detect if the user is making a workspace command (notes, todos, data).
    
    Args:
        text: User input text
        
    Returns:
        (command_dict, response_text) where command_dict has 'action' and optional 'data'
    """
    text_lower = text.lower().strip()
    logger.debug(f"Checking workspace command: '{text}'")
    
    # ===== ADD NOTE =====
    note_patterns = [
        r"(?:add|make|create|write)\s+(?:a\s+)?note[,:\s]+(.+)",
        r"note\s+(?:this\s+)?(?:down)?[,:\s]+(.+)",
        r"write\s+(?:this\s+)?down[,:\s]+(.+)",
        r"remember\s+(?:this|that)?[,:\s]+(.+)",
        r"save\s+(?:this\s+)?(?:as\s+a\s+)?note[,:\s]+(.+)",
    ]
    
    for pattern in note_patterns:
        match = re.search(pattern, text_lower)
        if match:
            # Get original case content
            original_match = re.search(pattern, text, re.IGNORECASE)
            if original_match:
                note_content = text[original_match.start(1):original_match.end(1)].strip()
            else:
                note_content = match.group(1).strip()
            logger.debug(f"Note detected: '{note_content}'")
            return {"action": "add_note", "content": note_content}, "Got it, I've added that to your notes."
    
    # ===== ADD TODO =====
    todo_patterns = [
        # Explicit todo commands
        r"(?:add|create|make)\s+(?:a\s+)?(?:todo|to-do|to do|task)[,:\s]+(.+)",
        r"(?:add|create|make)\s+(?:a\s+)?(?:to-do|todo)[,:\s]+(.+)",
        # "remind me to X", "tell me to X"
        r"(?:remind|tell)\s+me\s+to\s+(.+)",
        # "add X to my todo list", "put X on my list"
        r"(?:put|add)\s+(.+?)\s+(?:to|on)\s+(?:the\s+)?(?:my\s+)?(?:todo|to-do|to do|task)\s*list",
        r"(?:add)\s+(.+?)\s+(?:to|on)\s+(?:the\s+)?(?:my\s+)?list",
        # "I need to X" / "I have to X" / "don't forget to X"
        r"(?:i\s+)?(?:need|have|got)\s+to\s+(.+)",
        r"don'?t\s+(?:let\s+me\s+)?forget\s+(?:to\s+)?(.+)",
        # "task: X"
        r"task[,:\s]+(.+)",
        # "todo X" (very direct)
        r"^to-?do[,:\s]+(.+)",
        # "my todo is X" / "my task is X"
        r"(?:my\s+)?(?:todo|to-do|task)\s+(?:is\s+)?[,:\s]+(.+)",
        # Simple "add X" at start of sentence (last resort, less specific)
        r"^add\s+[\"']?(.+?)[\"']?(?:\s+(?:to\s+)?(?:my|the)\s+(?:list|todos?))?$",
    ]
    
    for pattern in todo_patterns:
        match = re.search(pattern, text_lower)
        if match:
            # Get original case content
            original_match = re.search(pattern, text, re.IGNORECASE)
            if original_match:
                todo_content = text[original_match.start(1):original_match.end(1)].strip()
            else:
                todo_content = match.group(1).strip()
            # Clean up the content
            todo_content = re.sub(r'^(?:that\s+)?(?:i\s+)?(?:need|have|got)\s+to\s+', '', todo_content, flags=re.IGNORECASE)
            todo_content = re.sub(r'[.,;!?]+$', '', todo_content)  # Remove trailing punctuation
            logger.debug(f"Todo detected: '{todo_content}'")
            return {"action": "add_todo", "content": todo_content}, f"Added to your to-do list: {todo_content}"
    
    # ===== MARK TODO DONE =====
    done_patterns = [
        r"mark\s+['\"]?(.+?)['\"]?\s+(?:as\s+)?(?:done|complete|finished)",
        r"(?:i'm\s+)?done\s+with\s+['\"]?(.+)['\"]?",
        r"(?:i\s+)?(?:completed|finished)\s+['\"]?(.+)['\"]?",
        r"check\s+off\s+['\"]?(.+)['\"]?",
    ]
    
    for pattern in done_patterns:
        match = re.search(pattern, text_lower)
        if match:
            todo_text = match.group(1).strip()
            return {"action": "complete_todo", "search": todo_text}, "I'll mark that as done."
    
    # ===== READ TODOS =====
    if re.search(r"(?:what(?:'s| is)\s+(?:on\s+)?my\s+(?:todo|to-do|task)\s*list|read\s+(?:my\s+)?(?:todos?|to-dos?|tasks?))", text_lower):
        return {"action": "read_todos"}, "Let me check your to-do list."
    
    # ===== READ NOTES =====
    if re.search(r"(?:read|show|what(?:'s| is| are))\s+(?:my\s+)?notes?", text_lower):
        return {"action": "read_notes"}, "Let me read your notes."
    
    # ===== LOG DATA =====
    data_patterns = [
        # "log X minutes/hours of exercise/running/etc"
        (r"log\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\s+(?:of\s+)?(\w+)", "exercise"),
        # "log exercise 30 minutes"
        (r"log\s+(exercise|workout|running|walking|cycling|swimming|weights?|yoga)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)?", "exercise"),
        # "log weight 185 lbs"
        (r"log\s+(?:my\s+)?weight\s+(\d+(?:\.\d+)?)\s*(lbs?|pounds?|kg|kilos?)?", "weight"),
        # "track 2000 calories"
        (r"(?:log|track)\s+(\d+)\s*(calories?|cals?)", "diet"),
        # "log sleep 8 hours"
        (r"log\s+(?:my\s+)?sleep\s+(\d+(?:\.\d+)?)\s*(hours?|hrs?)?", "sleep"),
        # "log water 64 oz"
        (r"log\s+(?:my\s+)?water\s+(\d+)\s*(oz|ounces?|cups?|glasses?|liters?|ml)?", "water"),
    ]
    
    for pattern, data_type in data_patterns:
        match = re.search(pattern, text_lower)
        if match:
            groups = match.groups()
            if data_type == "exercise" and len(groups) >= 3:
                if groups[0].isdigit():
                    # "log 30 minutes of running"
                    value = groups[0]
                    unit = groups[1]
                    activity = groups[2] if len(groups) > 2 else "exercise"
                else:
                    # "log running 30 minutes"
                    activity = groups[0]
                    value = groups[1]
                    unit = groups[2] if groups[2] else "minutes"
                return {
                    "action": "log_data",
                    "type": "exercise",
                    "value": value,
                    "unit": unit,
                    "notes": activity
                }, f"Logged {value} {unit} of {activity}."
            elif data_type == "weight":
                value = groups[0]
                unit = groups[1] if groups[1] else "lbs"
                return {
                    "action": "log_data",
                    "type": "weight",
                    "value": value,
                    "unit": unit
                }, f"Logged weight: {value} {unit}."
            elif data_type == "diet":
                value = groups[0]
                unit = "calories"
                return {
                    "action": "log_data",
                    "type": "diet",
                    "value": value,
                    "unit": unit
                }, f"Logged {value} calories."
            elif data_type == "sleep":
                value = groups[0]
                unit = groups[1] if groups[1] else "hours"
                return {
                    "action": "log_data",
                    "type": "sleep",
                    "value": value,
                    "unit": unit
                }, f"Logged {value} {unit} of sleep."
            elif data_type == "water":
                value = groups[0]
                unit = groups[1] if groups[1] else "oz"
                return {
                    "action": "log_data",
                    "type": "water",
                    "value": value,
                    "unit": unit
                }, f"Logged {value} {unit} of water."
    
    # ===== OPEN WORKSPACE =====
    if re.search(r"(?:open|show)\s+(?:my\s+)?(?:workspace|notes?|todos?|data|tracking)", text_lower):
        return {"action": "open_workspace"}, "Opening your workspace."
    
    # ===== FALLBACK DETECTION =====
    # If text contains "to-do" or "todo" plus something that looks like a task
    fallback_todo = re.search(r"(?:add\s+)?(.+?)\s+(?:to\s+)?(?:my\s+)?(?:to-?do|todo|task)\s*(?:list)?", text_lower)
    if fallback_todo:
        content = fallback_todo.group(1).strip()
        content = re.sub(r"^(?:add\s+)?(?:a\s+)?", "", content)
        content = re.sub(r"[.,;!?]+$", "", content)
        if content and len(content) > 2:
            logger.debug(f"Fallback todo detected: '{content}'")
            return {"action": "add_todo", "content": content}, f"Added to your to-do list: {content}"
    
    # Fallback for notes
    fallback_note = re.search(r"(?:add\s+)?(?:a\s+)?note[,:\s]+(.+)", text_lower)
    if not fallback_note:
        fallback_note = re.search(r"(.+?)\s+(?:to\s+)?(?:my\s+)?notes?", text_lower)
    if fallback_note:
        content = fallback_note.group(1).strip()
        content = re.sub(r"^(?:add\s+)?(?:a\s+)?", "", content)
        content = re.sub(r"[.,;!?]+$", "", content)
        if content and len(content) > 2:
            logger.debug(f"Fallback note detected: '{content}'")
            return {"action": "add_note", "content": content}, "Got it, I've added that to your notes."
    
    logger.debug("No workspace command detected")
    return None, ""

