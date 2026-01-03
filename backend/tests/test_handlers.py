"""Tests for WebSocket message handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from app.handlers.base import BaseHandler, HandlerContext, ConversationState
from app.handlers.voice import VoiceHandler
from app.handlers.vision import VisionHandler
from app.handlers.workspace import WorkspaceHandler
from app.handlers.search import SearchHandler
from app.core.constants import MessageType, ResponseType, Status


class TestConversationState:
    """Tests for ConversationState."""
    
    def test_init(self):
        """Test default initialization."""
        state = ConversationState()
        assert state.messages == []
        assert state.should_interrupt is False
        assert state.is_speaking is False
        assert state.current_audio_task is None
    
    def test_reset_interrupt(self):
        """Test interrupt reset."""
        state = ConversationState()
        state.should_interrupt = True
        state.reset_interrupt()
        assert state.should_interrupt is False


class TestHandlerContext:
    """Tests for HandlerContext."""
    
    @pytest.mark.asyncio
    async def test_send_status(self, mock_websocket, sample_user_settings, sample_conversation_state):
        """Test sending status updates."""
        ctx = HandlerContext(
            websocket=mock_websocket,
            state=sample_conversation_state,
            settings=sample_user_settings,
            data={}
        )
        
        await ctx.send_status(Status.PROCESSING)
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == ResponseType.STATUS.value
        assert call_args["state"] == Status.PROCESSING.value
    
    @pytest.mark.asyncio
    async def test_send_error(self, mock_websocket, sample_user_settings, sample_conversation_state):
        """Test sending error messages."""
        ctx = HandlerContext(
            websocket=mock_websocket,
            state=sample_conversation_state,
            settings=sample_user_settings,
            data={}
        )
        
        await ctx.send_error("Something went wrong")
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == ResponseType.ERROR.value
        assert call_args["message"] == "Something went wrong"


class TestVoiceHandler:
    """Tests for VoiceHandler."""
    
    def test_instance_creation(self):
        """Test handler can be instantiated."""
        handler = VoiceHandler()
        assert handler is not None
    
    @pytest.mark.asyncio
    async def test_handle_routes_audio(self, mock_websocket, sample_user_settings, sample_conversation_state):
        """Test that audio_data routes to _handle_audio."""
        handler = VoiceHandler()
        
        ctx = HandlerContext(
            websocket=mock_websocket,
            state=sample_conversation_state,
            settings=sample_user_settings,
            data={"type": MessageType.AUDIO_DATA.value, "audio": ""}
        )
        
        # Mock the internal handler
        handler._handle_audio = AsyncMock()
        
        await handler.handle(ctx)
        
        handler._handle_audio.assert_called_once_with(ctx)
    
    @pytest.mark.asyncio
    async def test_handle_routes_text(self, mock_websocket, sample_user_settings, sample_conversation_state):
        """Test that text_message routes to _handle_text."""
        handler = VoiceHandler()
        
        ctx = HandlerContext(
            websocket=mock_websocket,
            state=sample_conversation_state,
            settings=sample_user_settings,
            data={"type": MessageType.TEXT_MESSAGE.value, "content": "hello"}
        )
        
        handler._handle_text = AsyncMock()
        
        await handler.handle(ctx)
        
        handler._handle_text.assert_called_once_with(ctx)


class TestVisionHandler:
    """Tests for VisionHandler."""
    
    def test_instance_creation(self):
        """Test handler can be instantiated."""
        handler = VisionHandler()
        assert handler is not None
    
    @pytest.mark.asyncio
    async def test_handle_open_eyes(self, mock_websocket, sample_user_settings, sample_conversation_state):
        """Test open_eyes message routing."""
        handler = VisionHandler()
        
        ctx = HandlerContext(
            websocket=mock_websocket,
            state=sample_conversation_state,
            settings=sample_user_settings,
            data={"type": MessageType.OPEN_EYES.value}
        )
        
        handler.handle_open = AsyncMock()
        
        await handler.handle(ctx)
        
        handler.handle_open.assert_called_once()


class TestWorkspaceHandler:
    """Tests for WorkspaceHandler."""
    
    def test_instance_creation(self):
        """Test handler can be instantiated."""
        handler = WorkspaceHandler()
        assert handler is not None
    
    def test_get_confirmation_text_add_todo(self):
        """Test confirmation text for add_todo."""
        handler = WorkspaceHandler()
        text = handler._get_confirmation_text("add_todo", {"content": "buy milk"})
        assert "Added to your to-do list" in text
        assert "buy milk" in text
    
    def test_get_confirmation_text_clear_todos(self):
        """Test confirmation text for clear_todos."""
        handler = WorkspaceHandler()
        text = handler._get_confirmation_text("clear_todos", {})
        assert "Cleared" in text


class TestSearchHandler:
    """Tests for SearchHandler."""
    
    def test_instance_creation(self):
        """Test handler can be instantiated."""
        handler = SearchHandler()
        assert handler is not None
    
    def test_format_search_context(self):
        """Test search context formatting."""
        handler = SearchHandler()
        
        results = {
            "summary": "Test summary",
            "results": [
                {"title": "Result 1", "url": "http://example.com", "snippet": "Test snippet"}
            ]
        }
        
        context = handler._format_search_context(results)
        
        assert "AI Summary: Test summary" in context
        assert "Result 1" in context


class TestBaseHandlerSafeHandle:
    """Tests for BaseHandler.safe_handle error handling."""
    
    @pytest.mark.asyncio
    async def test_safe_handle_catches_exceptions(self, mock_websocket, sample_user_settings, sample_conversation_state):
        """Test that safe_handle catches exceptions and sends error."""
        
        class FailingHandler(BaseHandler):
            async def handle(self, ctx: HandlerContext):
                raise ValueError("Test error")
        
        handler = FailingHandler()
        
        ctx = HandlerContext(
            websocket=mock_websocket,
            state=sample_conversation_state,
            settings=sample_user_settings,
            data={}
        )
        
        # Should not raise
        await handler.safe_handle(ctx)
        
        # Should have sent error message
        assert mock_websocket.send_json.call_count >= 1
        
        # Check that error was sent
        calls = mock_websocket.send_json.call_args_list
        error_sent = any(
            call[0][0].get("type") == ResponseType.ERROR.value
            for call in calls
        )
        assert error_sent, "Error message should have been sent"
