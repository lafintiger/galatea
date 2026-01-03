"""Service Container for Dependency Injection.

This provides a central location for service instances, making it easy to:
1. Access services from anywhere in the codebase
2. Replace services with mocks for testing
3. Control service lifecycle

Usage:
    # Normal usage (singleton pattern)
    from app.services.container import services
    await services.ollama.chat(...)
    
    # Testing (inject mocks)
    from app.services.container import ServiceContainer
    mock_ollama = MockOllamaService()
    container = ServiceContainer(ollama=mock_ollama)
"""
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

# Lazy imports to avoid circular dependencies
if TYPE_CHECKING:
    from .ollama import OllamaService
    from .kokoro import KokoroService
    from .wyoming import WhisperService, PiperService
    from .web_search import WebSearchService
    from .vision import VisionService
    from .vision_live import VisionLiveService
    from .command_router import CommandRouter
    from .domain_router import DomainRouter
    from .embedding import EmbeddingService
    from .docker_service import DockerService
    from .homeassistant_service import HomeAssistantService
    from .user_profile import UserProfileService
    from .settings_manager import SettingsManager
    from .conversation_history import ConversationHistoryService


@dataclass
class ServiceContainer:
    """Container for all Galatea services.
    
    Services are lazily initialized on first access unless
    explicitly provided in the constructor.
    
    Example:
        # Use default services
        container = ServiceContainer()
        result = await container.ollama.chat(...)
        
        # Inject mock for testing
        container = ServiceContainer(ollama=mock_ollama)
    """
    # Core LLM/AI services
    _ollama: Optional["OllamaService"] = None
    _command_router: Optional["CommandRouter"] = None
    _domain_router: Optional["DomainRouter"] = None
    
    # Voice services
    _kokoro: Optional["KokoroService"] = None
    _whisper: Optional["WhisperService"] = None
    _piper: Optional["PiperService"] = None
    
    # Vision services
    _vision: Optional["VisionService"] = None
    _vision_live: Optional["VisionLiveService"] = None
    
    # Search & RAG
    _web_search: Optional["WebSearchService"] = None
    _embedding: Optional["EmbeddingService"] = None
    
    # MCP Integrations
    _docker: Optional["DockerService"] = None
    _homeassistant: Optional["HomeAssistantService"] = None
    
    # User data
    _user_profile: Optional["UserProfileService"] = None
    _settings: Optional["SettingsManager"] = None
    _conversation_history: Optional["ConversationHistoryService"] = None
    
    # =========================================
    # Lazy property accessors
    # =========================================
    
    @property
    def ollama(self) -> "OllamaService":
        """Get or create Ollama service."""
        if self._ollama is None:
            from .ollama import ollama_service
            self._ollama = ollama_service
        return self._ollama
    
    @property
    def command_router(self) -> "CommandRouter":
        """Get or create command router."""
        if self._command_router is None:
            from .command_router import command_router
            self._command_router = command_router
        return self._command_router
    
    @property
    def domain_router(self) -> "DomainRouter":
        """Get or create domain router."""
        if self._domain_router is None:
            from .domain_router import domain_router
            self._domain_router = domain_router
        return self._domain_router
    
    @property
    def kokoro(self) -> "KokoroService":
        """Get or create Kokoro TTS service."""
        if self._kokoro is None:
            from .kokoro import kokoro_service
            self._kokoro = kokoro_service
        return self._kokoro
    
    @property
    def whisper(self) -> "WhisperService":
        """Get or create Whisper STT service."""
        if self._whisper is None:
            from .wyoming import whisper_service
            self._whisper = whisper_service
        return self._whisper
    
    @property
    def piper(self) -> "PiperService":
        """Get or create Piper TTS service."""
        if self._piper is None:
            from .wyoming import piper_service
            self._piper = piper_service
        return self._piper
    
    @property
    def vision(self) -> "VisionService":
        """Get or create vision analysis service."""
        if self._vision is None:
            from .vision import vision_service
            self._vision = vision_service
        return self._vision
    
    @property
    def vision_live(self) -> "VisionLiveService":
        """Get or create live vision service."""
        if self._vision_live is None:
            from .vision_live import vision_live_service
            self._vision_live = vision_live_service
        return self._vision_live
    
    @property
    def web_search(self) -> "WebSearchService":
        """Get or create web search service."""
        if self._web_search is None:
            from .web_search import web_search
            self._web_search = web_search
        return self._web_search
    
    @property
    def embedding(self) -> "EmbeddingService":
        """Get or create embedding service."""
        if self._embedding is None:
            from .embedding import embedding_service
            self._embedding = embedding_service
        return self._embedding
    
    @property
    def docker(self) -> "DockerService":
        """Get or create Docker service."""
        if self._docker is None:
            from .docker_service import docker_service
            self._docker = docker_service
        return self._docker
    
    @property
    def homeassistant(self) -> "HomeAssistantService":
        """Get or create Home Assistant service."""
        if self._homeassistant is None:
            from .homeassistant_service import ha_service
            self._homeassistant = ha_service
        return self._homeassistant
    
    @property
    def user_profile(self) -> "UserProfileService":
        """Get or create user profile service."""
        if self._user_profile is None:
            from .user_profile import user_profile_service
            self._user_profile = user_profile_service
        return self._user_profile
    
    @property
    def settings(self) -> "SettingsManager":
        """Get or create settings manager."""
        if self._settings is None:
            from .settings_manager import settings_manager
            self._settings = settings_manager
        return self._settings
    
    @property
    def conversation_history(self) -> "ConversationHistoryService":
        """Get or create conversation history service."""
        if self._conversation_history is None:
            from .conversation_history import conversation_history
            self._conversation_history = conversation_history
        return self._conversation_history
    
    # =========================================
    # Health checks
    # =========================================
    
    async def check_health(self) -> dict:
        """Check health of all services."""
        return {
            "ollama": await self._check_service_health("ollama"),
            "kokoro": await self._check_service_health("kokoro"),
            "whisper": await self._check_service_health("whisper"),
            "vision": await self._check_service_health("vision"),
            "search": await self._check_service_health("search"),
            "docker": await self._check_service_health("docker"),
        }
    
    async def _check_service_health(self, service_name: str) -> dict:
        """Check health of a specific service."""
        try:
            if service_name == "ollama":
                available = await self.ollama.is_available()
            elif service_name == "kokoro":
                available = await self.kokoro.is_available()
            elif service_name == "whisper":
                available = True  # Wyoming doesn't have health check
            elif service_name == "vision":
                available = await self.vision_live.is_available()
            elif service_name == "search":
                status = await self.web_search.check_status()
                return {
                    "available": status["searxng"]["available"] or status["perplexica"]["available"],
                    "details": status
                }
            elif service_name == "docker":
                available = self.docker.is_available
            else:
                available = False
            
            return {"available": available}
        except Exception as e:
            return {"available": False, "error": str(e)}


# Default singleton container
services = ServiceContainer()
