"""WebSocket message handlers.

Each handler is responsible for a specific domain of functionality.
The handler registry maps message types to their handlers.
"""
from .base import BaseHandler, HandlerContext
from .voice import VoiceHandler
from .vision import VisionHandler
from .workspace import WorkspaceHandler
from .search import SearchHandler
from .mcp import MCPHandler

from ..core.constants import MessageType

# Handler instances
voice_handler = VoiceHandler()
vision_handler = VisionHandler()
workspace_handler = WorkspaceHandler()
search_handler = SearchHandler()
mcp_handler = MCPHandler()

# Handler registry - maps message types to handlers
HANDLER_REGISTRY = {
    # Voice/Text
    MessageType.AUDIO_DATA: voice_handler,
    MessageType.TEXT_MESSAGE: voice_handler,
    MessageType.SPEAK_TEXT: voice_handler,
    
    # Vision
    MessageType.OPEN_EYES: vision_handler,
    MessageType.CLOSE_EYES: vision_handler,
    MessageType.GET_VISION_STATUS: vision_handler,
    
    # Workspace
    MessageType.WORKSPACE_RESULT: workspace_handler,
    
    # Search
    MessageType.WEB_SEARCH: search_handler,
}

__all__ = [
    "BaseHandler",
    "HandlerContext",
    "VoiceHandler",
    "VisionHandler",
    "WorkspaceHandler",
    "SearchHandler",
    "MCPHandler",
    "HANDLER_REGISTRY",
    "voice_handler",
    "vision_handler",
    "workspace_handler",
    "search_handler",
    "mcp_handler",
]
