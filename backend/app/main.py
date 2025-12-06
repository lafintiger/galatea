"""Galatea Backend - Main FastAPI Application"""
import asyncio
import base64
import json
import re
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .services.ollama import ollama_service
from .services.wyoming import whisper_service, piper_service
from .services.settings_manager import settings_manager
from .models.schemas import UserSettings


def clean_for_speech(text: str) -> str:
    """Remove emojis, action markers, thinking tags, and formatting from text for natural TTS.
    
    This prevents the TTS from saying things like "smiling face with smiling eyes"
    or reading out "*smiles warmly*" literally, or speaking <think> blocks.
    """
    # Remove <think>...</think> blocks (thinking model output)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any remaining unclosed think tags
    text = re.sub(r'</?think(?:ing)?>', '', text, flags=re.IGNORECASE)
    
    # Pattern to match emojis and other symbols that shouldn't be spoken
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended
        "\U00002600-\U000026FF"  # misc symbols
        "\U00002700-\U000027BF"  # dingbats
        "\U0001F000-\U0001F02F"  # mahjong tiles
        "\U0001F0A0-\U0001F0FF"  # playing cards
        "]+", 
        flags=re.UNICODE
    )
    
    # Remove emojis
    text = emoji_pattern.sub('', text)
    
    # Remove action markers like *smiles*, *laughs*, *nods*
    text = re.sub(r'\*[^*]+\*', '', text)
    
    # Remove parenthetical actions like (smiles) (laughs warmly)
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Remove bracketed actions like [smiling] [nodding]
    text = re.sub(r'\[[^\]]*\]', '', text)
    
    # Remove common text emoticons
    text = re.sub(r'[:;]-?[)(\[\]DPp]', '', text)  # :) :( ;) :D etc
    text = re.sub(r'<3', '', text)  # heart
    
    # Remove markdown formatting but keep the text
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__ -> bold
    text = re.sub(r'`([^`]+)`', r'\1', text)        # `code` -> code
    
    # Clean up extra whitespace and punctuation artifacts
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)  # Remove space before punctuation
    text = re.sub(r'([.,!?])\s*([.,!?])', r'\1', text)  # Remove double punctuation
    text = text.strip()
    
    return text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print("🌟 Galatea is waking up...")
    print(f"   Ollama: {settings.ollama_base_url}")
    print(f"   Whisper: {settings.whisper_host}:{settings.whisper_port}")
    print(f"   Piper: {settings.piper_host}:{settings.piper_port}")
    yield
    print("💤 Galatea is going to sleep...")


app = FastAPI(
    title="Galatea",
    description="Local Voice AI Companion",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== REST Endpoints ==============

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "name": "Galatea"}


@app.get("/api/settings")
async def get_settings():
    """Get current user settings"""
    return settings_manager.load()


@app.put("/api/settings")
async def update_settings(new_settings: UserSettings):
    """Update user settings"""
    return settings_manager.save(new_settings)


@app.get("/api/models")
async def list_models():
    """List available Ollama models"""
    try:
        models = await ollama_service.list_models()
        return {"models": models}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/voices")
async def list_voices():
    """List available Piper voices"""
    try:
        voices = await piper_service.list_voices()
        return {"voices": voices}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/voices/test/{voice_id}")
async def test_voice(voice_id: str, natural: bool = True):
    """Test a voice by synthesizing a sample phrase
    
    Args:
        voice_id: The Piper voice model ID
        natural: If True, use more expressive/natural speech parameters
    """
    from fastapi.responses import Response
    
    # Use a conversational test phrase
    test_phrase = "Hello! I'm Galatea, your AI companion. It's so nice to meet you! How can I help you today?"
    
    # Parameters for more natural, expressive speech
    if natural:
        length_scale = 1.0  # Normal speed
        noise_scale = 0.8   # More expressive variation
        noise_w = 0.6       # More natural phoneme timing
    else:
        # Default Piper values (more robotic)
        length_scale = 1.0
        noise_scale = 0.667
        noise_w = 0.333
    
    try:
        audio_data = await piper_service.synthesize(
            text=test_phrase,
            voice=voice_id,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w=noise_w,
        )
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={"Content-Disposition": f"inline; filename=voice_test.wav"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Voice test failed: {str(e)}"}
        )


# ============== WebSocket Handler ==============

class ConversationState:
    """Tracks conversation state for a WebSocket connection"""
    
    def __init__(self):
        self.messages: list[dict] = []
        self.is_speaking = False
        self.should_interrupt = False
        self.current_audio_task: asyncio.Task | None = None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for voice conversation"""
    await websocket.accept()
    state = ConversationState()
    user_settings = settings_manager.load()
    
    print(f"🔌 Client connected")
    
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
            
            if msg_type == "audio_data":
                # Process voice input
                await handle_voice_input(websocket, state, data, user_settings)
            
            elif msg_type == "text_message":
                # Process text input
                await handle_text_input(websocket, state, data, user_settings)
            
            elif msg_type == "interrupt":
                # Interrupt current speech
                state.should_interrupt = True
                if state.current_audio_task:
                    state.current_audio_task.cancel()
                await websocket.send_json({"type": "interrupted"})
            
            elif msg_type == "settings_update":
                # Update settings
                new_settings = UserSettings(**data.get("settings", {}))
                user_settings = settings_manager.save(new_settings)
                await websocket.send_json({
                    "type": "settings_updated",
                    "settings": user_settings.model_dump()
                })
            
            elif msg_type == "clear_history":
                # Clear conversation history
                state.messages = []
                await websocket.send_json({"type": "history_cleared"})
    
    except WebSocketDisconnect:
        print(f"🔌 Client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))


async def handle_voice_input(
    websocket: WebSocket,
    state: ConversationState,
    data: dict,
    user_settings: UserSettings
):
    """Handle voice input from client"""
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
    
    # Update status
    await websocket.send_json({"type": "status", "state": "processing"})
    
    try:
        # Transcribe audio
        transcript = await whisper_service.transcribe(audio_bytes)
        
        if not transcript.strip():
            await websocket.send_json({
                "type": "status",
                "state": "idle"
            })
            return
        
        # Send transcription
        await websocket.send_json({
            "type": "transcription",
            "text": transcript,
            "final": True
        })
        
        # Add to conversation history
        state.messages.append({
            "role": "user",
            "content": transcript
        })
        
        # Generate and send response
        await generate_response(websocket, state, user_settings)
    
    except Exception as e:
        print(f"❌ Voice processing error: {e}")
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
    """Handle text input from client"""
    text = data.get("content", "").strip()
    
    if not text:
        return
    
    # Add to conversation history
    state.messages.append({
        "role": "user",
        "content": text
    })
    
    # Update status
    await websocket.send_json({"type": "status", "state": "processing"})
    
    await generate_response(websocket, state, user_settings)


async def generate_response(
    websocket: WebSocket,
    state: ConversationState,
    user_settings: UserSettings
):
    """Generate LLM response and TTS"""
    state.should_interrupt = False
    
    # Build system prompt
    system_prompt = ollama_service.build_system_prompt(
        assistant_name=user_settings.assistant_name,
        nickname=user_settings.assistant_nickname,
        response_style=user_settings.response_style,
        current_time=datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    )
    
    # Stream LLM response with sentence-level TTS for lower latency
    full_response = ""
    sentence_buffer = ""
    sentences_spoken = []
    first_audio_sent = False
    in_think_block = False
    think_buffer = ""
    
    await websocket.send_json({"type": "status", "state": "processing"})
    
    try:
        async for chunk in ollama_service.chat_stream(
            messages=state.messages,
            model=user_settings.selected_model,
            system_prompt=system_prompt,
            enable_thinking=False
        ):
            if state.should_interrupt:
                break
            
            # Track <think> blocks and filter them out
            think_buffer += chunk
            
            # Check for <think> opening tag
            if '<think>' in think_buffer.lower() or '<thinking>' in think_buffer.lower():
                in_think_block = True
            
            # Check for </think> closing tag
            if '</think>' in think_buffer.lower() or '</thinking>' in think_buffer.lower():
                in_think_block = False
                # Clear the think buffer and skip this content
                think_buffer = re.sub(r'</?think(?:ing)?>', '', think_buffer, flags=re.IGNORECASE)
                think_buffer = ""
                continue
            
            # If we're in a think block, don't output anything
            if in_think_block:
                continue
            
            # Clear think buffer if no tags found after reasonable length
            if len(think_buffer) > 50 and '<' not in think_buffer:
                think_buffer = ""
            
            full_response += chunk
            sentence_buffer += chunk
            
            # Send chunk to client for display (skip if looks like thinking content)
            if not chunk.strip().startswith('<'):
                await websocket.send_json({
                    "type": "llm_chunk",
                    "text": chunk
                })
            
            # Check if we have a complete sentence to speak
            # Look for sentence endings: . ! ? followed by space or end
            sentence_end_match = re.search(r'[.!?](?:\s|$)', sentence_buffer)
            
            if sentence_end_match:
                # Extract the complete sentence
                end_pos = sentence_end_match.end()
                sentence = sentence_buffer[:end_pos].strip()
                sentence_buffer = sentence_buffer[end_pos:].strip()
                
                if sentence and len(sentence) > 3:  # Skip very short fragments
                    # Clean and synthesize this sentence immediately
                    clean_sentence = clean_for_speech(sentence)
                    
                    if clean_sentence:
                        if not first_audio_sent:
                            await websocket.send_json({"type": "status", "state": "speaking"})
                            state.is_speaking = True
                            first_audio_sent = True
                        
                        try:
                            audio_data = await piper_service.synthesize(
                                text=clean_sentence,
                                voice=user_settings.selected_voice,
                                length_scale=getattr(user_settings, 'voice_speed', 1.0),
                                noise_scale=getattr(user_settings, 'voice_variation', 0.8),
                                noise_w=getattr(user_settings, 'voice_phoneme_var', 0.6),
                            )
                            
                            if not state.should_interrupt:
                                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                                await websocket.send_json({
                                    "type": "audio_chunk",
                                    "audio": audio_b64,
                                    "format": "wav",
                                    "sentence": clean_sentence
                                })
                                sentences_spoken.append(clean_sentence)
                        except Exception as e:
                            print(f"❌ TTS error for sentence: {e}")
        
        if state.should_interrupt:
            await websocket.send_json({"type": "status", "state": "idle"})
            return
        
        # Handle any remaining text in buffer
        if sentence_buffer.strip():
            clean_remainder = clean_for_speech(sentence_buffer.strip())
            if clean_remainder:
                if not first_audio_sent:
                    await websocket.send_json({"type": "status", "state": "speaking"})
                    state.is_speaking = True
                    first_audio_sent = True
                
                try:
                    audio_data = await piper_service.synthesize(
                        text=clean_remainder,
                        voice=user_settings.selected_voice,
                        length_scale=getattr(user_settings, 'voice_speed', 1.0),
                        noise_scale=getattr(user_settings, 'voice_variation', 0.8),
                        noise_w=getattr(user_settings, 'voice_phoneme_var', 0.6),
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
                    print(f"❌ TTS error for remainder: {e}")
        
        # Send complete response marker
        await websocket.send_json({
            "type": "llm_complete",
            "text": full_response
        })
        
        # Add to history
        state.messages.append({
            "role": "assistant",
            "content": full_response
        })
    
    except Exception as e:
        print(f"❌ LLM error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"LLM generation failed: {str(e)}"
        })
    
    finally:
        state.is_speaking = False
        await websocket.send_json({"type": "status", "state": "idle"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)

