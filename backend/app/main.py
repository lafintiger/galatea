"""Galatea Backend - Main FastAPI Application.

This is the entry point for the Galatea backend. It:
- Sets up the FastAPI application
- Configures CORS middleware
- Includes API and WebSocket routers
- Handles application lifespan (startup/shutdown)

All business logic has been moved to:
- app/routers/api.py - REST endpoints
- app/routers/websocket.py - WebSocket handler
- app/core/ - Shared utilities (logging, exceptions, audio, intent)
- app/services/ - External service clients
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core import get_logger, setup_logging
from .config import settings
from .routers import api_router, websocket_router
from .services.settings_manager import settings_manager
from .services.model_manager import model_manager
from .services.embedding import embedding_service
from .services.background_worker import background_worker

# Initialize logging
setup_logging(level="INFO")
logger = get_logger(__name__)


async def warmup_model(model_name: str) -> bool:
    """Pre-load the LLM model into VRAM for instant responses."""
    logger.info(f"Loading model: {model_name}")
    try:
        success = await model_manager.load_model(model_name)
        if success:
            logger.info(f"Model {model_name} is ready")
        else:
            logger.warning("Model warmup completed (may not be loaded)")
        return success
    except Exception as e:
        logger.warning(f"Model warmup failed: {e}")
        logger.info("First message may have a delay while model loads")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown."""
    # Startup
    logger.info("Galatea is waking up...")
    logger.info(f"Ollama: {settings.ollama_base_url}")
    logger.info(f"Whisper: {settings.whisper_host}:{settings.whisper_port}")
    logger.info(f"Piper: {settings.piper_host}:{settings.piper_port}")
    logger.info(f"LanceDB: {embedding_service.db_path}")
    
    # Load user settings
    user_settings = settings_manager.load()
    
    # Pre-load the LLM model
    await warmup_model(user_settings.selected_model)
    
    # Start background embedding worker
    background_worker.start(user_settings.selected_model)
    
    logger.info("Galatea is ready!")
    
    yield
    
    # Shutdown
    background_worker.stop()
    logger.info("Galatea is going to sleep...")


# Create FastAPI application
app = FastAPI(
    title="Galatea",
    description="Local Voice AI Companion",
    version="0.2.0",
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

# Include routers
app.include_router(api_router)
app.include_router(websocket_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
