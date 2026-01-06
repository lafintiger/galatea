"""Parakeet ASR Server - FastAPI wrapper for NVIDIA Parakeet STT.

Provides a REST API for speech-to-text using NVIDIA's Parakeet model.
Supports both batch transcription and streaming.

API Endpoints:
- POST /v1/audio/transcriptions - Transcribe audio (OpenAI compatible)
- POST /v1/audio/transcriptions/stream - Streaming transcription
- GET /v1/models - List available models
- GET /health - Health check
"""
import os
import io
import base64
import logging
import tempfile
from typing import Optional
from contextlib import asynccontextmanager

import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = os.environ.get("PARAKEET_MODEL", "nvidia/parakeet-ctc-1.1b")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Global model instance
model = None
processor = None


def get_device():
    """Get the best available device."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model():
    """Load Parakeet model on startup."""
    global model, processor
    
    device = get_device()
    logger.info(f"Loading Parakeet model {MODEL_NAME} on device: {device}")
    
    try:
        # Try loading from NeMo
        import nemo.collections.asr as nemo_asr
        
        # Load pretrained model
        model = nemo_asr.models.ASRModel.from_pretrained(MODEL_NAME)
        model = model.to(device)
        model.eval()
        
        logger.info(f"Parakeet model loaded successfully")
        return True
        
    except ImportError:
        logger.warning("NeMo not available, trying HuggingFace transformers...")
        
        try:
            from transformers import AutoModelForCTC, AutoProcessor
            
            processor = AutoProcessor.from_pretrained(MODEL_NAME)
            model = AutoModelForCTC.from_pretrained(MODEL_NAME)
            model = model.to(device)
            model.eval()
            
            logger.info("Parakeet model loaded via HuggingFace")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    except Exception as e:
        logger.error(f"Failed to load Parakeet model: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    load_model()
    yield
    # Cleanup
    global model, processor
    model = None
    processor = None


app = FastAPI(
    title="Parakeet ASR Server",
    description="NVIDIA Parakeet Speech-to-Text API",
    version="1.0.0",
    lifespan=lifespan
)


# =========================================
# Pydantic Models
# =========================================

class TranscriptionRequest(BaseModel):
    """Transcription request (OpenAI compatible)."""
    audio: str  # Base64 encoded audio
    model: str = "parakeet-ctc-1.1b"
    language: str = "en"
    sample_rate: int = 16000
    response_format: str = "json"


class TranscriptionResponse(BaseModel):
    """Transcription response."""
    text: str
    language: str = "en"
    duration: Optional[float] = None


class StreamingRequest(BaseModel):
    """Streaming transcription request."""
    audio: str  # Base64 encoded audio chunk
    session_id: str
    is_final: bool = False
    model: str = "parakeet-ctc-1.1b"


class StreamingResponse(BaseModel):
    """Streaming transcription response."""
    text: Optional[str] = None
    partial_text: Optional[str] = None
    is_partial: bool = False
    is_final: bool = False


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    type: str
    streaming: bool


# Streaming sessions storage
streaming_sessions = {}


# =========================================
# Helper Functions
# =========================================

def decode_audio(audio_b64: str, sample_rate: int = 16000) -> torch.Tensor:
    """Decode base64 audio to tensor."""
    audio_bytes = base64.b64decode(audio_b64)
    
    # Try to read as audio file first
    try:
        with io.BytesIO(audio_bytes) as audio_io:
            audio_data, sr = sf.read(audio_io)
            
            # Resample if needed
            if sr != sample_rate:
                import torchaudio.transforms as T
                resampler = T.Resample(sr, sample_rate)
                audio_tensor = torch.tensor(audio_data, dtype=torch.float32)
                if audio_tensor.dim() == 1:
                    audio_tensor = audio_tensor.unsqueeze(0)
                audio_data = resampler(audio_tensor).squeeze().numpy()
            
            return torch.tensor(audio_data, dtype=torch.float32)
    except Exception:
        # Assume raw PCM
        import numpy as np
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return torch.tensor(audio_array, dtype=torch.float32)


def transcribe_nemo(audio_tensor: torch.Tensor) -> str:
    """Transcribe using NeMo model."""
    global model
    
    device = get_device()
    
    # Save to temp file (NeMo prefers file input)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
        sf.write(f.name, audio_tensor.numpy(), 16000)
        
        # Transcribe
        with torch.no_grad():
            transcription = model.transcribe([f.name])
        
        if isinstance(transcription, list):
            return transcription[0] if transcription else ""
        return str(transcription)


def transcribe_hf(audio_tensor: torch.Tensor) -> str:
    """Transcribe using HuggingFace model."""
    global model, processor
    
    device = get_device()
    
    # Process audio
    inputs = processor(
        audio_tensor.numpy(),
        sampling_rate=16000,
        return_tensors="pt",
        padding=True
    )
    
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Generate
    with torch.no_grad():
        logits = model(**inputs).logits
    
    # Decode
    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = processor.batch_decode(predicted_ids)
    
    return transcription[0] if transcription else ""


# =========================================
# API Endpoints
# =========================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy" if model is not None else "loading",
        "model": MODEL_NAME,
        "device": get_device(),
        "cuda_available": torch.cuda.is_available()
    }


@app.get("/v1/models")
async def list_models():
    """List available models."""
    models = [
        ModelInfo(id="parakeet-ctc-1.1b", name="Parakeet CTC 1.1B", type="ctc", streaming=True),
        ModelInfo(id="parakeet-tdt-1.1b", name="Parakeet TDT 1.1B", type="tdt", streaming=True),
    ]
    return {"models": [m.dict() for m in models]}


@app.post("/v1/audio/transcriptions")
async def create_transcription(request: TranscriptionRequest):
    """Transcribe audio (OpenAI compatible endpoint)."""
    
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        # Decode audio
        audio_tensor = decode_audio(request.audio, request.sample_rate)
        duration = len(audio_tensor) / request.sample_rate
        
        logger.info(f"Transcribing {duration:.2f}s of audio...")
        
        # Transcribe based on backend
        if processor is not None:
            text = transcribe_hf(audio_tensor)
        else:
            text = transcribe_nemo(audio_tensor)
        
        logger.info(f"Transcription: {text[:50]}...")
        
        return TranscriptionResponse(
            text=text,
            language=request.language,
            duration=duration
        )
    
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/audio/transcriptions/stream")
async def create_streaming_transcription(request: StreamingRequest):
    """Streaming transcription endpoint."""
    
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    
    try:
        # Get or create session
        session_id = request.session_id
        
        if session_id not in streaming_sessions:
            streaming_sessions[session_id] = {
                "audio_chunks": [],
                "partial_text": ""
            }
        
        session = streaming_sessions[session_id]
        
        # Decode and add audio chunk
        audio_chunk = decode_audio(request.audio)
        session["audio_chunks"].append(audio_chunk)
        
        # Concatenate all audio
        full_audio = torch.cat(session["audio_chunks"])
        
        # Transcribe
        if processor is not None:
            text = transcribe_hf(full_audio)
        else:
            text = transcribe_nemo(full_audio)
        
        if request.is_final:
            # Clean up session
            del streaming_sessions[session_id]
            
            return StreamingResponse(
                text=text,
                is_final=True
            )
        else:
            # Return partial result
            session["partial_text"] = text
            
            return StreamingResponse(
                partial_text=text,
                is_partial=True
            )
    
    except Exception as e:
        logger.error(f"Streaming transcription failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=50052)
