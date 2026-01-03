"""Galatea Services

This module provides service classes for external integrations:
- Ollama (LLM)
- Kokoro/Piper (TTS)
- Whisper (STT)
- SearXNG/Perplexica (Web Search)
- Vision (Image Analysis)
- Docker/HomeAssistant (MCP)

Usage:
    from app.services import ollama_service, kokoro_service
    
    # Or use dependency injection:
    from app.services import ServiceContainer
    container = ServiceContainer()
"""

from .base import BaseService, ServiceResult

__all__ = [
    "BaseService",
    "ServiceResult",
]
