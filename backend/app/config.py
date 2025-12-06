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
    default_model: str = "huihui_ai/qwen3-abliterated:8b"
    
    # Wyoming Whisper (STT)
    whisper_host: str = "localhost"
    whisper_port: int = 10300
    
    # Wyoming Piper (TTS)
    piper_host: str = "localhost"
    piper_port: int = 10200
    default_voice: str = "en_US-lessac-medium"
    
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

