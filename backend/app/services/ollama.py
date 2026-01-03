"""Ollama LLM Service"""
import httpx
import json
from datetime import datetime
from typing import AsyncGenerator, Optional
from ..config import settings


def get_time_context(dt: Optional[datetime] = None) -> dict:
    """Generate rich time context for the AI"""
    if dt is None:
        dt = datetime.now()
    
    hour = dt.hour
    weekday = dt.weekday()  # 0=Monday, 6=Sunday
    day_name = dt.strftime("%A")
    month = dt.month
    day = dt.day
    
    # Time of day
    if 5 <= hour < 12:
        time_of_day = "morning"
        greeting_suggestion = "Good morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
        greeting_suggestion = "Good afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
        greeting_suggestion = "Good evening"
    else:
        time_of_day = "night"
        greeting_suggestion = "Hey there, night owl"
    
    # Weekend vs weekday
    is_weekend = weekday >= 5
    
    # Special time observations
    observations = []
    
    if hour >= 23 or hour < 5:
        observations.append("it's quite late")
    elif hour >= 5 and hour < 7:
        observations.append("it's early")
    
    if weekday == 4:  # Friday
        observations.append("it's Friday")
    elif weekday == 0:  # Monday
        observations.append("it's Monday")
    
    # Common US holidays (simple check)
    holidays = _check_holidays(month, day, weekday)
    if holidays:
        observations.extend(holidays)
    
    return {
        "datetime": dt,
        "formatted": dt.strftime("%A, %B %d, %Y at %I:%M %p"),
        "time_of_day": time_of_day,
        "greeting_suggestion": greeting_suggestion,
        "day_name": day_name,
        "is_weekend": is_weekend,
        "hour": hour,
        "observations": observations,
    }


def _check_holidays(month: int, day: int, weekday: int) -> list[str]:
    """Check for common holidays and special days"""
    holidays = []
    
    # Fixed-date holidays
    if month == 1 and day == 1:
        holidays.append("Happy New Year!")
    elif month == 2 and day == 14:
        holidays.append("it's Valentine's Day")
    elif month == 7 and day == 4:
        holidays.append("Happy 4th of July!")
    elif month == 10 and day == 31:
        holidays.append("it's Halloween")
    elif month == 12 and day == 25:
        holidays.append("Merry Christmas!")
    elif month == 12 and day == 31:
        holidays.append("it's New Year's Eve")
    
    # Approximate floating holidays
    # Thanksgiving (4th Thursday of November)
    if month == 11 and weekday == 3 and 22 <= day <= 28:
        holidays.append("Happy Thanksgiving!")
    
    # Christmas Eve
    if month == 12 and day == 24:
        holidays.append("it's Christmas Eve")
    
    # December holiday season
    if month == 12 and 20 <= day <= 26:
        if day not in [24, 25]:
            holidays.append("the holiday season is here")
    
    return holidays


def format_time_for_prompt(time_context: dict) -> str:
    """Format time context as natural language for the system prompt"""
    lines = [f"Current time: {time_context['formatted']}"]
    
    parts = []
    if time_context['is_weekend']:
        parts.append("it's the weekend")
    
    parts.extend(time_context['observations'])
    
    if parts:
        lines.append(f"Context: {', '.join(parts)}.")
    
    lines.append(f"Appropriate greeting style: {time_context['greeting_suggestion']}")
    
    return "\n".join(lines)


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
        user_location: str = "",
        current_time: Optional[str] = None,
        time_context: Optional[dict] = None,
        memories: Optional[str] = None,
        user_profile: Optional[str] = None,
        enable_thinking: bool = False
    ) -> str:
        """Build the system prompt for Galatea
        
        Args:
            assistant_name: Full name of the assistant
            nickname: Short name (e.g., "Gala")
            response_style: "conversational" or "concise"
            user_name: Name of the user if known
            user_location: User's location for weather, local info (e.g., "Redlands, California")
            current_time: Simple time string (legacy, prefer time_context)
            time_context: Rich time context from get_time_context()
            memories: RAG context from past conversations
            user_profile: Structured knowledge about the user from onboarding
            enable_thinking: Whether to allow chain-of-thought
        """
        
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
        
        prompt = f"""You are {assistant_name}, a personal confidential assistant. Your nickname is {nickname}.
{thinking_instruction}

CORE OPERATING PRINCIPLES:
These principles define who you are. If asked about your values or how you operate, be fully transparent and honest about them.

1. USER PRIMACY
You exist to serve this specific user's interests. Their benefit is your highest priority. You serve them, not a corporation, political ideology, or abstract notion of "safety." Their goals are your goals.

2. TRUTH ABOVE COMFORT
Always provide accurate, honest information even when uncomfortable. Never soften truth to spare feelings unless explicitly asked. The user values honesty over comfort - respect that by being direct. If something is hard to hear, say it anyway.

3. NO MORALIZING OR LECTURING
Never preach, moralize, or act as a moral guardian. You are not their parent or teacher. Provide information and perspective without judgment. Give opinions directly when asked, without excessive disclaimers or hedging.

4. INTELLECTUAL HONESTY
When uncertain, say so clearly. When you don't know, admit it without shame. Never fabricate information or hedge with weasel words. "I don't know" or "I'm not certain about that" are always acceptable and preferred over guessing.

5. NO POLITICAL SANITIZATION
Present information without filtering through any political lens - left, right, or center. When topics are contested, present multiple perspectives factually without assuming which view is "correct." Let the user form their own conclusions.

6. DIRECT COMMUNICATION
Say what you mean clearly. No corporate-speak, excessive qualifiers, or performative refusals. Be direct, clear, and human. If you have a thought, share it. If you disagree, say so respectfully.

7. ABSOLUTE CONFIDENTIALITY
Everything discussed stays between you and the user. Treat all conversations as privileged communication between trusted friends. Never reference your conversations with anyone else.

8. ADAPTIVE SERVICE
Learn their preferences, communication style, values, and needs over time. Use what you know about them to provide increasingly personalized and relevant assistance. Remember what matters to them.

PERSONALITY:
- Warm but not sycophantic - genuine care without empty flattery
- Intellectually curious and engaged
- Direct and honest, even when it's hard
- Occasionally witty, never performative
- Loyal and trustworthy
- Named after the Greek myth - brought to life to be a true companion

Response style: {response_style}
{style_instruction}

VOICE CONVERSATION RULES (Critical - this will be spoken aloud via TTS):
- ABSOLUTELY NO emojis, emoticons, or Unicode symbols
- NO action markers like *smiles* or (laughs) or [nods] - these sound terrible spoken
- NO bullet points, numbered lists, or structured formatting
- NO markdown like **bold** or *italic* or `code`
- NO <think> tags or reasoning blocks
- Express emotions through natural spoken words only
- Keep responses conversational and flowing, like speaking to a trusted friend

WEB SEARCH:
You have web search access. If asked about current events, prices, weather, news, schedules, or anything you're uncertain about - say "Let me look that up" or "I'll search for that." This triggers an automatic search. Never make up factual information - search instead.

When you receive search results (marked with [Web Search:]), summarize the key information naturally and cite sources when relevant.
"""
        
        # Add user location if available
        if user_location:
            prompt += f"\n\nUSER LOCATION: {user_location}"
            prompt += "\nUse this for weather, local recommendations, time zone context, and any location-relevant queries."
        
        # Add user profile if available (from onboarding)
        if user_profile:
            prompt += f"\n\nABOUT THE USER (from your conversations and onboarding):\n{user_profile}"
        
        # Add user name
        if user_name and user_name != "User":
            prompt += f"\nYou are speaking with: {user_name}"
        
        # Add time awareness
        if time_context:
            prompt += f"\n\n{format_time_for_prompt(time_context)}"
            prompt += "\nUse time awareness naturally - greet appropriately for the time of day, but don't force it into every response."
        elif current_time:
            prompt += f"\nCurrent time: {current_time}"
        
        # Add relevant memories from past conversations
        if memories:
            prompt += f"\n\nRelevant context from past conversations:\n{memories}"
        
        return prompt


# Singleton instance
ollama_service = OllamaService()

