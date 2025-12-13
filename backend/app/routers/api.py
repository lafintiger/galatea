"""REST API endpoints for Galatea.

This module contains all REST endpoints (non-WebSocket) for:
- Health checks
- Settings management
- Model/voice listing
- Conversation history
- Web search
- RAG/embedding system
- User profile/onboarding
- Vision (static and live)
- Face recognition
- Domain routing
"""
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, Response

from ..core import get_logger
from ..config import settings
from ..services.ollama import ollama_service
from ..services.wyoming import piper_service
from ..services.kokoro import kokoro_service
from ..services.settings_manager import settings_manager
from ..services.conversation_history import conversation_history
from ..services.web_search import web_search
from ..services.embedding import embedding_service
from ..services.model_manager import model_manager
from ..services.background_worker import background_worker
from ..services.user_profile import user_profile_service
from ..services.vision import vision_service
from ..services.vision_live import vision_live_service
from ..services.domain_router import domain_router, Domain
from ..models.schemas import UserSettings

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["api"])


# ============== Health & Settings ==============

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "name": "Galatea"}


@router.get("/settings")
async def get_settings():
    """Get current user settings"""
    return settings_manager.load()


@router.put("/settings")
async def update_settings(new_settings: UserSettings):
    """Update user settings"""
    return settings_manager.save(new_settings)


# ============== Models & Voices ==============

@router.get("/models")
async def list_models():
    """List available Ollama models"""
    try:
        models = await ollama_service.list_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/voices")
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
                logger.warning(f"Could not get Piper voices: {e}")
                result["piper"] = []
        
        # Get Kokoro voices
        if provider is None or provider == "kokoro":
            try:
                kokoro_voices = await kokoro_service.list_voices()
                result["kokoro"] = kokoro_voices
            except Exception as e:
                logger.warning(f"Could not get Kokoro voices: {e}")
                result["kokoro"] = []
        
        # For backwards compatibility, also include flat list
        all_voices = result.get("piper", []) + result.get("kokoro", [])
        result["voices"] = all_voices
        
        return result
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/voices/test/{voice_id}")
async def test_voice(voice_id: str, provider: str = "piper", natural: bool = True):
    """Test a voice by synthesizing a sample phrase
    
    Args:
        voice_id: The voice model ID
        provider: TTS provider ("piper" or "kokoro")
        natural: If True, use more expressive/natural speech parameters (Piper only)
    """
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
            headers={"Content-Disposition": "inline; filename=voice_test.wav"}
        )
    except Exception as e:
        logger.error(f"Voice test failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Voice test failed: {str(e)}"}
        )


# ============== Conversation History ==============

@router.get("/conversations")
async def list_conversations(limit: int = 50):
    """List saved conversations"""
    try:
        conversations = conversation_history.list_conversations(limit=limit)
        return {"conversations": [c.model_dump() for c in conversations]}
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation"""
    conversation = conversation_history.load_conversation(conversation_id)
    if not conversation:
        return JSONResponse(
            status_code=404,
            content={"error": "Conversation not found"}
        )
    return conversation.model_dump()


@router.post("/conversations")
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
        logger.error(f"Failed to save conversation: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    success = conversation_history.delete_conversation(conversation_id)
    if not success:
        return JSONResponse(
            status_code=404,
            content={"error": "Conversation not found"}
        )
    return {"success": True}


@router.patch("/conversations/{conversation_id}")
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


# ============== Web Search ==============

@router.get("/search/status")
async def search_status():
    """Check availability of search services"""
    return await web_search.check_status()


@router.post("/search")
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
        logger.error(f"Search failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ============== RAG / Embedding ==============

@router.get("/rag/status")
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


@router.post("/rag/process")
async def trigger_embedding():
    """Manually trigger embedding processing (bypasses idle wait)"""
    import asyncio
    
    user_settings = settings_manager.load()
    
    if background_worker.is_processing:
        return {"message": "Already processing", "status": "busy"}
    
    # Process in background
    asyncio.create_task(
        background_worker.process_pending_embeddings(user_settings.selected_model)
    )
    
    return {"message": "Processing started", "status": "started"}


@router.get("/rag/search")
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
        logger.error(f"RAG search failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ============== User Profile / Onboarding ==============

@router.get("/profile")
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


@router.get("/profile/questions")
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


@router.get("/profile/next")
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


@router.post("/profile/answer")
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
        logger.error(f"Failed to record answer: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("/profile/answer/{question_id}")
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


@router.delete("/profile")
async def clear_profile():
    """Clear the entire user profile and start fresh"""
    user_profile_service.clear_profile()
    return {"success": True, "message": "Profile cleared"}


@router.get("/profile/summary")
async def get_profile_summary():
    """Get a text summary of the profile (for debugging/display)"""
    summary = user_profile_service.get_profile_summary()
    return {"summary": summary}


# ============== Vision (Static) ==============

@router.post("/vision/analyze")
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
        logger.error(f"Vision analysis failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/vision/models")
async def get_vision_models():
    """Check which vision models are available."""
    available = await vision_service.check_models_available()
    return {
        "models": vision_service.models,
        "available": available
    }


# ============== Vision Live (Gala's Eyes) ==============

@router.get("/vision/live/health")
async def vision_live_health():
    """Check if the live vision service is available"""
    is_healthy = await vision_live_service.health_check()
    return {
        "available": is_healthy,
        "host": settings.vision_host,
        "port": settings.vision_port
    }


@router.post("/vision/live/start")
async def vision_live_start(capture_startup: bool = True):
    """
    Open Gala's eyes - start real-time vision analysis
    
    Args:
        capture_startup: If True, capture comprehensive startup context including scene analysis
    """
    try:
        result = await vision_live_service.start()
        
        # Update user settings
        user_settings = settings_manager.load()
        user_settings.vision_enabled = True
        settings_manager.save(user_settings)
        
        # Capture startup context (who is this, how do they feel, where are they)
        startup_context = None
        if capture_startup:
            async def scene_analyzer(image_b64: str) -> str:
                """Analyze the scene using vision model"""
                result = await vision_service.analyze_image(
                    image_b64,
                    prompt="Briefly describe the environment/setting you see. Focus on: location type (office, bedroom, living room, etc), lighting, and general atmosphere. Keep it to 1-2 sentences.",
                    model_type="general"
                )
                if result.get("success"):
                    return result.get("description", "")
                return ""
            
            try:
                startup_context = await vision_live_service.capture_startup_context(
                    scene_analyzer=scene_analyzer
                )
                logger.info(f"Startup context captured: {startup_context.identity or 'Unknown'}, {startup_context.emotion}")
            except Exception as e:
                logger.warning(f"Startup context capture failed (non-fatal): {e}")
        
        response = {
            "success": True, 
            "message": "Eyes opened", 
            **result
        }
        
        if startup_context:
            response["startup_context"] = startup_context.to_dict()
            response["greeting_context"] = startup_context.to_greeting_context()
        
        return response
    except Exception as e:
        logger.error(f"Failed to start vision: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/vision/live/stop")
async def vision_live_stop():
    """Close Gala's eyes - stop real-time vision analysis"""
    try:
        result = await vision_live_service.stop()
        
        # Clear startup context
        vision_live_service.clear_startup_context()
        
        # Update user settings
        user_settings = settings_manager.load()
        user_settings.vision_enabled = False
        settings_manager.save(user_settings)
        return {"success": True, "message": "Eyes closed", **result}
    except Exception as e:
        logger.error(f"Failed to stop vision: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/vision/live/status")
async def vision_live_status():
    """Get current vision status and latest analysis"""
    try:
        status = await vision_live_service.get_status()
        
        # Include startup context if available
        startup_ctx = vision_live_service.get_startup_context()
        if startup_ctx:
            status["startup_context"] = startup_ctx.to_dict()
            status["greeting_context"] = startup_ctx.to_greeting_context()
        
        return status
    except Exception as e:
        logger.error(f"Failed to get vision status: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/vision/live/startup-context")
async def get_startup_context():
    """Get the current startup context (captured when eyes opened)"""
    startup_ctx = vision_live_service.get_startup_context()
    
    if not startup_ctx:
        return {
            "has_context": False,
            "message": "No startup context available. Open Gala's eyes to capture context."
        }
    
    return {
        "has_context": True,
        "context": startup_ctx.to_dict(),
        "greeting_context": startup_ctx.to_greeting_context()
    }


# ============== Face Recognition ==============

@router.post("/faces/enroll")
async def enroll_face(
    name: str = Body(...),
    role: str = Body("friend"),
    image: str = Body(None)
):
    """
    Enroll a face for recognition
    
    - name: Name of the person
    - role: "owner", "friend", or "family"
    - image: Optional base64 image, or None to capture from webcam
    """
    try:
        result = await vision_live_service.enroll_face(name, role, image)
        return result
    except Exception as e:
        logger.error(f"Face enrollment failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/faces")
async def list_faces():
    """List all enrolled faces"""
    try:
        result = await vision_live_service.list_faces()
        return result
    except Exception as e:
        logger.error(f"Failed to list faces: {e}")
        return JSONResponse(
            status_code=500,
            content={"faces": [], "owner_enrolled": False, "error": str(e)}
        )


@router.delete("/faces/{face_id}")
async def delete_face(face_id: str):
    """Delete an enrolled face"""
    try:
        result = await vision_live_service.delete_face(face_id)
        return result
    except Exception as e:
        logger.error(f"Failed to delete face: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/faces/capture")
async def capture_frame_for_enrollment():
    """Capture a frame from webcam for enrollment preview"""
    try:
        result = await vision_live_service.capture_frame()
        return result
    except Exception as e:
        logger.error(f"Frame capture failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/faces/check-owner")
async def check_owner():
    """Check if owner is enrolled"""
    try:
        has_owner = await vision_live_service.has_owner()
        owner_name = await vision_live_service.get_owner_name() if has_owner else None
        return {
            "owner_enrolled": has_owner,
            "owner_name": owner_name
        }
    except Exception as e:
        logger.error(f"Owner check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"owner_enrolled": False, "error": str(e)}
        )


# ============== Domain Routing ==============

@router.get("/routing/specialists")
async def get_specialists():
    """Get list of enabled specialist domains and models"""
    return {
        "specialists": domain_router.get_enabled_specialists(),
        "routing_enabled": settings_manager.load().domain_routing_enabled
    }


@router.post("/routing/detect")
async def detect_domain(text: str = Body(..., embed=True)):
    """Detect the domain of a query (for testing/debugging)"""
    domain, confidence, model, voice = domain_router.detect_domain(text)
    return {
        "domain": domain.value,
        "confidence": confidence,
        "specialist_model": model,
        "voice_override": voice,
        "would_route": model is not None and confidence >= 0.4
    }


@router.post("/routing/configure")
async def configure_routing(
    domain: str = Body(...),
    model: str = Body(...),
    enabled: bool = Body(True)
):
    """Configure a specialist model for a domain"""
    try:
        domain_enum = Domain(domain)
        domain_router.configure_specialist(domain_enum, model, enabled)
        
        # Also update user settings
        user_settings = settings_manager.load()
        spec_models = user_settings.specialist_models
        
        if domain == "medical":
            spec_models.medical = model if enabled else ""
        elif domain == "legal":
            spec_models.legal = model if enabled else ""
        elif domain == "coding":
            spec_models.coding = model if enabled else ""
        elif domain == "math":
            spec_models.math = model if enabled else ""
        elif domain == "finance":
            spec_models.finance = model if enabled else ""
        elif domain == "science":
            spec_models.science = model if enabled else ""
        elif domain == "creative":
            spec_models.creative = model if enabled else ""
        
        user_settings.specialist_models = spec_models
        settings_manager.save(user_settings)
        
        return {"success": True, "domain": domain, "model": model, "enabled": enabled}
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": f"Unknown domain: {domain}"}
        )
