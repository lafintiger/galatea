"""Pydantic schemas for API models"""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class UserSettings(BaseModel):
    """User settings schema"""
    assistant_name: str = "Galatea"
    assistant_nickname: str = "Gala"
    selected_model: str = "ministral-3:latest"
    selected_voice: str = "en_US-lessac-high"  # High quality for more natural sound
    response_style: Literal["concise", "conversational"] = "conversational"
    activation_mode: Literal["push-to-talk", "vad", "wake-word"] = "push-to-talk"
    wake_word: Optional[str] = None
    transcript_visible: bool = True
    theme: str = "futuristic-dark"
    language: str = "en"
    
    # TTS Provider: "piper" (fast, CPU) or "kokoro" (high quality, GPU)
    tts_provider: Literal["piper", "kokoro"] = "piper"
    
    # Voice tuning for more natural/expressive speech (Piper-specific)
    voice_speed: float = 1.0  # length_scale: 0.5-2.0 (lower=faster, higher=slower)
    voice_variation: float = 0.8  # noise_scale: 0-1 (higher=more expressive)
    voice_phoneme_var: float = 0.6  # noise_w: 0-1 (higher=more natural timing)
    
    # Vision (Gala's Eyes) - real-time face/emotion analysis
    vision_enabled: bool = False  # Eyes open/closed state


class Message(BaseModel):
    """Chat message schema"""
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    audio_url: Optional[str] = None


class Conversation(BaseModel):
    """Conversation schema"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[Message] = []


class OllamaModel(BaseModel):
    """Ollama model info"""
    name: str
    size: str
    modified: str


class PiperVoice(BaseModel):
    """Piper voice info"""
    id: str
    name: str
    language: str
    quality: str
    gender: str


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str
    data: Optional[dict] = None


class TranscriptionResult(BaseModel):
    """STT result"""
    text: str
    final: bool = True


class SynthesisRequest(BaseModel):
    """TTS request"""
    text: str
    voice: Optional[str] = None

