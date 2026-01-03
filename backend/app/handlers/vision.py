"""Vision handler - Gala's eyes.

This handler processes:
- Open eyes (start vision)
- Close eyes (stop vision)
- Describe view (analyze current view)
- Get vision status
"""
import base64

from .base import BaseHandler, HandlerContext
from ..core import (
    get_logger,
    clean_for_speech,
    synthesize_tts,
    MessageType,
    ResponseType,
    Status,
)
from ..services.vision_live import vision_live_service
from ..services.vision import vision_service
from ..services.settings_manager import settings_manager

logger = get_logger(__name__)


class VisionHandler(BaseHandler):
    """Handles vision commands - open/close eyes, describe view."""
    
    async def handle(self, ctx: HandlerContext) -> None:
        """Route to appropriate sub-handler based on message type."""
        msg_type = ctx.data.get("type")
        
        if msg_type == MessageType.OPEN_EYES:
            await self.handle_open(ctx)
        elif msg_type == MessageType.CLOSE_EYES:
            await self.handle_close(ctx)
        elif msg_type == MessageType.GET_VISION_STATUS:
            await self._handle_get_status(ctx)
    
    async def handle_open(self, ctx: HandlerContext, response_text: str = "Opening my eyes...") -> None:
        """Open Gala's eyes - start vision analysis."""
        try:
            await vision_live_service.start()
            ctx.settings.vision_enabled = True
            settings_manager.save(ctx.settings)
            
            await ctx.send_response(
                ResponseType.VISION_STATUS,
                eyes_open=True,
                message=response_text
            )
            logger.info("Gala's eyes opened")
            
            # Capture startup context with scene analysis
            async def scene_analyzer(image_b64: str) -> str:
                """Analyze the scene using vision model."""
                try:
                    result = await vision_service.analyze_image(
                        image_base64=image_b64,
                        prompt="Briefly describe what you see in this image. Focus on the person, their setting, and any notable details. Keep it concise (1-2 sentences).",
                        model_type="general"
                    )
                    if result.get("success"):
                        return result.get("description", "")
                except Exception as e:
                    logger.warning(f"Scene analysis failed: {e}")
                return ""
            
            try:
                startup_context = await vision_live_service.capture_startup_context(scene_analyzer=scene_analyzer)
                if startup_context:
                    logger.info(f"Startup context captured: identity={startup_context.identity}, emotion={startup_context.emotion}, scene={startup_context.scene_description[:50] if startup_context.scene_description else 'N/A'}...")
            except Exception as e:
                logger.warning(f"Failed to capture startup context: {e}")
            
            # Record in conversation
            ctx.state.messages.append({"role": "user", "content": "[Vision command: open eyes]"})
            ctx.state.messages.append({"role": "assistant", "content": response_text})
            
            # Speak response
            await ctx.send_status(Status.SPEAKING)
            await self._speak(ctx, response_text)
            await ctx.send_status(Status.IDLE)
            
        except Exception as e:
            error_msg = f"Couldn't open my eyes: {str(e)}"
            await ctx.send_error(error_msg)
            await ctx.send_status(Status.IDLE)
    
    async def handle_close(self, ctx: HandlerContext, response_text: str = "Closing my eyes.") -> None:
        """Close Gala's eyes - stop vision analysis."""
        try:
            await vision_live_service.stop()
            ctx.settings.vision_enabled = False
            settings_manager.save(ctx.settings)
            
            await ctx.send_response(
                ResponseType.VISION_STATUS,
                eyes_open=False,
                message=response_text
            )
            logger.info("Gala's eyes closed")
            
            # Record in conversation
            ctx.state.messages.append({"role": "user", "content": "[Vision command: close eyes]"})
            ctx.state.messages.append({"role": "assistant", "content": response_text})
            
            # Speak response
            await ctx.send_status(Status.SPEAKING)
            await self._speak(ctx, response_text)
            await ctx.send_status(Status.IDLE)
            
        except Exception as e:
            error_msg = f"Couldn't close my eyes: {str(e)}"
            await ctx.send_error(error_msg)
            await ctx.send_status(Status.IDLE)
    
    async def handle_describe(self, ctx: HandlerContext, prompt: str) -> None:
        """Describe what Gala can see right now."""
        try:
            await ctx.send_status(Status.PROCESSING)
            
            # Check if eyes are open
            if not ctx.settings.vision_enabled:
                error_msg = "I can't see anything right now - my eyes are closed. Say 'open your eyes' first."
                await ctx.send_response(ResponseType.LLM_COMPLETE, text=error_msg)
                ctx.state.messages.append({"role": "user", "content": prompt})
                ctx.state.messages.append({"role": "assistant", "content": error_msg})
                await ctx.send_status(Status.SPEAKING)
                await self._speak(ctx, error_msg)
                await ctx.send_status(Status.IDLE)
                return
            
            # Capture current frame
            frame_data = await vision_live_service.capture_frame()
            
            if "error" in frame_data or not frame_data.get("image"):
                error_msg = "I'm having trouble seeing right now. Let me try again in a moment."
                await ctx.send_response(ResponseType.LLM_COMPLETE, text=error_msg)
                ctx.state.messages.append({"role": "user", "content": prompt})
                ctx.state.messages.append({"role": "assistant", "content": error_msg})
                await ctx.send_status(Status.IDLE)
                return
            
            image_base64 = frame_data["image"]
            
            # Build vision prompt
            vision_prompt = prompt if prompt else "Describe what you see in detail. Focus on any people, their actions, expressions, and the environment."
            
            await ctx.send_status(Status.THINKING)
            
            # Send to vision model
            result = await vision_service.analyze_image(
                image_base64=image_base64,
                prompt=vision_prompt,
                model_type="general"
            )
            
            if result.get("success"):
                description = result.get("description", "I couldn't describe what I see.")
                description = clean_for_speech(description)
            else:
                description = f"I had trouble analyzing the image: {result.get('error', 'unknown error')}"
            
            # Send to frontend
            await ctx.send_response(ResponseType.LLM_COMPLETE, text=description)
            
            # Update conversation
            ctx.state.messages.append({"role": "user", "content": prompt or "[Asked to describe view]"})
            ctx.state.messages.append({"role": "assistant", "content": description})
            
            # Speak response
            await ctx.send_status(Status.SPEAKING)
            await self._speak(ctx, description)
            await ctx.send_status(Status.IDLE)
            
            logger.info(f"Described view: {description[:100]}...")
            
        except Exception as e:
            logger.error(f"Describe view error: {e}", exc_info=True)
            error_msg = f"I had trouble seeing: {str(e)}"
            await ctx.send_error(error_msg)
            await ctx.send_status(Status.IDLE)
    
    async def _handle_get_status(self, ctx: HandlerContext) -> None:
        """Get current vision status."""
        try:
            status = await vision_live_service.get_status()
            await ctx.send_response(ResponseType.VISION_UPDATE, data=status)
        except Exception as e:
            await ctx.send_response(
                ResponseType.VISION_UPDATE,
                data={"analyzing": False, "error": str(e)}
            )
    
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
            logger.error(f"Vision TTS error: {e}")
