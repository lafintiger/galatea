"""WebSocket endpoint for real-time voice conversation.

This module handles the main WebSocket connection for:
- Voice input processing (STT)
- Text input processing
- LLM response generation
- TTS audio streaming
- Vision commands
- Workspace commands
- Web search
"""
import asyncio
import base64
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core import (
    get_logger,
    clean_for_speech,
    detect_search_intent,
    detect_vision_command,
    detect_workspace_command,
    synthesize_tts,
)
from ..services.ollama import ollama_service, get_time_context
from ..services.wyoming import whisper_service
from ..services.settings_manager import settings_manager
from ..services.web_search import web_search
from ..services.embedding import embedding_service
from ..services.background_worker import background_worker
from ..services.user_profile import user_profile_service
from ..services.vision_live import vision_live_service
from ..services.vision import vision_service
from ..services.domain_router import domain_router, Domain
from ..services.command_router import command_router
from ..services.docker_service import docker_service
from ..services.homeassistant_service import ha_service
from ..models.schemas import UserSettings

logger = get_logger(__name__)

router = APIRouter()


class ConversationState:
    """Tracks conversation state for a WebSocket connection."""
    
    def __init__(self):
        self.messages: list[dict] = []
        self.is_speaking = False
        self.should_interrupt = False
        self.current_audio_task: asyncio.Task | None = None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for voice conversation."""
    await websocket.accept()
    state = ConversationState()
    user_settings = settings_manager.load()
    
    logger.info("Client connected")
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "state": "idle",
            "settings": user_settings.model_dump()
        })
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            # Record user activity (resets idle timer for background embedding)
            background_worker.record_activity()
            
            if msg_type == "audio_data":
                await handle_voice_input(websocket, state, data, user_settings)
            
            elif msg_type == "text_message":
                await handle_text_input(websocket, state, data, user_settings)
            
            elif msg_type == "web_search":
                await handle_web_search(websocket, state, data, user_settings)
            
            elif msg_type == "interrupt":
                state.should_interrupt = True
                if state.current_audio_task:
                    state.current_audio_task.cancel()
                await websocket.send_json({"type": "interrupted"})
            
            elif msg_type == "settings_update":
                new_settings = UserSettings(**data.get("settings", {}))
                user_settings = settings_manager.save(new_settings)
                await websocket.send_json({
                    "type": "settings_updated",
                    "settings": user_settings.model_dump()
                })
            
            elif msg_type == "clear_history":
                state.messages = []
                await websocket.send_json({"type": "history_cleared"})
            
            elif msg_type == "speak_text":
                text = data.get("text", "")
                if text:
                    await websocket.send_json({"type": "status", "state": "speaking"})
                    await speak_response(websocket, state, text, user_settings)
                    await websocket.send_json({"type": "status", "state": "idle"})
            
            elif msg_type == "open_eyes":
                try:
                    await vision_live_service.start()
                    user_settings.vision_enabled = True
                    settings_manager.save(user_settings)
                    await websocket.send_json({
                        "type": "vision_status",
                        "eyes_open": True,
                        "message": "I can see you now"
                    })
                    logger.info("Gala's eyes opened")
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Could not open eyes: {str(e)}"
                    })
            
            elif msg_type == "close_eyes":
                try:
                    await vision_live_service.stop()
                    user_settings.vision_enabled = False
                    settings_manager.save(user_settings)
                    await websocket.send_json({
                        "type": "vision_status",
                        "eyes_open": False,
                        "message": "Eyes closed"
                    })
                    logger.info("Gala's eyes closed")
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Could not close eyes: {str(e)}"
                    })
            
            elif msg_type == "workspace_result":
                await handle_workspace_result(websocket, state, data, user_settings)
            
            elif msg_type == "get_vision_status":
                try:
                    status = await vision_live_service.get_status()
                    await websocket.send_json({
                        "type": "vision_update",
                        "data": status
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "vision_update",
                        "data": {"analyzing": False, "error": str(e)}
                    })
    
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close(code=1011, reason=str(e))


async def handle_voice_input(
    websocket: WebSocket,
    state: ConversationState,
    data: dict,
    user_settings: UserSettings
):
    """Handle voice input from client."""
    # Decode base64 audio
    audio_b64 = data.get("audio", "")
    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid audio data"
        })
        return
    
    await websocket.send_json({"type": "status", "state": "processing"})
    
    try:
        # Transcribe audio
        transcript = await whisper_service.transcribe(audio_bytes)
        
        if not transcript.strip():
            await websocket.send_json({"type": "status", "state": "idle"})
            return
        
        # Send transcription
        await websocket.send_json({
            "type": "transcription",
            "text": transcript,
            "final": True
        })
        
        # Try command router first (Ministral)
        logger.debug(f"Routing voice transcript: '{transcript}'")
        try:
            routed_cmd, routed_response = await command_router.route(transcript)
            logger.debug(f"Route result: cmd={routed_cmd}, response={routed_response}")
            if routed_cmd:
                action = routed_cmd.get("action")
                logger.debug(f"Routed to action: {action}")
                
                if action in ["add_todo", "add_note", "complete_todo", "log_data", "open_workspace", "read_todos", "read_notes", "clear_todos", "clear_notes"]:
                    await handle_workspace_command(websocket, routed_cmd, routed_response, user_settings, state)
                    return
                elif action == "search_web":
                    query = routed_cmd.get("query", transcript)
                    await handle_web_search(websocket, state, {"query": query, "original_request": transcript}, user_settings)
                    return
                elif action == "open_eyes":
                    await handle_vision_command(websocket, "open", "Opening my eyes...", user_settings, state)
                    return
                elif action == "close_eyes":
                    await handle_vision_command(websocket, "close", "Closing my eyes.", user_settings, state)
                    return
                elif action == "clarify":
                    clarify_msg = routed_cmd.get("message", "Would you like me to add that to your todo list?")
                    state.messages.append({"role": "user", "content": transcript})
                    state.messages.append({"role": "assistant", "content": clarify_msg})
                    await websocket.send_json({"type": "llm_complete", "text": clarify_msg})
                    await websocket.send_json({"type": "status", "state": "speaking"})
                    await speak_response(websocket, state, clarify_msg, user_settings)
                    await websocket.send_json({"type": "status", "state": "idle"})
                    return
                # MCP Commands (Docker, Home Assistant)
                elif action.startswith("docker_") or action.startswith("ha_"):
                    await handle_mcp_command(websocket, routed_cmd, user_settings, state)
                    return
        except Exception as router_error:
            logger.warning(f"Command router error (falling back to regex): {router_error}")
        
        # Fallback: Regex-based detection
        vision_cmd, vision_response = detect_vision_command(transcript)
        if vision_cmd:
            logger.debug(f"Detected vision command: '{vision_cmd}'")
            await handle_vision_command(websocket, vision_cmd, vision_response, user_settings, state)
            return
        
        workspace_cmd, workspace_response = detect_workspace_command(transcript)
        if workspace_cmd:
            logger.debug(f"Detected workspace command: '{workspace_cmd['action']}'")
            await handle_workspace_command(websocket, workspace_cmd, workspace_response, user_settings, state)
            return
        
        is_search, search_query = detect_search_intent(transcript)
        if is_search and search_query:
            logger.debug(f"Detected search intent: '{search_query}'")
            await handle_web_search(websocket, state, {"query": search_query, "original_request": transcript}, user_settings)
            return
        
        # Regular conversation
        state.messages.append({"role": "user", "content": transcript})
        await generate_response(websocket, state, user_settings)
    
    except Exception as e:
        logger.error(f"Voice processing error: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": f"Voice processing failed: {str(e)}"
        })
        await websocket.send_json({"type": "status", "state": "idle"})


async def handle_text_input(
    websocket: WebSocket,
    state: ConversationState,
    data: dict,
    user_settings: UserSettings
):
    """Handle text input from client."""
    text = data.get("content", "").strip()
    
    if not text:
        return
    
    # Try command router first
    try:
        routed_cmd, routed_response = await command_router.route(text)
        if routed_cmd:
            action = routed_cmd.get("action")
            logger.debug(f"Text routed to action: {action}")
            
            if action in ["add_todo", "add_note", "complete_todo", "log_data", "open_workspace", "read_todos", "read_notes", "clear_todos", "clear_notes"]:
                await handle_workspace_command(websocket, routed_cmd, routed_response, user_settings, state)
                return
            elif action == "search_web":
                query = routed_cmd.get("query", text)
                await handle_web_search(websocket, state, {"query": query, "original_request": text}, user_settings)
                return
            elif action == "open_eyes":
                await handle_vision_command(websocket, "open", "Opening my eyes...", user_settings, state)
                return
            elif action == "close_eyes":
                await handle_vision_command(websocket, "close", "Closing my eyes.", user_settings, state)
                return
            elif action == "clarify":
                clarify_msg = routed_cmd.get("message", "Would you like me to add that to your todo list?")
                state.messages.append({"role": "user", "content": text})
                state.messages.append({"role": "assistant", "content": clarify_msg})
                await websocket.send_json({"type": "llm_complete", "text": clarify_msg})
                await websocket.send_json({"type": "status", "state": "speaking"})
                await speak_response(websocket, state, clarify_msg, user_settings)
                await websocket.send_json({"type": "status", "state": "idle"})
                return
            # MCP Commands (Docker, Home Assistant)
            elif action.startswith("docker_") or action.startswith("ha_"):
                await handle_mcp_command(websocket, routed_cmd, user_settings, state)
                return
    except Exception as router_error:
        logger.warning(f"Text routing error (falling back): {router_error}")
    
    # Fallback: Regex-based detection
    vision_cmd, vision_response = detect_vision_command(text)
    if vision_cmd:
        await handle_vision_command(websocket, vision_cmd, vision_response, user_settings, state)
        return
    
    logger.debug(f"Checking for workspace command in: '{text}'")
    workspace_cmd, workspace_response = detect_workspace_command(text)
    logger.debug(f"Workspace detection result: {workspace_cmd}")
    if workspace_cmd:
        logger.debug(f"Detected workspace command: '{workspace_cmd['action']}'")
        await handle_workspace_command(websocket, workspace_cmd, workspace_response, user_settings, state)
        return
    
    is_search, search_query = detect_search_intent(text)
    if is_search and search_query:
        await handle_web_search(websocket, state, {"query": search_query, "original_request": text}, user_settings)
        return
    
    # Regular conversation
    state.messages.append({"role": "user", "content": text})
    await websocket.send_json({"type": "status", "state": "processing"})
    await generate_response(websocket, state, user_settings)


async def handle_web_search(
    websocket: WebSocket,
    state: ConversationState,
    data: dict,
    user_settings: UserSettings
):
    """Handle web search request."""
    query = data.get("query", "").strip()
    provider = data.get("provider", "auto")
    follow_up = data.get("follow_up", "")
    original_request = data.get("original_request", "")
    
    if not query:
        await websocket.send_json({"type": "error", "message": "Search query required"})
        return
    
    await websocket.send_json({"type": "status", "state": "searching"})
    await websocket.send_json({"type": "search_start", "query": query})
    
    logger.info(f"Performing web search: '{query}'")
    
    try:
        search_results = await web_search.search(query, provider=provider)
        
        await websocket.send_json({
            "type": "search_results",
            "data": search_results
        })
        
        formatted_results = web_search.format_results_for_llm(search_results)
        
        if original_request:
            user_message = f"User said: \"{original_request}\"\n\n"
            user_message += f"[I searched the web for: {query}]\n\n{formatted_results}\n\n"
            user_message += "Please answer the user's request based on these search results. Be conversational and helpful."
        elif follow_up:
            user_message = f"[Web Search: {query}]\n\n{formatted_results}\n\nUser question: {follow_up}"
        else:
            user_message = f"[Web Search: {query}]\n\n{formatted_results}\n\nPlease summarize these search results for me in a helpful way."
        
        state.messages.append({"role": "user", "content": user_message})
        
        await websocket.send_json({"type": "status", "state": "thinking"})
        await generate_response(websocket, state, user_settings)
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Search failed: {str(e)}"
        })
        await websocket.send_json({"type": "status", "state": "idle"})


async def handle_workspace_command(
    websocket: WebSocket,
    command: dict,
    response_text: str,
    user_settings: UserSettings,
    state: ConversationState
):
    """Handle workspace commands (notes, todos, data logging).
    
    We don't speak confirmation here - frontend confirms when action succeeds.
    """
    try:
        action = command.get("action")
        content = command.get("content", "")
        
        await websocket.send_json({
            "type": "workspace_command",
            "command": command,
            "confirmation_text": response_text
        })
        logger.debug(f"Sent workspace command to frontend: {command}")
        
        state.messages.append({
            "role": "user",
            "content": f"[Workspace: {action}] {content}"
        })
        
        await websocket.send_json({"type": "status", "state": "processing"})
        
    except Exception as e:
        error_msg = f"Couldn't complete workspace action: {str(e)}"
        logger.error(error_msg)
        await websocket.send_json({"type": "error", "message": error_msg})
        await websocket.send_json({"type": "status", "state": "idle"})


async def handle_workspace_result(
    websocket: WebSocket,
    state: ConversationState,
    data: dict,
    user_settings: UserSettings
):
    """Handle workspace action result from frontend."""
    success = data.get("success", False)
    action = data.get("action", "")
    confirmation_text = data.get("confirmation_text", "")
    error = data.get("error", "")
    
    logger.debug(f"Workspace result: success={success}, action={action}")
    
    if success and confirmation_text:
        state.messages.append({"role": "assistant", "content": confirmation_text})
        
        logger.debug(f"Sending llm_complete: '{confirmation_text[:50]}...'")
        await websocket.send_json({"type": "llm_complete", "text": confirmation_text})
        
        await websocket.send_json({"type": "status", "state": "speaking"})
        try:
            audio_data = await synthesize_tts(
                text=confirmation_text,
                voice=user_settings.selected_voice,
                provider=getattr(user_settings, 'tts_provider', 'piper'),
                speed=getattr(user_settings, 'voice_speed', 1.0)
            )
            if audio_data:
                await websocket.send_json({
                    "type": "audio_chunk",
                    "audio": base64.b64encode(audio_data).decode('utf-8'),
                    "sentence": confirmation_text
                })
        except Exception as tts_error:
            logger.error(f"Workspace TTS error: {tts_error}")
        await websocket.send_json({"type": "status", "state": "idle"})
    elif not success:
        error_msg = f"Sorry, I couldn't {action.replace('_', ' ')}. {error}"
        logger.warning(f"Workspace action failed: {error_msg}")
        state.messages.append({"role": "assistant", "content": error_msg})
        await websocket.send_json({"type": "llm_complete", "text": error_msg})
        await websocket.send_json({"type": "status", "state": "speaking"})
        try:
            audio_data = await synthesize_tts(
                text=error_msg,
                voice=user_settings.selected_voice,
                provider=getattr(user_settings, 'tts_provider', 'piper'),
                speed=getattr(user_settings, 'voice_speed', 1.0)
            )
            if audio_data:
                await websocket.send_json({
                    "type": "audio_chunk",
                    "audio": base64.b64encode(audio_data).decode('utf-8'),
                    "sentence": error_msg
                })
        except Exception as tts_error:
            logger.error(f"Workspace TTS error: {tts_error}")
        await websocket.send_json({"type": "status", "state": "idle"})
    else:
        await websocket.send_json({"type": "status", "state": "idle"})


async def handle_vision_command(
    websocket: WebSocket,
    command: str,
    response_text: str,
    user_settings: UserSettings,
    state: ConversationState
):
    """Handle vision open/close commands."""
    try:
        if command == "open":
            await vision_live_service.start()
            user_settings.vision_enabled = True
            settings_manager.save(user_settings)
            await websocket.send_json({
                "type": "vision_status",
                "eyes_open": True,
                "message": response_text
            })
            logger.info("Gala's eyes opened via voice command")
            
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
        elif command == "close":
            await vision_live_service.stop()
            user_settings.vision_enabled = False
            settings_manager.save(user_settings)
            await websocket.send_json({
                "type": "vision_status",
                "eyes_open": False,
                "message": response_text
            })
            logger.info("Gala's eyes closed via voice command")
        
        state.messages.append({"role": "user", "content": f"[Vision command: {command} eyes]"})
        state.messages.append({"role": "assistant", "content": response_text})
        
        await websocket.send_json({"type": "status", "state": "speaking"})
        try:
            audio_data = await synthesize_tts(
                text=response_text,
                voice=user_settings.selected_voice,
                provider=getattr(user_settings, 'tts_provider', 'piper'),
                speed=getattr(user_settings, 'voice_speed', 1.0)
            )
            if audio_data:
                await websocket.send_json({
                    "type": "audio_chunk",
                    "audio": base64.b64encode(audio_data).decode('utf-8'),
                    "sentence": response_text
                })
        except Exception as tts_error:
            logger.error(f"Vision TTS error: {tts_error}")
        await websocket.send_json({"type": "status", "state": "idle"})
        
    except Exception as e:
        error_msg = f"Couldn't {'open' if command == 'open' else 'close'} my eyes: {str(e)}"
        await websocket.send_json({"type": "error", "message": error_msg})


async def handle_mcp_command(
    websocket: WebSocket,
    command: dict,
    user_settings: UserSettings,
    state: ConversationState
):
    """Handle MCP commands (Docker, Home Assistant, etc.)."""
    action = command.get("action", "")
    
    try:
        await websocket.send_json({"type": "status", "state": "processing"})
        
        result_text = ""
        
        # =========================================
        # Docker Commands
        # =========================================
        if action == "docker_list":
            if not docker_service.is_available:
                result_text = "I can't connect to Docker right now. Make sure Docker is running."
            else:
                containers = await docker_service.list_containers(all_containers=command.get("all", True))
                if not containers:
                    result_text = "No Docker containers found."
                else:
                    running = [c for c in containers if c.status == 'running']
                    stopped = [c for c in containers if c.status != 'running']
                    
                    lines = []
                    if running:
                        lines.append(f"Running ({len(running)}): " + ", ".join(c.name for c in running))
                    if stopped:
                        lines.append(f"Stopped ({len(stopped)}): " + ", ".join(c.name for c in stopped))
                    result_text = " ".join(lines)
        
        elif action == "docker_restart":
            container_name = command.get("container", "")
            if not docker_service.is_available:
                result_text = "I can't connect to Docker right now."
            else:
                # Try to find container by partial name
                full_name = docker_service.find_container_by_partial_name(container_name)
                if not full_name:
                    result_text = f"I couldn't find a container named {container_name}."
                else:
                    success, msg = await docker_service.restart_container(full_name)
                    result_text = msg
        
        elif action == "docker_status":
            container_name = command.get("container", "")
            if not docker_service.is_available:
                result_text = "I can't connect to Docker right now."
            else:
                full_name = docker_service.find_container_by_partial_name(container_name)
                if not full_name:
                    result_text = f"I couldn't find a container named {container_name}."
                else:
                    health = await docker_service.get_container_health(full_name)
                    if 'error' in health:
                        result_text = health['error']
                    else:
                        status = "running" if health['healthy'] else "stopped"
                        result_text = f"{health['name']} is {status}. CPU: {health['cpu_percent']}%, Memory: {health['memory_mb']:.0f} MB."
        
        elif action == "docker_logs":
            container_name = command.get("container", "")
            lines = command.get("lines", 20)
            if not docker_service.is_available:
                result_text = "I can't connect to Docker right now."
            else:
                full_name = docker_service.find_container_by_partial_name(container_name)
                if not full_name:
                    result_text = f"I couldn't find a container named {container_name}."
                else:
                    success, logs = await docker_service.get_logs(full_name, tail=lines)
                    if success:
                        # Summarize logs rather than reading them all
                        log_lines = logs.strip().split('\n')
                        if len(log_lines) > 5:
                            result_text = f"Here are the last {len(log_lines)} log lines from {full_name}. The most recent entry says: {log_lines[-1][:100]}"
                        else:
                            result_text = f"Logs from {full_name}: {logs[:200]}"
                    else:
                        result_text = logs
        
        # =========================================
        # Home Assistant Commands
        # =========================================
        elif action == "ha_turn_on":
            device = command.get("device", "")
            brightness = command.get("brightness")
            
            if not ha_service.is_configured:
                result_text = "Home Assistant is not configured. Set HA_URL and HA_TOKEN in your environment."
            else:
                # Find the entity
                lights = await ha_service.get_lights()
                entity = ha_service.find_entity_by_name(lights, device)
                
                if not entity:
                    # Try switches too
                    switches = await ha_service.get_switches()
                    entity = ha_service.find_entity_by_name(switches, device)
                
                if not entity:
                    result_text = f"I couldn't find a device called {device}."
                else:
                    if brightness:
                        success, msg = await ha_service.set_brightness(entity.entity_id, brightness)
                    else:
                        success, msg = await ha_service.turn_on(entity.entity_id)
                    result_text = f"Turned on {entity.friendly_name}." if success else msg
        
        elif action == "ha_turn_off":
            device = command.get("device", "")
            
            if not ha_service.is_configured:
                result_text = "Home Assistant is not configured."
            else:
                lights = await ha_service.get_lights()
                entity = ha_service.find_entity_by_name(lights, device)
                
                if not entity:
                    switches = await ha_service.get_switches()
                    entity = ha_service.find_entity_by_name(switches, device)
                
                if not entity:
                    result_text = f"I couldn't find a device called {device}."
                else:
                    success, msg = await ha_service.turn_off(entity.entity_id)
                    result_text = f"Turned off {entity.friendly_name}." if success else msg
        
        elif action == "ha_set_temperature":
            temperature = command.get("temperature")
            device = command.get("device")
            
            if not ha_service.is_configured:
                result_text = "Home Assistant is not configured."
            else:
                climate_devices = await ha_service.get_climate()
                if not climate_devices:
                    result_text = "I couldn't find any thermostats."
                else:
                    # Use first thermostat if device not specified
                    if device:
                        entity = ha_service.find_entity_by_name(climate_devices, device)
                    else:
                        entity = climate_devices[0]
                    
                    if not entity:
                        result_text = f"I couldn't find a thermostat called {device}."
                    else:
                        success, msg = await ha_service.set_temperature(entity.entity_id, temperature)
                        result_text = f"Set {entity.friendly_name} to {temperature} degrees." if success else msg
        
        elif action == "ha_get_state":
            device = command.get("device", "")
            
            if not ha_service.is_configured:
                result_text = "Home Assistant is not configured."
            else:
                states = await ha_service.get_states()
                entity = ha_service.find_entity_by_name(states, device)
                
                if not entity:
                    result_text = f"I couldn't find a device called {device}."
                else:
                    result_text = f"{entity.friendly_name} is {entity.state}."
        
        elif action == "ha_list_devices":
            device_type = command.get("type", "all")
            
            if not ha_service.is_configured:
                result_text = "Home Assistant is not configured."
            else:
                if device_type == "light":
                    devices = await ha_service.get_lights()
                elif device_type == "switch":
                    devices = await ha_service.get_switches()
                elif device_type == "climate":
                    devices = await ha_service.get_climate()
                elif device_type == "lock":
                    devices = await ha_service.get_locks()
                else:
                    # Get a mix of common device types
                    devices = []
                    devices.extend(await ha_service.get_lights())
                    devices.extend(await ha_service.get_switches())
                    devices.extend(await ha_service.get_climate())
                
                if not devices:
                    result_text = f"No {device_type} devices found."
                else:
                    names = [d.friendly_name for d in devices[:10]]  # Limit to 10
                    result_text = f"Found {len(devices)} devices: " + ", ".join(names)
                    if len(devices) > 10:
                        result_text += f" and {len(devices) - 10} more."
        
        else:
            result_text = "I don't know how to handle that command yet."
        
        # Send result and speak it
        state.messages.append({"role": "user", "content": f"[MCP Command: {action}]"})
        state.messages.append({"role": "assistant", "content": result_text})
        
        await websocket.send_json({"type": "llm_complete", "text": result_text})
        await websocket.send_json({"type": "status", "state": "speaking"})
        await speak_response(websocket, state, result_text, user_settings)
        await websocket.send_json({"type": "status", "state": "idle"})
        
    except Exception as e:
        logger.error(f"MCP command error: {e}", exc_info=True)
        error_msg = f"Sorry, I had trouble with that: {str(e)}"
        await websocket.send_json({"type": "error", "message": error_msg})
        await websocket.send_json({"type": "status", "state": "idle"})


async def speak_response(
    websocket: WebSocket,
    state: ConversationState,
    text: str,
    user_settings: UserSettings
):
    """Synthesize and send TTS audio for a text response."""
    clean_text = clean_for_speech(text)
    if not clean_text:
        return
    
    try:
        audio_data = await synthesize_tts(
            text=clean_text,
            voice=user_settings.selected_voice,
            provider=getattr(user_settings, 'tts_provider', 'piper'),
            speed=getattr(user_settings, 'voice_speed', 1.0)
        )
        if audio_data:
            await websocket.send_json({
                "type": "audio_chunk",
                "audio": base64.b64encode(audio_data).decode('utf-8'),
                "sentence": clean_text
            })
    except Exception as e:
        logger.error(f"TTS synthesis error: {e}")


async def generate_response(
    websocket: WebSocket,
    state: ConversationState,
    user_settings: UserSettings
):
    """Generate LLM response with streaming TTS."""
    state.should_interrupt = False
    
    # ============== ACCESS CONTROL CHECK ==============
    access_mode = "full"
    current_identity = ""
    
    if user_settings.vision_enabled and vision_live_service.is_active:
        try:
            has_owner = await vision_live_service.has_owner()
            
            if has_owner:
                # IMPORTANT: Refresh vision status to get latest face recognition result
                # Without this, _current_result may be stale or None
                await vision_live_service.get_status()
                
                name, role = vision_live_service.get_current_identity()
                logger.debug(f"Face recognition: name='{name}', role='{role}'")
                
                if role == "owner":
                    access_mode = "full"
                    current_identity = name
                elif role in ["friend", "family"]:
                    access_mode = "restricted"
                    current_identity = name
                elif not name:
                    # No face detected or recognition failed - give benefit of doubt
                    logger.debug("No face detected, allowing access")
                    access_mode = "full"
                else:
                    access_mode = "denied"
                    
        except Exception as e:
            logger.warning(f"Access control check failed: {e}")
            access_mode = "full"
    
    # Handle denied access
    if access_mode == "denied":
        await websocket.send_json({"type": "status", "state": "processing"})
        
        denial_message = "I don't recognize you. I'm Gala, a personal AI assistant. I can only have conversations with my owner. Please ask them to introduce you if you'd like to chat!"
        
        await websocket.send_json({"type": "llm_chunk", "text": denial_message})
        await websocket.send_json({"type": "llm_complete", "text": denial_message})
        
        try:
            audio_data = await synthesize_tts(
                text=denial_message,
                voice=user_settings.selected_voice,
                provider=getattr(user_settings, 'tts_provider', 'piper'),
                speed=getattr(user_settings, 'voice_speed', 1.0),
            )
            if audio_data:
                await websocket.send_json({
                    "type": "audio_chunk",
                    "audio": base64.b64encode(audio_data).decode('utf-8'),
                    "sentence": denial_message
                })
        except Exception as e:
            logger.error(f"TTS error for denial: {e}")
        
        await websocket.send_json({"type": "status", "state": "idle"})
        return
    
    # Get user profile (only for owner)
    user_profile_summary = ""
    user_name = "User"
    
    if access_mode == "full":
        user_profile_summary = user_profile_service.get_profile_summary()
        user_name = user_profile_service.load_profile().user_name or "User"
    elif access_mode == "restricted":
        user_name = current_identity if current_identity else "Guest"
        user_profile_summary = ""
    
    # Get vision context
    vision_context = ""
    if user_settings.vision_enabled and vision_live_service.is_active:
        vision_context = vision_live_service.get_emotion_context()
    
    # Build system prompt
    time_context = get_time_context()
    system_prompt = ollama_service.build_system_prompt(
        assistant_name=user_settings.assistant_name,
        nickname=user_settings.assistant_nickname,
        response_style=user_settings.response_style,
        user_name=user_name,
        time_context=time_context,
        user_profile=user_profile_summary if user_profile_summary else None,
    )
    
    if access_mode == "restricted":
        system_prompt += f"\n\nACCESS MODE: You are speaking with {user_name}, a friend/family member of your owner. Be helpful but DO NOT share any personal information about your owner. DO NOT reference previous conversations or the owner's profile. Treat this as a casual conversation with a guest."
    
    if vision_context:
        system_prompt += f"\n\nVISUAL AWARENESS:\n{vision_context}\nUse this visual context naturally - acknowledge emotions appropriately but don't constantly reference what you see."
    
    # Startup context for greeting
    startup_greeting = vision_live_service.get_startup_greeting_context()
    is_first_message = len([m for m in state.messages if m.get("role") == "user"]) <= 1
    
    if startup_greeting and is_first_message:
        system_prompt += f"\n\nSTARTUP AWARENESS:\n{startup_greeting}\nThis is the start of the conversation. Use this context to give a warm, personalized greeting. Acknowledge what you observe naturally - their presence, mood, environment, time of day. Be genuine and observant, not robotic."
    
    # RAG context
    rag_context = ""
    try:
        user_messages = [m for m in state.messages if m.get("role") == "user"]
        if user_messages:
            last_user_msg = user_messages[-1].get("content", "")
            similar = await embedding_service.search_similar(last_user_msg, limit=3)
            
            if similar:
                rag_context = "\n\n[Relevant context from past conversations:]\n"
                for item in similar:
                    if item.get("score", 0) < 0.95:
                        rag_context += f"- {item['role'].title()}: {item['content'][:200]}...\n"
                
                if rag_context.strip().endswith(":]\n"):
                    rag_context = ""
    except Exception as e:
        logger.debug(f"RAG retrieval error (non-fatal): {e}")
    
    if rag_context:
        system_prompt = system_prompt + rag_context
    
    # ============== DOMAIN ROUTING ==============
    active_model = user_settings.selected_model
    
    if user_settings.domain_routing_enabled:
        user_messages = [m for m in state.messages if m.get("role") == "user"]
        if user_messages:
            last_user_msg = user_messages[-1].get("content", "")
            
            detected_domain, confidence, specialist_model, voice_override = domain_router.detect_domain(last_user_msg)
            
            if specialist_model and confidence >= 0.4:
                spec_models = user_settings.specialist_models
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
                    logger.info(f"Domain routing: {detected_domain.value} -> {configured_model} (confidence: {confidence:.2f})")
                    
                    if voice_override:
                        logger.debug(f"Voice override: {voice_override}")
                        user_settings.selected_voice = voice_override
                    
                    handoff_msg = domain_router.get_handoff_message(detected_domain)
                    await websocket.send_json({
                        "type": "domain_switch",
                        "domain": detected_domain.value,
                        "model": configured_model,
                        "message": handoff_msg,
                        "confidence": confidence,
                        "voice_override": voice_override
                    })
                    
                    active_model = configured_model
        
        routing_prompt = domain_router.get_routing_prompt_addition()
        if routing_prompt:
            system_prompt += routing_prompt
    
    # Stream LLM response with sentence-level TTS
    full_response = ""
    sentence_buffer = ""
    first_audio_sent = False
    in_think_block = False
    think_buffer = ""
    
    await websocket.send_json({"type": "status", "state": "processing"})
    
    try:
        async for chunk in ollama_service.chat_stream(
            messages=state.messages,
            model=active_model,
            system_prompt=system_prompt,
            enable_thinking=False
        ):
            if state.should_interrupt:
                break
            
            # Track <think> blocks
            think_buffer += chunk
            
            if '<think>' in think_buffer.lower() or '<thinking>' in think_buffer.lower():
                in_think_block = True
                think_buffer = re.sub(r'<think(?:ing)?>', '', think_buffer, flags=re.IGNORECASE)
            
            if '</think>' in think_buffer.lower() or '</thinking>' in think_buffer.lower():
                in_think_block = False
                think_content = re.sub(r'</think(?:ing)?>', '', think_buffer, flags=re.IGNORECASE)
                if think_content.strip():
                    await websocket.send_json({"type": "thinking_chunk", "text": think_content})
                think_buffer = ""
                continue
            
            if in_think_block:
                if think_buffer.strip() and not think_buffer.strip().startswith('<'):
                    await websocket.send_json({"type": "thinking_chunk", "text": think_buffer})
                    think_buffer = ""
                continue
            
            if len(think_buffer) > 50 and '<' not in think_buffer:
                think_buffer = ""
            
            full_response += chunk
            sentence_buffer += chunk
            
            if not chunk.strip().startswith('<'):
                await websocket.send_json({"type": "llm_chunk", "text": chunk})
            
            # Detect if LLM wants to search
            if len(full_response) < 150 and len(full_response) > 20:
                response_lower = full_response.lower()
                search_phrases = [
                    "let me look that up", "let me search", "i'll search",
                    "i will search", "let me check", "i'll look that up",
                    "i will look that up", "searching for", "let me find",
                    "i'll find out",
                ]
                for phrase in search_phrases:
                    if phrase in response_lower:
                        user_messages = [m for m in state.messages if m.get("role") == "user"]
                        if user_messages:
                            original_query = user_messages[-1].get("content", "")
                            logger.info(f"LLM indicated search intent, triggering search for: {original_query}")
                            
                            await websocket.send_json({
                                "type": "llm_chunk",
                                "text": " Let me search for that...\n\n"
                            })
                            
                            if state.messages and state.messages[-1].get("role") == "user":
                                state.should_interrupt = True
                                await handle_web_search(
                                    websocket, state,
                                    {"query": original_query, "original_request": original_query},
                                    user_settings
                                )
                                return
                        break
            
            # Check for complete sentence
            sentence_end_match = re.search(r'[.!?](?:\s|$)', sentence_buffer)
            
            if sentence_end_match:
                end_pos = sentence_end_match.end()
                sentence = sentence_buffer[:end_pos].strip()
                sentence_buffer = sentence_buffer[end_pos:].strip()
                
                if sentence and len(sentence) > 3:
                    clean_sentence = clean_for_speech(sentence)
                    
                    if clean_sentence:
                        if not first_audio_sent:
                            await websocket.send_json({"type": "status", "state": "speaking"})
                            state.is_speaking = True
                            first_audio_sent = True
                        
                        try:
                            audio_data = await synthesize_tts(
                                text=clean_sentence,
                                voice=user_settings.selected_voice,
                                provider=getattr(user_settings, 'tts_provider', 'piper'),
                                speed=getattr(user_settings, 'voice_speed', 1.0),
                                variation=getattr(user_settings, 'voice_variation', 0.8),
                                phoneme_var=getattr(user_settings, 'voice_phoneme_var', 0.6),
                            )
                            
                            if not state.should_interrupt:
                                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                                await websocket.send_json({
                                    "type": "audio_chunk",
                                    "audio": audio_b64,
                                    "format": "wav",
                                    "sentence": clean_sentence
                                })
                        except Exception as e:
                            logger.error(f"TTS error for sentence: {e}")
        
        if state.should_interrupt:
            await websocket.send_json({"type": "status", "state": "idle"})
            return
        
        # Handle remaining text
        if sentence_buffer.strip():
            clean_remainder = clean_for_speech(sentence_buffer.strip())
            if clean_remainder:
                if not first_audio_sent:
                    await websocket.send_json({"type": "status", "state": "speaking"})
                    state.is_speaking = True
                    first_audio_sent = True
                
                try:
                    audio_data = await synthesize_tts(
                        text=clean_remainder,
                        voice=user_settings.selected_voice,
                        provider=getattr(user_settings, 'tts_provider', 'piper'),
                        speed=getattr(user_settings, 'voice_speed', 1.0),
                        variation=getattr(user_settings, 'voice_variation', 0.8),
                        phoneme_var=getattr(user_settings, 'voice_phoneme_var', 0.6),
                    )
                    
                    if not state.should_interrupt:
                        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                        await websocket.send_json({
                            "type": "audio_chunk",
                            "audio": audio_b64,
                            "format": "wav",
                            "sentence": clean_remainder
                        })
                except Exception as e:
                    logger.error(f"TTS error for remainder: {e}")
        
        await websocket.send_json({"type": "llm_complete", "text": full_response})
        
        state.messages.append({"role": "assistant", "content": full_response})
    
    except Exception as e:
        logger.error(f"LLM error: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": f"LLM generation failed: {str(e)}"
        })
    
    finally:
        state.is_speaking = False
        await websocket.send_json({"type": "status", "state": "idle"})

