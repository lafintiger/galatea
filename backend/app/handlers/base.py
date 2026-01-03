"""Base handler class for WebSocket message handling.

All handlers inherit from BaseHandler and implement the handle() method.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
import asyncio

from fastapi import WebSocket

from ..models.schemas import UserSettings
from ..core import get_logger, ResponseType, Status

logger = get_logger(__name__)


@dataclass
class ConversationState:
    """Shared state for a WebSocket conversation."""
    messages: list = field(default_factory=list)
    should_interrupt: bool = False
    is_speaking: bool = False
    current_audio_task: Optional[asyncio.Task] = None
    
    def reset_interrupt(self):
        """Reset interrupt flag."""
        self.should_interrupt = False


@dataclass
class HandlerContext:
    """Context passed to all handlers."""
    websocket: WebSocket
    state: ConversationState
    settings: UserSettings
    data: dict
    
    async def send_status(self, status: Status):
        """Send status update to client."""
        await self.websocket.send_json({
            "type": ResponseType.STATUS,
            "state": status.value
        })
    
    async def send_error(self, message: str):
        """Send error to client."""
        await self.websocket.send_json({
            "type": ResponseType.ERROR,
            "message": message
        })
    
    async def send_response(self, response_type: ResponseType, **kwargs):
        """Send a typed response to client."""
        await self.websocket.send_json({
            "type": response_type.value,
            **kwargs
        })


class BaseHandler(ABC):
    """Abstract base class for WebSocket message handlers."""
    
    @abstractmethod
    async def handle(self, ctx: HandlerContext) -> None:
        """Handle the incoming message.
        
        Args:
            ctx: Handler context with websocket, state, settings, and data
        """
        pass
    
    async def safe_handle(self, ctx: HandlerContext) -> None:
        """Wrapper that catches exceptions and sends errors to client."""
        try:
            await self.handle(ctx)
        except Exception as e:
            logger.error(f"Handler error: {e}", exc_info=True)
            await ctx.send_error(f"An error occurred: {str(e)}")
            await ctx.send_status(Status.IDLE)
