"""Galatea Backend - Main FastAPI Application"""
import asyncio
import base64
import json
import re
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .services.ollama import ollama_service, get_time_context
from .services.wyoming import whisper_service, piper_service
from .services.kokoro import kokoro_service
from .services.settings_manager import settings_manager
from .services.conversation_history import conversation_history
from .services.web_search import web_search
from .services.embedding import embedding_service
from .services.model_manager import model_manager
from .services.background_worker import background_worker
from .services.user_profile import user_profile_service
from .services.vision_live import vision_live_service
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


async def warmup_model(model_name: str):
    """Pre-load the LLM model into VRAM for instant responses"""
    print(f"   🔥 Warming up model: {model_name}")
    try:
        # Use model_manager to load the model (handles VRAM properly)
        success = await model_manager.load_model(model_name)
        if success:
            print(f"   ✅ Model {model_name} is ready!")
        else:
            print(f"   ⚠️ Model warmup completed (may not be loaded)")
        return success
    except Exception as e:
        print(f"   ⚠️ Model warmup failed: {e}")
        print(f"   (First message may have a delay while model loads)")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print("🌟 Galatea is waking up...")
    print(f"   Ollama: {settings.ollama_base_url}")
    print(f"   Whisper: {settings.whisper_host}:{settings.whisper_port}")
    print(f"   Piper: {settings.piper_host}:{settings.piper_port}")
    print(f"   LanceDB: {embedding_service.db_path}")
    
    # Load user settings
    user_settings = settings_manager.load()
    
    # Pre-load the LLM model for instant first response
    await warmup_model(user_settings.selected_model)
    
    # Start background embedding worker
    background_worker.start(user_settings.selected_model)
    
    yield
    
    # Stop background worker
    background_worker.stop()
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
async def list_voices(provider: str = None):
    """List available TTS voices
    
    Args:
        provider: TTS provider ("piper" or "kokoro"). If not specified, returns both.
    """
    try:
        result = {}
        
        # Get Piper voices
        if provider is None or provider == "piper":
            try:
                piper_voices = await piper_service.list_voices()
                result["piper"] = piper_voices
            except Exception as e:
                print(f"Warning: Could not get Piper voices: {e}")
                result["piper"] = []
        
        # Get Kokoro voices
        if provider is None or provider == "kokoro":
            try:
                kokoro_voices = await kokoro_service.list_voices()
                result["kokoro"] = kokoro_voices
            except Exception as e:
                print(f"Warning: Could not get Kokoro voices: {e}")
                result["kokoro"] = []
        
        # For backwards compatibility, also include flat list
        all_voices = result.get("piper", []) + result.get("kokoro", [])
        result["voices"] = all_voices
        
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


async def synthesize_tts(
    text: str,
    voice: str,
    provider: str = "piper",
    speed: float = 1.0,
    variation: float = 0.8,
    phoneme_var: float = 0.6,
) -> bytes:
    """Synthesize text to speech using the specified provider
    
    Args:
        text: Text to synthesize
        voice: Voice ID
        provider: TTS provider ("piper" or "kokoro")
        speed: Speaking speed (1.0 = normal)
        variation: Voice variation/expressiveness (Piper only)
        phoneme_var: Phoneme timing variation (Piper only)
        
    Returns:
        WAV audio bytes
    """
    if provider == "kokoro":
        return await kokoro_service.synthesize(
            text=text,
            voice=voice,
            speed=speed,
        )
    else:
        # Default to Piper
        return await piper_service.synthesize(
            text=text,
            voice=voice,
            length_scale=speed,
            noise_scale=variation,
            noise_w=phoneme_var,
        )


@app.get("/api/voices/test/{voice_id}")
async def test_voice(voice_id: str, provider: str = "piper", natural: bool = True):
    """Test a voice by synthesizing a sample phrase
    
    Args:
        voice_id: The voice model ID
        provider: TTS provider ("piper" or "kokoro")
        natural: If True, use more expressive/natural speech parameters (Piper only)
    """
    from fastapi.responses import Response
    
    # Use a conversational test phrase
    test_phrase = "Hello! I'm Galatea, your AI companion. It's so nice to meet you! How can I help you today?"
    
    try:
        if provider == "kokoro":
            audio_data = await kokoro_service.synthesize(
                text=test_phrase,
                voice=voice_id,
                speed=1.0,
            )
        else:
            # Piper with natural/robotic settings
            if natural:
                length_scale = 1.0
                noise_scale = 0.8
                noise_w = 0.6
            else:
                length_scale = 1.0
                noise_scale = 0.667
                noise_w = 0.333
            
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


# ============== Conversation History Endpoints ==============

@app.get("/api/conversations")
async def list_conversations(limit: int = 50):
    """List saved conversations"""
    try:
        conversations = conversation_history.list_conversations(limit=limit)
        return {"conversations": [c.model_dump() for c in conversations]}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation"""
    conversation = conversation_history.load_conversation(conversation_id)
    if not conversation:
        return JSONResponse(
            status_code=404,
            content={"error": "Conversation not found"}
        )
    return conversation.model_dump()


@app.post("/api/conversations")
async def save_conversation(data: dict):
    """Save a conversation
    
    Body: { messages: [...], title?: string, id?: string }
    """
    try:
        messages = data.get("messages", [])
        title = data.get("title")
        conversation_id = data.get("id")
        
        conversation = conversation_history.save_conversation(
            messages=messages,
            conversation_id=conversation_id,
            title=title
        )
        
        # Add to embedding queue for background processing
        background_worker.add_to_queue(conversation.id)
        
        return conversation.model_dump()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    success = conversation_history.delete_conversation(conversation_id)
    if not success:
        return JSONResponse(
            status_code=404,
            content={"error": "Conversation not found"}
        )
    return {"success": True}


@app.patch("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, data: dict):
    """Update conversation (rename)
    
    Body: { title: string }
    """
    title = data.get("title")
    if not title:
        return JSONResponse(
            status_code=400,
            content={"error": "Title required"}
        )
    
    conversation = conversation_history.rename_conversation(conversation_id, title)
    if not conversation:
        return JSONResponse(
            status_code=404,
            content={"error": "Conversation not found"}
        )
    return conversation.model_dump()


# ============== Web Search Endpoints ==============

@app.get("/api/search/status")
async def search_status():
    """Check availability of search services"""
    return await web_search.check_status()


@app.post("/api/search")
async def perform_search(data: dict):
    """Perform a web search
    
    Body: { 
        query: string, 
        provider?: "searxng" | "perplexica" | "auto",
        num_results?: int 
    }
    """
    query = data.get("query", "").strip()
    if not query:
        return JSONResponse(
            status_code=400,
            content={"error": "Query required"}
        )
    
    provider = data.get("provider", "auto")
    num_results = data.get("num_results", 5)
    
    try:
        results = await web_search.search(query, provider=provider, num_results=num_results)
        return results
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ============== RAG / Embedding Endpoints ==============

@app.get("/api/rag/status")
async def rag_status():
    """Get RAG system status"""
    worker_status = background_worker.get_status()
    embedding_stats = embedding_service.get_stats()
    model_info = await model_manager.get_vram_info()
    
    return {
        "worker": worker_status,
        "embeddings": embedding_stats,
        "models": model_info,
    }


@app.post("/api/rag/process")
async def trigger_embedding():
    """Manually trigger embedding processing (bypasses idle wait)"""
    user_settings = settings_manager.load()
    
    if background_worker.is_processing:
        return {"message": "Already processing", "status": "busy"}
    
    # Process in background
    import asyncio
    asyncio.create_task(
        background_worker.process_pending_embeddings(user_settings.selected_model)
    )
    
    return {"message": "Processing started", "status": "started"}


@app.get("/api/rag/search")
async def rag_search(query: str, limit: int = 5):
    """Search the RAG knowledge base
    
    Args:
        query: Search query
        limit: Max results (default 5)
    """
    try:
        results = await embedding_service.search_similar(query, limit=limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ============== User Profile / Onboarding Endpoints ==============

@app.get("/api/profile")
async def get_profile():
    """Get the user's profile and onboarding status"""
    profile = user_profile_service.load_profile()
    progress = user_profile_service.get_progress()
    
    return {
        "profile": {
            "user_name": profile.user_name,
            "onboarding_started": profile.onboarding_started.isoformat() if profile.onboarding_started else None,
            "onboarding_completed": profile.onboarding_completed,
            "last_updated": profile.last_updated.isoformat() if profile.last_updated else None,
            "answers": [
                {
                    "question_id": a.question_id,
                    "question": a.question,
                    "answer": a.answer,
                    "category": a.category,
                    "answered_at": a.answered_at.isoformat()
                }
                for a in profile.answers
            ]
        },
        "progress": progress
    }


@app.get("/api/profile/questions")
async def get_profile_questions(category: str = None, unanswered_only: bool = False):
    """Get profile questions
    
    Args:
        category: Filter by category (optional)
        unanswered_only: Only return unanswered questions
    """
    if unanswered_only:
        questions = user_profile_service.get_unanswered_questions()
    elif category:
        questions = user_profile_service.get_questions_by_category(category)
    else:
        questions = user_profile_service.questions
    
    return {
        "questions": [q.model_dump() for q in questions],
        "categories": user_profile_service.get_categories(),
        "total": len(questions)
    }


@app.get("/api/profile/next")
async def get_next_questions(count: int = 1):
    """Get the next N questions to ask in onboarding
    
    Args:
        count: Number of questions to return (default 1)
    """
    questions = user_profile_service.get_next_questions(count)
    progress = user_profile_service.get_progress()
    
    return {
        "questions": [q.model_dump() for q in questions],
        "progress": progress,
        "is_complete": progress["is_complete"]
    }


@app.post("/api/profile/answer")
async def record_profile_answer(data: dict):
    """Record an answer to a profile question
    
    Body: { question_id: string, answer: string }
    """
    try:
        question_id = data.get("question_id")
        answer = data.get("answer")
        
        if not question_id or not answer:
            return JSONResponse(
                status_code=400,
                content={"error": "Both question_id and answer are required"}
            )
        
        profile_answer = user_profile_service.record_answer(question_id, answer)
        progress = user_profile_service.get_progress()
        next_questions = user_profile_service.get_next_questions(1)
        
        return {
            "success": True,
            "answer": {
                "question_id": profile_answer.question_id,
                "answer": profile_answer.answer,
                "answered_at": profile_answer.answered_at.isoformat()
            },
            "progress": progress,
            "next_question": next_questions[0].model_dump() if next_questions else None
        }
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.delete("/api/profile/answer/{question_id}")
async def delete_profile_answer(question_id: str):
    """Delete a specific answer"""
    success = user_profile_service.delete_answer(question_id)
    
    if success:
        return {"success": True, "message": f"Deleted answer for {question_id}"}
    else:
        return JSONResponse(
            status_code=404,
            content={"error": f"No answer found for question {question_id}"}
        )


@app.delete("/api/profile")
async def clear_profile():
    """Clear the entire user profile and start fresh"""
    user_profile_service.clear_profile()
    return {"success": True, "message": "Profile cleared"}


@app.get("/api/profile/summary")
async def get_profile_summary():
    """Get a text summary of the profile (for debugging/display)"""
    summary = user_profile_service.get_profile_summary()
    return {"summary": summary}


# ============== Vision Endpoints ==============

from .services.vision import vision_service

@app.post("/api/vision/analyze")
async def analyze_image(
    image: str = Body(..., description="Base64-encoded image"),
    prompt: str = Body("Describe this image in detail.", description="What to analyze"),
    model_type: str = Body(None, description="Force model: general, ocr, or uncensored")
):
    """Analyze an image using vision models.
    
    Automatically selects the best model based on prompt:
    - 'general' (granite): Fast, general purpose
    - 'ocr' (deepseek): Text extraction
    - 'uncensored' (qwen-vl): For blocked content
    """
    try:
        result = await vision_service.analyze_image(
            image_base64=image,
            prompt=prompt,
            model_type=model_type
        )
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/vision/models")
async def get_vision_models():
    """Check which vision models are available."""
    available = await vision_service.check_models_available()
    return {
        "models": vision_service.models,
        "available": available
    }


# ============== Vision Live Endpoints (Gala's Eyes) ==============

@app.get("/api/vision/live/health")
async def vision_live_health():
    """Check if the live vision service is available"""
    is_healthy = await vision_live_service.health_check()
    return {
        "available": is_healthy,
        "host": settings.vision_host,
        "port": settings.vision_port
    }


@app.post("/api/vision/live/start")
async def vision_live_start():
    """Open Gala's eyes - start real-time vision analysis"""
    try:
        result = await vision_live_service.start()
        # Also update user settings
        user_settings = settings_manager.load()
        user_settings.vision_enabled = True
        settings_manager.save(user_settings)
        return {"success": True, "message": "Eyes opened", **result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/vision/live/stop")
async def vision_live_stop():
    """Close Gala's eyes - stop real-time vision analysis"""
    try:
        result = await vision_live_service.stop()
        # Also update user settings
        user_settings = settings_manager.load()
        user_settings.vision_enabled = False
        settings_manager.save(user_settings)
        return {"success": True, "message": "Eyes closed", **result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/vision/live/status")
async def vision_live_status():
    """Get current vision status and latest analysis"""
    try:
        status = await vision_live_service.get_status()
        return status
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
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
            
            # Record user activity (resets idle timer for background embedding)
            background_worker.record_activity()
            
            if msg_type == "audio_data":
                # Process voice input
                await handle_voice_input(websocket, state, data, user_settings)
            
            elif msg_type == "text_message":
                # Process text input
                await handle_text_input(websocket, state, data, user_settings)
            
            elif msg_type == "web_search":
                # Perform web search and add results to context
                await handle_web_search(websocket, state, data, user_settings)
            
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
            
            elif msg_type == "speak_text":
                # Speak arbitrary text (used for vision results, etc.)
                text = data.get("text", "")
                if text:
                    await websocket.send_json({"type": "status", "state": "speaking"})
                    await speak_response(websocket, state, text, user_settings)
                    await websocket.send_json({"type": "status", "state": "idle"})
            
            elif msg_type == "open_eyes":
                # Start real-time vision (Gala's eyes)
                try:
                    result = await vision_live_service.start()
                    user_settings.vision_enabled = True
                    settings_manager.save(user_settings)
                    await websocket.send_json({
                        "type": "vision_status",
                        "eyes_open": True,
                        "message": "I can see you now"
                    })
                    print("👁️ Gala's eyes opened")
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Could not open eyes: {str(e)}"
                    })
            
            elif msg_type == "close_eyes":
                # Stop real-time vision
                try:
                    result = await vision_live_service.stop()
                    user_settings.vision_enabled = False
                    settings_manager.save(user_settings)
                    await websocket.send_json({
                        "type": "vision_status",
                        "eyes_open": False,
                        "message": "Eyes closed"
                    })
                    print("😴 Gala's eyes closed")
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Could not close eyes: {str(e)}"
                    })
            
            elif msg_type == "get_vision_status":
                # Get current vision analysis
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
        
        # Check if this is a vision command (open/close eyes)
        vision_cmd, vision_response = detect_vision_command(transcript)
        if vision_cmd:
            print(f"👁️ Detected vision command: '{vision_cmd}'")
            await handle_vision_command(websocket, vision_cmd, vision_response, user_settings, state)
            return
        
        # Check if this is a search request
        is_search, search_query = detect_search_intent(transcript)
        
        if is_search and search_query:
            # Redirect to search handler
            print(f"🔍 Detected search intent: '{search_query}'")
            await handle_web_search(
                websocket, state, 
                {"query": search_query, "original_request": transcript},
                user_settings
            )
            return
        
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


def detect_search_intent(text: str) -> tuple[bool, str]:
    """Detect if the user is asking for a web search and extract the query.
    
    This detects both explicit search requests AND questions that need 
    real-time information (weather, news, prices, etc.)
    
    Returns:
        (is_search_request, extracted_query)
    """
    text_lower = text.lower().strip()
    
    # Topics that ALWAYS need real-time data (use full question as query)
    realtime_topics = [
        # Weather
        r"weather",
        r"temperature",
        r"forecast",
        r"rain(?:ing)?",
        r"snow(?:ing)?",
        r"humid",
        # News & Current Events  
        r"latest news",
        r"current (?:news|events)",
        r"recent (?:news|developments)",
        r"what(?:'s| is) happening",
        r"breaking news",
        r"today(?:'s)? news",
        r"this week",
        r"this month",
        # Financial/Prices
        r"stock price",
        r"share price", 
        r"how much (?:does|is|are|do)",
        r"price of",
        r"cost of",
        r"bitcoin|crypto|ethereum",
        r"market",
        # Sports
        r"(?:game|match) score",
        r"who won",
        r"standings",
        r"playoffs",
        r"championship",
        # Time-sensitive
        r"release date",
        r"when (?:does|is|will|did)",
        r"hours of",
        r"open(?:ing)? hours",
        r"schedule",
        r"next (?:week|month|year)",
        # Product/Tech info
        r"specs",
        r"specifications",
        r"features of",
        r"review(?:s)? (?:of|for)",
        r"compare|comparison",
        r"best (?:\w+ )?(?:for|to|in)",
        r"top \d+",
        r"recommended",
        # Location/Business
        r"near(?:by| me)",
        r"directions to",
        r"address of",
        r"phone number",
        r"contact",
        # Events/Entertainment
        r"movie(?:s)?",
        r"playing (?:tonight|today|now)",
        r"showing (?:tonight|today|now)",
        r"concert(?:s)?",
        r"event(?:s)?",
        r"ticket(?:s)?",
        # Research queries
        r"what is (?:a |an |the )?(?:\w+ ){0,3}(?:and|or) how",
        r"explain (?:what|how|why)",
        r"definition of",
        r"meaning of",
    ]
    
    for topic in realtime_topics:
        if re.search(topic, text_lower):
            # Use the full question as search query
            query = text.rstrip('?.!').strip()
            if len(query) > 5:
                print(f"🔍 Auto-search triggered by realtime topic: {topic}")
                return True, query
    
    # Patterns that indicate explicit search request
    search_patterns = [
        # Direct search commands
        (r"^(?:please\s+)?(?:can you\s+)?(?:web\s+)?search\s+(?:for\s+)?(?:the\s+)?(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^(?:please\s+)?look\s+up\s+(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^(?:please\s+)?find\s+(?:out\s+)?(?:about\s+)?(?:information\s+(?:on|about)\s+)?(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^(?:please\s+)?google\s+(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^(?:please\s+)?check\s+(?:the\s+)?(.+?)(?:\s+for me)?(?:\s+please)?$", 1),
        (r"^what(?:'s| is) the latest (?:news |info(?:rmation)? )?(?:on|about) (.+?)[\?\.]?$", 1),
        
        # "What is X" questions about real things (not conversational)
        (r"^what(?:'s| is| are) (?:the )?(?:current |latest |new )(.+?)[\?\.]?$", 1),
        
        # Explicit search triggers
        (r"^search[:\s]+(.+)$", 1),
        (r"^look up[:\s]+(.+)$", 1),
    ]
    
    for pattern, group in search_patterns:
        match = re.match(pattern, text_lower)
        if match:
            if group == 0:
                query = text  # Use full text
            else:
                query = match.group(group).strip()
            # Clean up query
            query = re.sub(r'^(the|a|an)\s+', '', query)
            query = query.rstrip('?.!')
            if len(query) > 3:  # Minimum query length
                return True, query
    
    # Check for keywords that strongly suggest search need
    search_keywords = [
        'search for', 'look up', 'find out', 'google', 
        'what is the latest', 'current news', 'recent news',
        'search the web', 'web search', 'check the',
        'look into', 'research'
    ]
    
    for keyword in search_keywords:
        if keyword in text_lower:
            # Extract query after the keyword
            idx = text_lower.find(keyword)
            query = text[idx + len(keyword):].strip()
            query = re.sub(r'^(for|about|on)\s+', '', query, flags=re.IGNORECASE)
            query = query.rstrip('?.!')
            if len(query) > 3:
                return True, query
    
    return False, ""


def detect_vision_command(text: str) -> tuple[str | None, str]:
    """Detect if the user is asking to open/close Gala's eyes.
    
    Returns:
        (command, response_text) where command is 'open', 'close', or None
    """
    text_lower = text.lower().strip()
    
    # Open eyes patterns
    open_patterns = [
        r"open\s+(?:your\s+)?eyes",
        r"(?:can you\s+)?see\s+me",
        r"look\s+at\s+me",
        r"(?:start|enable|turn on)\s+(?:your\s+)?(?:vision|eyes|camera|webcam)",
        r"(?:i\s+)?want\s+you\s+to\s+see",
        r"watch\s+me",
        r"eyes\s+open",
    ]
    
    for pattern in open_patterns:
        if re.search(pattern, text_lower):
            return "open", "Opening my eyes... I can see you now."
    
    # Close eyes patterns
    close_patterns = [
        r"close\s+(?:your\s+)?eyes",
        r"(?:stop|disable|turn off)\s+(?:your\s+)?(?:vision|eyes|camera|webcam)",
        r"(?:don't|do not)\s+(?:look|watch|see)",
        r"(?:stop\s+)?look(?:ing)?\s+at\s+me",
        r"eyes\s+(?:closed|shut)",
        r"shut\s+(?:your\s+)?eyes",
        r"(?:i\s+)?(?:don't\s+)?want\s+(?:you\s+to\s+)?(?:stop\s+)?see(?:ing)?",
    ]
    
    for pattern in close_patterns:
        if re.search(pattern, text_lower):
            return "close", "Closing my eyes. I can no longer see."
    
    return None, ""


async def handle_vision_command(
    websocket: WebSocket,
    command: str,
    response_text: str,
    user_settings: UserSettings,
    state
):
    """Handle vision open/close commands"""
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
            print("👁️ Gala's eyes opened via voice command")
        elif command == "close":
            await vision_live_service.stop()
            user_settings.vision_enabled = False
            settings_manager.save(user_settings)
            await websocket.send_json({
                "type": "vision_status",
                "eyes_open": False,
                "message": response_text
            })
            print("😴 Gala's eyes closed via voice command")
        
        # Add to conversation and speak the response
        state.messages.append({
            "role": "user",
            "content": f"[Vision command: {command} eyes]"
        })
        state.messages.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Speak the response
        await websocket.send_json({"type": "status", "state": "speaking"})
        await speak_response(websocket, state, response_text, user_settings)
        await websocket.send_json({"type": "status", "state": "idle"})
        
    except Exception as e:
        error_msg = f"I couldn't {'open' if command == 'open' else 'close'} my eyes: {str(e)}"
        await websocket.send_json({
            "type": "error",
            "message": error_msg
        })


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
    
    # Check if this is a vision command (open/close eyes)
    vision_cmd, vision_response = detect_vision_command(text)
    if vision_cmd:
        await handle_vision_command(websocket, vision_cmd, vision_response, user_settings, state)
        return
    
    # Check if this is a search request
    is_search, search_query = detect_search_intent(text)
    
    if is_search and search_query:
        # Redirect to search handler
        await handle_web_search(
            websocket, state, 
            {"query": search_query, "original_request": text},
            user_settings
        )
        return
    
    # Add to conversation history
    state.messages.append({
        "role": "user",
        "content": text
    })
    
    # Update status
    await websocket.send_json({"type": "status", "state": "processing"})
    
    await generate_response(websocket, state, user_settings)


async def handle_web_search(
    websocket: WebSocket,
    state: ConversationState,
    data: dict,
    user_settings: UserSettings
):
    """Handle web search request"""
    query = data.get("query", "").strip()
    provider = data.get("provider", "auto")
    follow_up = data.get("follow_up", "")  # Optional follow-up question about results
    original_request = data.get("original_request", "")  # Original voice/text request
    
    if not query:
        await websocket.send_json({"type": "error", "message": "Search query required"})
        return
    
    # Update status
    await websocket.send_json({"type": "status", "state": "searching"})
    await websocket.send_json({"type": "search_start", "query": query})
    
    print(f"🔍 Performing web search: '{query}'")
    
    try:
        # Perform search
        search_results = await web_search.search(query, provider=provider)
        
        # Send raw results to frontend
        await websocket.send_json({
            "type": "search_results",
            "data": search_results
        })
        
        # Format results for LLM context
        formatted_results = web_search.format_results_for_llm(search_results)
        
        # Build context message for LLM
        # Include the original request if it was a natural language query
        if original_request:
            user_message = f"User said: \"{original_request}\"\n\n"
            user_message += f"[I searched the web for: {query}]\n\n{formatted_results}\n\n"
            user_message += "Please answer the user's request based on these search results. Be conversational and helpful."
        elif follow_up:
            user_message = f"[Web Search: {query}]\n\n{formatted_results}\n\nUser question: {follow_up}"
        else:
            user_message = f"[Web Search: {query}]\n\n{formatted_results}\n\nPlease summarize these search results for me in a helpful way."
        
        state.messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Generate response based on search results
        await websocket.send_json({"type": "status", "state": "thinking"})
        await generate_response(websocket, state, user_settings)
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Search failed: {str(e)}"
        })
        await websocket.send_json({"type": "status", "state": "idle"})


async def generate_response(
    websocket: WebSocket,
    state: ConversationState,
    user_settings: UserSettings
):
    """Generate LLM response and TTS"""
    state.should_interrupt = False
    
    # Get user profile summary
    user_profile_summary = user_profile_service.get_profile_summary()
    user_name = user_profile_service.load_profile().user_name or "User"
    
    # Get vision context if eyes are open
    vision_context = ""
    if user_settings.vision_enabled and vision_live_service.is_active:
        vision_context = vision_live_service.get_emotion_context()
    
    # Build system prompt with rich time context, user profile, and vision
    time_context = get_time_context()
    system_prompt = ollama_service.build_system_prompt(
        assistant_name=user_settings.assistant_name,
        nickname=user_settings.assistant_nickname,
        response_style=user_settings.response_style,
        user_name=user_name,
        time_context=time_context,
        user_profile=user_profile_summary if user_profile_summary else None,
    )
    
    # Inject vision context if available
    if vision_context:
        system_prompt += f"\n\nVISUAL AWARENESS:\n{vision_context}\nUse this visual context naturally - acknowledge emotions appropriately but don't constantly reference what you see."
    
    # Try to get relevant context from RAG (if embeddings exist)
    rag_context = ""
    try:
        # Get the most recent user message for RAG query
        user_messages = [m for m in state.messages if m.get("role") == "user"]
        if user_messages:
            last_user_msg = user_messages[-1].get("content", "")
            similar = await embedding_service.search_similar(last_user_msg, limit=3)
            
            if similar:
                rag_context = "\n\n[Relevant context from past conversations:]\n"
                for item in similar:
                    # Don't include context that's too similar (it's from the current conversation)
                    if item.get("score", 0) < 0.95:  # Skip near-duplicates
                        rag_context += f"- {item['role'].title()}: {item['content'][:200]}...\n"
                
                if rag_context.strip().endswith(":]\n"):
                    rag_context = ""  # No useful context found
    except Exception as e:
        print(f"RAG retrieval error (non-fatal): {e}")
    
    # Inject RAG context into system prompt if found
    if rag_context:
        system_prompt = system_prompt + rag_context
    
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
            
            # Track <think> blocks - send separately for optional display
            think_buffer += chunk
            
            # Check for <think> opening tag
            if '<think>' in think_buffer.lower() or '<thinking>' in think_buffer.lower():
                in_think_block = True
                # Clean the tag from buffer
                think_buffer = re.sub(r'<think(?:ing)?>', '', think_buffer, flags=re.IGNORECASE)
            
            # Check for </think> closing tag
            if '</think>' in think_buffer.lower() or '</thinking>' in think_buffer.lower():
                in_think_block = False
                # Send final thinking chunk and clear
                think_content = re.sub(r'</think(?:ing)?>', '', think_buffer, flags=re.IGNORECASE)
                if think_content.strip():
                    await websocket.send_json({
                        "type": "thinking_chunk",
                        "text": think_content
                    })
                think_buffer = ""
                continue
            
            # If we're in a think block, send as thinking content
            if in_think_block:
                if think_buffer.strip() and not think_buffer.strip().startswith('<'):
                    await websocket.send_json({
                        "type": "thinking_chunk",
                        "text": think_buffer
                    })
                    think_buffer = ""
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
            
            # DETECT: If LLM says it will search, actually do the search!
            # Check early in the response (first ~100 chars)
            if len(full_response) < 150 and len(full_response) > 20:
                response_lower = full_response.lower()
                search_phrases = [
                    "let me look that up",
                    "let me search",
                    "i'll search",
                    "i will search",
                    "let me check",
                    "i'll look that up",
                    "i will look that up",
                    "searching for",
                    "let me find",
                    "i'll find out",
                ]
                for phrase in search_phrases:
                    if phrase in response_lower:
                        # LLM wants to search - extract query from user's last message
                        user_messages = [m for m in state.messages if m.get("role") == "user"]
                        if user_messages:
                            original_query = user_messages[-1].get("content", "")
                            print(f"🔍 LLM indicated search intent, triggering search for: {original_query}")
                            
                            # Notify frontend
                            await websocket.send_json({
                                "type": "llm_chunk",
                                "text": " Let me search for that...\n\n"
                            })
                            
                            # Remove the incomplete message and do actual search
                            if state.messages and state.messages[-1].get("role") == "user":
                                # Keep the user message but trigger search
                                state.should_interrupt = True
                                await handle_web_search(
                                    websocket, state,
                                    {"query": original_query, "original_request": original_query},
                                    user_settings
                                )
                                return
                        break
            
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

