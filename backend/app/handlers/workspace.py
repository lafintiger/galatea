"""Workspace handler - Notes, todos, and data tracking.

This handler processes:
- Add/complete todos
- Add notes
- Log data (exercise, weight, etc.)
- Read/clear workspace items
"""
import base64

from .base import BaseHandler, HandlerContext
from ..core import (
    get_logger,
    synthesize_tts,
    ResponseType,
    Status,
    WorkspaceAction,
)

logger = get_logger(__name__)


class WorkspaceHandler(BaseHandler):
    """Handles workspace commands - todos, notes, data logging."""
    
    async def handle(self, ctx: HandlerContext) -> None:
        """Handle workspace result from frontend."""
        # This is called when frontend reports completion of a workspace action
        result = ctx.data.get("result", {})
        action = result.get("action", "")
        success = result.get("success", False)
        
        if success:
            response_text = result.get("response", "Done!")
        else:
            response_text = result.get("error", "Something went wrong.")
        
        ctx.state.messages.append({"role": "assistant", "content": response_text})
        await ctx.send_response(ResponseType.LLM_COMPLETE, text=response_text)
        
        await ctx.send_status(Status.SPEAKING)
        await self._speak(ctx, response_text)
        await ctx.send_status(Status.IDLE)
    
    async def handle_command(
        self,
        ctx: HandlerContext,
        command: dict,
        response_text: str
    ) -> None:
        """Handle a workspace command from command router."""
        action = command.get("action", "")
        
        logger.debug(f"Workspace command: {action}")
        
        # Actions that need frontend to process
        frontend_actions = {
            WorkspaceAction.ADD_TODO,
            WorkspaceAction.ADD_NOTE,
            WorkspaceAction.COMPLETE_TODO,
            WorkspaceAction.LOG_DATA,
            WorkspaceAction.CLEAR_TODOS,
            WorkspaceAction.CLEAR_NOTES,
        }
        
        # Check if this action needs frontend processing
        if action in [a.value for a in frontend_actions]:
            # Send command to frontend
            await ctx.send_response(
                ResponseType.WORKSPACE_COMMAND,
                command=command
            )
            
            # Record in conversation
            ctx.state.messages.append({"role": "user", "content": f"[Workspace: {action}]"})
            
            # Build confirmation text based on action
            confirmation_text = self._get_confirmation_text(action, command)
            
            ctx.state.messages.append({"role": "assistant", "content": confirmation_text})
            
            logger.debug(f"Sending llm_complete: '{confirmation_text[:50]}...'")
            await ctx.send_response(ResponseType.LLM_COMPLETE, text=confirmation_text)
            
            await ctx.send_status(Status.SPEAKING)
            await self._speak(ctx, confirmation_text)
            await ctx.send_status(Status.IDLE)
            
        # Actions handled entirely in backend (read operations)
        elif action == WorkspaceAction.READ_TODOS.value:
            await self._handle_read_todos(ctx)
        elif action == WorkspaceAction.READ_NOTES.value:
            await self._handle_read_notes(ctx)
        elif action == WorkspaceAction.OPEN_WORKSPACE.value:
            tab = command.get("tab", "notes")
            await ctx.send_response(
                ResponseType.WORKSPACE_COMMAND,
                command={"action": "open_workspace", "tab": tab}
            )
            confirmation_text = f"Opening your {tab}."
            ctx.state.messages.append({"role": "assistant", "content": confirmation_text})
            await ctx.send_response(ResponseType.LLM_COMPLETE, text=confirmation_text)
            await ctx.send_status(Status.SPEAKING)
            await self._speak(ctx, confirmation_text)
            await ctx.send_status(Status.IDLE)
        else:
            # Unknown action - just respond
            await ctx.send_status(Status.SPEAKING)
            await self._speak(ctx, response_text)
            await ctx.send_status(Status.IDLE)
    
    def _get_confirmation_text(self, action: str, command: dict) -> str:
        """Generate confirmation text for an action."""
        if action == WorkspaceAction.ADD_TODO.value:
            content = command.get("content", "")
            return f"Added to your to-do list: {content}"
        elif action == WorkspaceAction.ADD_NOTE.value:
            content = command.get("content", "")
            preview = content[:50] + "..." if len(content) > 50 else content
            return f"Added to your notes: {preview}"
        elif action == WorkspaceAction.COMPLETE_TODO.value:
            search = command.get("search", "")
            return f"Marked '{search}' as complete."
        elif action == WorkspaceAction.LOG_DATA.value:
            data_type = command.get("type", "data")
            value = command.get("value", "")
            unit = command.get("unit", "")
            return f"Logged your {data_type}: {value} {unit}".strip()
        elif action == WorkspaceAction.CLEAR_TODOS.value:
            return "Cleared all your todos."
        elif action == WorkspaceAction.CLEAR_NOTES.value:
            return "Cleared all your notes."
        else:
            return "Done!"
    
    async def _handle_read_todos(self, ctx: HandlerContext) -> None:
        """Handle read todos request."""
        # This triggers frontend to send back the current todos
        await ctx.send_response(
            ResponseType.WORKSPACE_COMMAND,
            command={"action": "read_todos"}
        )
        # Response will come back via workspace_result
    
    async def _handle_read_notes(self, ctx: HandlerContext) -> None:
        """Handle read notes request."""
        # This triggers frontend to send back the current notes
        await ctx.send_response(
            ResponseType.WORKSPACE_COMMAND,
            command={"action": "read_notes"}
        )
        # Response will come back via workspace_result
    
    async def _speak(self, ctx: HandlerContext, text: str) -> None:
        """Synthesize and send TTS audio."""
        try:
            audio_data = await synthesize_tts(
                text=text,
                voice=ctx.settings.selected_voice,
                provider=getattr(ctx.settings, 'tts_provider', 'piper'),
                speed=getattr(ctx.settings, 'voice_speed', 1.0)
            )
            if audio_data:
                await ctx.send_response(
                    ResponseType.AUDIO_CHUNK,
                    audio=base64.b64encode(audio_data).decode('utf-8'),
                    sentence=text
                )
        except Exception as e:
            logger.error(f"Workspace TTS error: {e}")
