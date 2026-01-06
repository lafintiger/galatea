"""Galatea Configuration"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "qwen3:4b"
    
    # Wyoming Whisper (STT)
    whisper_host: str = "localhost"
    whisper_port: int = 10300
    
    # Wyoming Piper (TTS) - Fast CPU-based TTS
    piper_host: str = "localhost"
    piper_port: int = 10200
    default_voice: str = "en_US-lessac-medium"
    
    # Kokoro TTS (High quality GPU-accelerated TTS)
    kokoro_base_url: str = "http://localhost:8880"
    kokoro_default_voice: str = "af_heart"
    
    # TTS Provider: "piper" (fast), "kokoro" (high quality), "chatterbox" (SoTA + cloning)
    tts_provider: str = "piper"
    
    # Chatterbox TTS (State-of-the-art TTS with voice cloning)
    chatterbox_base_url: str = "http://localhost:8881"
    chatterbox_default_voice: str = "default"
    
    # STT Provider: "whisper" (stable) or "parakeet" (fast, NVIDIA)
    stt_provider: str = "whisper"
    
    # Parakeet ASR (NVIDIA low-latency STT)
    parakeet_base_url: str = "http://localhost:50052"
    parakeet_model: str = "parakeet-ctc-1.1b"
    
    # Web Search - SearXNG (meta-search engine)
    searxng_host: str = "localhost"
    searxng_port: int = 4000
    
    # Web Search - Perplexica (AI-powered search)
    perplexica_host: str = "localhost"
    perplexica_port: int = 3000
    # Perplexica provider ID for Ollama (get from Perplexica config.json)
    perplexica_ollama_provider_id: str = "ff71bfa7-4d8d-45c2-8e70-a6232e437a5f"
    perplexica_chat_model: str = "qwen3:4b"  # Fast non-thinking model for search
    perplexica_embedding_model: str = "nomic-embed-text:latest"  # Embedding model
    
    # Vision Service (galatea-vision - DeepFace face/emotion analysis)
    vision_host: str = "localhost"
    vision_port: int = 8020
    
    # Home Assistant (MCP Integration)
    ha_url: str = ""  # e.g., http://homeassistant.local:8123
    ha_token: str = ""  # Long-lived access token
    
    # Docker Management (MCP Integration)
    docker_enabled: bool = True  # Enable Docker container management
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/galatea.db"
    chroma_path: str = "./data/chroma"
    
    # Paths
    data_dir: Path = Path("./data")
    audio_dir: Path = Path("./data/audio")
    
    # Assistant defaults
    assistant_name: str = "Galatea"
    assistant_nickname: str = "Gala"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.audio_dir.mkdir(parents=True, exist_ok=True)

