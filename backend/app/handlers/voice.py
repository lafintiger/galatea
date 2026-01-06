"""Voice handler - STT, text input, LLM response, and TTS.

This handler processes:
- Audio data (speech-to-text)
- Text messages
- LLM response generation with streaming TTS
"""
import asyncio
import base64
import re

from .base import BaseHandler, HandlerContext
from ..core import (
    get_logger,
    clean_for_speech,
    detect_search_intent,
    detect_workspace_command,
    synthesize_tts,
    MessageType,
    ResponseType,
    Status,
)
from ..services.ollama import ollama_service, get_time_context
from ..services.wyoming import whisper_service
from ..services.parakeet import parakeet_service
from ..services.embedding import embedding_service
from ..services.user_profile import user_profile_service
from ..services.vision_live import vision_live_service
from ..services.domain_router import domain_router, Domain
from ..services.command_router import command_router

logger = get_logger(__name__)


class VoiceHandler(BaseHandler):
    """Handles voice input, text input, and response generation."""
    
    async def handle(self, ctx: HandlerContext) -> None:
        """Route to appropriate sub-handler based on message type."""
        msg_type = ctx.data.get("type")
        
        if msg_type == MessageType.AUDIO_DATA:
            await self._handle_audio(ctx)
        elif msg_type == MessageType.TEXT_MESSAGE:
            await self._handle_text(ctx)
        elif msg_type == MessageType.SPEAK_TEXT:
            await self._handle_speak(ctx)
    
    async def _handle_audio(self, ctx: HandlerContext) -> None:
        """Handle voice input from client."""
        # Decode base64 audio
        audio_b64 = ctx.data.get("audio", "")
        if not audio_b64:
            return
        
        audio_bytes = base64.b64decode(audio_b64)
        
        # Transcribe using selected STT provider
        await ctx.send_status(Status.PROCESSING)
        
        try:
            stt_provider = ctx.user_settings.stt_provider
            
            if stt_provider == "parakeet":
                # Try Parakeet first, fall back to Whisper if unavailable
                try:
                    if await parakeet_service.is_available():
                        transcript = await parakeet_service.transcribe(audio_bytes)
                        logger.debug("Transcription via Parakeet")
                    else:
                        logger.warning("Parakeet unavailable, falling back to Whisper")
                        transcript = await whisper_service.transcribe(audio_bytes)
                except Exception as e:
                    logger.warning(f"Parakeet error, falling back to Whisper: {e}")
                    transcript = await whisper_service.transcribe(audio_bytes)
            else:
                # Default: Whisper
                transcript = await whisper_service.transcribe(audio_bytes)
            
            if not transcript or not transcript.strip():
                await ctx.send_status(Status.IDLE)
                return
            
            # Send transcription to frontend
            await ctx.send_response(
                ResponseType.TRANSCRIPTION,
                text=transcript,
                final=True
            )
            
            # Process through command router
            await self._process_input(ctx, transcript, is_voice=True)
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}", exc_info=True)
            await ctx.send_error(f"Voice processing failed: {str(e)}")
            await ctx.send_status(Status.IDLE)
    
    async def _handle_text(self, ctx: HandlerContext) -> None:
        """Handle text input from client."""
        text = ctx.data.get("content", "").strip()
        if not text:
            return
        
        await self._process_input(ctx, text, is_voice=False)
    
    async def _handle_speak(self, ctx: HandlerContext) -> None:
        """Handle speak text request."""
        text = ctx.data.get("text", "")
        if text:
            await ctx.send_status(Status.SPEAKING)
            await self.speak_response(ctx, text)
            await ctx.send_status(Status.IDLE)
    
    async def _process_input(self, ctx: HandlerContext, text: str, is_voice: bool) -> None:
        """Process user input through command router and generate response."""
        from .vision import VisionHandler
        from .workspace import WorkspaceHandler
        from .search import SearchHandler
        from .mcp import MCPHandler
        
        # Try command router first
        try:
            logger.debug(f"Routing {'voice' if is_voice else 'text'}: '{text}'")
            routed_cmd, routed_response = await command_router.route(text)
            logger.debug(f"Route result: cmd={routed_cmd}, response={routed_response}")
            
            if routed_cmd:
                action = routed_cmd.get("action")
                logger.debug(f"Routed to action: {action}")
                
                # Workspace actions
                if action in ["add_todo", "add_note", "complete_todo", "log_data", 
                             "open_workspace", "read_todos", "read_notes", 
                             "clear_todos", "clear_notes"]:
                    handler = WorkspaceHandler()
                    await handler.handle_command(ctx, routed_cmd, routed_response)
                    return
                
                # Search
                elif action == "search_web":
                    query = routed_cmd.get("query", text)
                    handler = SearchHandler()
                    await handler.handle_search(ctx, query, text)
                    return
                
                # Vision
                elif action == "open_eyes":
                    handler = VisionHandler()
                    await handler.handle_open(ctx)
                    return
                elif action == "close_eyes":
                    handler = VisionHandler()
                    await handler.handle_close(ctx)
                    return
                elif action == "describe_view":
                    prompt = routed_cmd.get("prompt", "")
                    handler = VisionHandler()
                    await handler.handle_describe(ctx, prompt or text)
                    return
                
                # Clarify
                elif action == "clarify":
                    clarify_msg = routed_cmd.get("message", "Would you like me to add that to your todo list?")
                    ctx.state.messages.append({"role": "user", "content": text})
                    ctx.state.messages.append({"role": "assistant", "content": clarify_msg})
                    await ctx.send_response(ResponseType.LLM_COMPLETE, text=clarify_msg)
                    await ctx.send_status(Status.SPEAKING)
                    await self.speak_response(ctx, clarify_msg)
                    await ctx.send_status(Status.IDLE)
                    return
                
                # MCP Commands (Docker, Home Assistant)
                elif action.startswith("docker_") or action.startswith("ha_"):
                    handler = MCPHandler()
                    await handler.handle_command(ctx, routed_cmd)
                    return
                    
        except Exception as router_error:
            logger.warning(f"Routing error (falling back): {router_error}")
        
        # Fallback: Check for workspace commands via regex
        workspace_cmd, workspace_response = detect_workspace_command(text)
        if workspace_cmd:
            logger.debug(f"Detected workspace command: '{workspace_cmd['action']}'")
            handler = WorkspaceHandler()
            await handler.handle_command(ctx, workspace_cmd, workspace_response)
            return
        
        # Check for search intent
        is_search, search_query = detect_search_intent(text)
        if is_search and search_query:
            handler = SearchHandler()
            await handler.handle_search(ctx, search_query, text)
            return
        
        # Regular conversation
        ctx.state.messages.append({"role": "user", "content": text})
        await ctx.send_status(Status.PROCESSING)
        await self.generate_response(ctx)
    
    async def speak_response(self, ctx: HandlerContext, text: str) -> None:
        """Synthesize and send TTS audio."""
        if ctx.state.should_interrupt:
            return
        
        clean_text = clean_for_speech(text)
        if not clean_text:
            return
        
        try:
            audio_data = await synthesize_tts(
                text=clean_text,
                voice=ctx.settings.selected_voice,
                provider=getattr(ctx.settings, 'tts_provider', 'piper'),
                speed=getattr(ctx.settings, 'voice_speed', 1.0),
                variation=getattr(ctx.settings, 'voice_variation', 0.8),
                phoneme_var=getattr(ctx.settings, 'voice_phoneme_var', 0.6),
            )
            
            if audio_data and not ctx.state.should_interrupt:
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                await ctx.send_response(
                    ResponseType.AUDIO_CHUNK,
                    audio=audio_b64,
                    format="wav",
                    sentence=clean_text
                )
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    async def generate_response(self, ctx: HandlerContext) -> None:
        """Generate LLM response with streaming TTS."""
        ctx.state.is_speaking = True
        ctx.state.should_interrupt = False
        
        # Get context for system prompt
        time_context = get_time_context()
        user_profile_summary = user_profile_service.get_context_summary()
        
        # Vision context
        vision_context = ""
        if ctx.settings.vision_enabled:
            try:
                vision_status = await vision_live_service.get_status()
                if vision_status.get("analyzing"):
                    result = vision_status.get("latest_result", {})
                    if result.get("face_detected"):
                        parts = []
                        if result.get("emotion"):
                            parts.append(f"User appears {result['emotion']}")
                        if result.get("identity"):
                            parts.append(f"Recognized as {result['identity']}")
                        if parts:
                            vision_context = " | ".join(parts)
            except Exception as e:
                logger.debug(f"Vision context error: {e}")
        
        # Access control based on face recognition
        access_mode = "full"
        user_name = None
        
        if ctx.settings.vision_enabled:
            try:
                identity = await vision_live_service.get_current_identity()
                if identity:
                    if identity.get("is_owner"):
                        access_mode = "full"
                        user_name = identity.get("name")
                    elif identity.get("role") in ["friend", "family"]:
                        access_mode = "restricted"
                        user_name = identity.get("name")
                    else:
                        access_mode = "denied"
            except Exception as e:
                logger.debug(f"Identity check error: {e}")
        
        # Build system prompt
        user_location = getattr(ctx.settings, 'user_location', '')
        system_prompt = ollama_service.build_system_prompt(
            name=ctx.settings.assistant_name,
            nickname=ctx.settings.assistant_nickname,
            style=ctx.settings.response_style,
            time_context=time_context,
            user_profile=user_profile_summary if user_profile_summary else None,
            user_location=user_location,
        )
        
        if access_mode == "restricted":
            system_prompt += f"\n\nACCESS MODE: You are speaking with {user_name}, a friend/family member of your owner. Be helpful but DO NOT share any personal information about your owner."
        
        if vision_context:
            system_prompt += f"\n\nVISUAL AWARENESS:\n{vision_context}\nUse this visual context naturally."
        
        # Startup greeting context
        startup_greeting = vision_live_service.get_startup_greeting_context()
        is_first_message = len([m for m in ctx.state.messages if m.get("role") == "user"]) <= 1
        
        if startup_greeting and is_first_message:
            system_prompt += f"\n\nSTARTUP AWARENESS:\n{startup_greeting}\nUse this context to give a warm, personalized greeting."
        
        # RAG context
        try:
            user_messages = [m for m in ctx.state.messages if m.get("role") == "user"]
            if user_messages:
                last_user_msg = user_messages[-1].get("content", "")
                similar = await embedding_service.search_similar(last_user_msg, limit=3)
                
                if similar:
                    rag_parts = []
                    for item in similar:
                        if item.get("score", 0) < 0.95:
                            rag_parts.append(f"- {item['role'].title()}: {item['content'][:200]}...")
                    
                    if rag_parts:
                        system_prompt += "\n\n[Relevant context from past conversations:]\n" + "\n".join(rag_parts)
        except Exception as e:
            logger.debug(f"RAG retrieval error: {e}")
        
        # Domain routing
        active_model = ctx.settings.selected_model
        if getattr(ctx.settings, 'domain_routing_enabled', False):
            try:
                user_messages = [m for m in ctx.state.messages if m.get("role") == "user"]
                if user_messages:
                    last_msg = user_messages[-1].get("content", "")
                    detected_domain, confidence, voice_override = domain_router.detect_domain(last_msg)
                    
                    if detected_domain != Domain.GENERAL and confidence >= 0.6:
                        spec_models = ctx.settings.specialist_models
                        model_map = {
                            Domain.MEDICAL: spec_models.medical,
                            Domain.LEGAL: spec_models.legal,
                            Domain.CODING: spec_models.coding,
                            Domain.MATH: spec_models.math,
                            Domain.FINANCE: spec_models.finance,
                            Domain.SCIENCE: spec_models.science,
                            Domain.CREATIVE: spec_models.creative,
                            Domain.KNOWLEDGE: spec_models.knowledge,
                            Domain.PERSONALITY: spec_models.personality,
                        }
                        
                        configured_model = model_map.get(detected_domain, "")
                        
                        if configured_model and configured_model != active_model:
                            logger.info(f"Domain routing: {detected_domain.value} -> {configured_model}")
                            
                            if voice_override:
                                ctx.settings.selected_voice = voice_override
                            
                            handoff_msg = domain_router.get_handoff_message(detected_domain)
                            await ctx.send_response(
                                ResponseType.DOMAIN_SWITCH,
                                domain=detected_domain.value,
                                model=configured_model,
                                message=handoff_msg,
                                confidence=confidence,
                                voice_override=voice_override
                            )
                            
                            active_model = configured_model
            except Exception as e:
                logger.debug(f"Domain routing error: {e}")
            
            routing_prompt = domain_router.get_routing_prompt_addition()
            if routing_prompt:
                system_prompt += routing_prompt
        
        # Stream LLM response with sentence-level TTS
        full_response = ""
        sentence_buffer = ""
        first_audio_sent = False
        in_think_block = False
        think_buffer = ""
        
        await ctx.send_status(Status.PROCESSING)
        
        try:
            async for chunk in ollama_service.chat_stream(
                messages=ctx.state.messages,
                model=active_model,
                system_prompt=system_prompt,
                enable_thinking=False
            ):
                if ctx.state.should_interrupt:
                    break
                
                # Track <think> blocks
                think_buffer += chunk
                
                if '<think>' in think_buffer.lower() or '<thinking>' in think_buffer.lower():
                    in_think_block = True
                    think_buffer = re.sub(r'<think(?:ing)?>', '', think_buffer, flags=re.IGNORECASE)
                
                if '</think>' in think_buffer.lower() or '</thinking>' in think_buffer.lower():
                    in_think_block = False
                    think_buffer = re.sub(r'</think(?:ing)?>', '', think_buffer, flags=re.IGNORECASE)
                    think_buffer = ""
                    continue
                
                if in_think_block:
                    continue
                
                # Display chunk
                display_chunk = chunk
                display_chunk = re.sub(r'<think(?:ing)?>', '', display_chunk, flags=re.IGNORECASE)
                display_chunk = re.sub(r'</think(?:ing)?>', '', display_chunk, flags=re.IGNORECASE)
                
                if display_chunk:
                    full_response += display_chunk
                    await ctx.send_response(ResponseType.LLM_CHUNK, text=display_chunk)
                    
                    sentence_buffer += display_chunk
                    
                    # Check for sentence boundaries
                    sentence_ends = ['.', '!', '?', '。', '！', '？']
                    for end in sentence_ends:
                        if end in sentence_buffer:
                            parts = sentence_buffer.split(end)
                            for i, part in enumerate(parts[:-1]):
                                sentence = part.strip() + end
                                if sentence and len(sentence) > 2:
                                    if not first_audio_sent:
                                        await ctx.send_status(Status.SPEAKING)
                                        first_audio_sent = True
                                    
                                    clean_sentence = clean_for_speech(sentence)
                                    if clean_sentence and not ctx.state.should_interrupt:
                                        try:
                                            audio_data = await synthesize_tts(
                                                text=clean_sentence,
                                                voice=ctx.settings.selected_voice,
                                                provider=getattr(ctx.settings, 'tts_provider', 'piper'),
                                                speed=getattr(ctx.settings, 'voice_speed', 1.0),
                                            )
                                            
                                            if audio_data and not ctx.state.should_interrupt:
                                                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                                                await ctx.send_response(
                                                    ResponseType.AUDIO_CHUNK,
                                                    audio=audio_b64,
                                                    format="wav",
                                                    sentence=clean_sentence
                                                )
                                        except Exception as e:
                                            logger.error(f"TTS error: {e}")
                            
                            sentence_buffer = parts[-1]
                            break
            
            # Handle remaining text
            if sentence_buffer.strip() and not ctx.state.should_interrupt:
                clean_remainder = clean_for_speech(sentence_buffer.strip())
                if clean_remainder:
                    if not first_audio_sent:
                        await ctx.send_status(Status.SPEAKING)
                    
                    try:
                        audio_data = await synthesize_tts(
                            text=clean_remainder,
                            voice=ctx.settings.selected_voice,
                            provider=getattr(ctx.settings, 'tts_provider', 'piper'),
                            speed=getattr(ctx.settings, 'voice_speed', 1.0),
                        )
                        
                        if audio_data and not ctx.state.should_interrupt:
                            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                            await ctx.send_response(
                                ResponseType.AUDIO_CHUNK,
                                audio=audio_b64,
                                format="wav",
                                sentence=clean_remainder
                            )
                    except Exception as e:
                        logger.error(f"TTS error for remainder: {e}")
            
            # Clean emojis from final response
            cleaned_response = clean_for_speech(full_response)
            await ctx.send_response(ResponseType.LLM_COMPLETE, text=cleaned_response)
            
            ctx.state.messages.append({"role": "assistant", "content": cleaned_response})
        
        except Exception as e:
            logger.error(f"LLM error: {e}", exc_info=True)
            await ctx.send_error(f"LLM generation failed: {str(e)}")
        
        finally:
            ctx.state.is_speaking = False
            await ctx.send_status(Status.IDLE)
