"""WebSocket endpoint for real-time voice conversation.

This is the main WebSocket entry point. All message handling logic
has been moved to dedicated handler modules in app/handlers/.

Handler responsibilities:
- VoiceHandler: Audio/text input, LLM response, TTS
- VisionHandler: Open/close eyes, describe view
- WorkspaceHandler: Notes, todos, data tracking
- SearchHandler: Web search via SearXNG/Perplexica
- MCPHandler: Docker and Home Assistant control
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core import get_logger, MessageType, ResponseType, Status
from ..handlers.base import ConversationState, HandlerContext
from ..handlers import (
    voice_handler,
    vision_handler,
    workspace_handler,
    search_handler,
)
from ..services.settings_manager import settings_manager
from ..services.background_worker import background_worker
from ..models.schemas import UserSettings

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for voice conversation.
    
    Message routing:
    - audio_data, text_message, speak_text -> VoiceHandler
    - open_eyes, close_eyes, get_vision_status -> VisionHandler
    - workspace_result -> WorkspaceHandler
    - web_search -> SearchHandler
    - settings_update, clear_history, interrupt -> Handled inline
    """
    await websocket.accept()
    state = ConversationState()
    user_settings = settings_manager.load()
    
    logger.info("Client connected")
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": ResponseType.STATUS.value,
            "state": Status.IDLE.value,
            "settings": user_settings.model_dump()
        })
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            # Record user activity (resets idle timer for background embedding)
            background_worker.record_activity()
            
            # Create handler context
            ctx = HandlerContext(
                websocket=websocket,
                state=state,
                settings=user_settings,
                data=data
            )
            
            # =========================================
            # Voice/Text Input -> VoiceHandler
            # =========================================
            if msg_type in [MessageType.AUDIO_DATA.value, 
                           MessageType.TEXT_MESSAGE.value,
                           MessageType.SPEAK_TEXT.value]:
                await voice_handler.safe_handle(ctx)
            
            # =========================================
            # Vision -> VisionHandler
            # =========================================
            elif msg_type in [MessageType.OPEN_EYES.value,
                             MessageType.CLOSE_EYES.value,
                             MessageType.GET_VISION_STATUS.value]:
                await vision_handler.safe_handle(ctx)
            
            # =========================================
            # Workspace -> WorkspaceHandler
            # =========================================
            elif msg_type == MessageType.WORKSPACE_RESULT.value:
                await workspace_handler.safe_handle(ctx)
            
            # =========================================
            # Search -> SearchHandler
            # =========================================
            elif msg_type == MessageType.WEB_SEARCH.value:
                await search_handler.safe_handle(ctx)
            
            # =========================================
            # Inline Handlers (Simple operations)
            # =========================================
            elif msg_type == MessageType.INTERRUPT.value:
                state.should_interrupt = True
                if state.current_audio_task:
                    state.current_audio_task.cancel()
                await websocket.send_json({"type": ResponseType.INTERRUPTED.value})
            
            elif msg_type == MessageType.SETTINGS_UPDATE.value:
                new_settings = UserSettings(**data.get("settings", {}))
                user_settings = settings_manager.save(new_settings)
                ctx.settings = user_settings  # Update context
                await websocket.send_json({
                    "type": ResponseType.SETTINGS_UPDATED.value,
                    "settings": user_settings.model_dump()
                })
            
            elif msg_type == MessageType.CLEAR_HISTORY.value:
                state.messages = []
                await websocket.send_json({"type": ResponseType.HISTORY_CLEARED.value})
    
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close(code=1011, reason=str(e))
