"""Chatterbox TTS Server - FastAPI wrapper for Chatterbox TTS.

Provides an OpenAI-compatible TTS API for Galatea integration.
Supports both Chatterbox-Turbo (fast, English) and Chatterbox (quality, English).

API Endpoints:
- POST /v1/audio/speech - Generate speech (OpenAI compatible)
- GET /v1/audio/voices - List available voices
- POST /v1/audio/clone - Clone a voice from reference audio
- GET /health - Health check
"""
import os
import io
import wave
import hashlib
import logging
from pathlib import Path
from typing import Optional, Literal

import torch
import torchaudio as ta
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Chatterbox TTS Server",
    description="OpenAI-compatible TTS API powered by Chatterbox",
    version="1.0.0"
)

# Global model instances
turbo_model = None
standard_model = None

# Voice reference storage
VOICES_DIR = Path("/app/voices")
VOICES_DIR.mkdir(parents=True, exist_ok=True)

# Default reference voice (will be downloaded on first use)
DEFAULT_VOICE_URL = "https://huggingface.co/spaces/ResembleAI/chatterbox-turbo-demo/resolve/main/assets/reference.wav"


def get_device():
    """Get the best available device."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_models():
    """Load Chatterbox models on startup."""
    global turbo_model, standard_model
    device = get_device()
    logger.info(f"Loading models on device: {device}")
    
    try:
        # Load Turbo model (faster, supports paralinguistic tags)
        from chatterbox.tts_turbo import ChatterboxTurboTTS
        turbo_model = ChatterboxTurboTTS.from_pretrained(device=device)
        logger.info("Chatterbox Turbo model loaded")
    except Exception as e:
        logger.warning(f"Could not load Turbo model: {e}")
    
    try:
        # Load standard model (higher quality, more control)
        from chatterbox.tts import ChatterboxTTS
        standard_model = ChatterboxTTS.from_pretrained(device=device)
        logger.info("Chatterbox Standard model loaded")
    except Exception as e:
        logger.warning(f"Could not load Standard model: {e}")
    
    if turbo_model is None and standard_model is None:
        raise RuntimeError("Failed to load any Chatterbox model")


def get_default_voice_path() -> Path:
    """Get or download default reference voice."""
    default_path = VOICES_DIR / "default.wav"
    if not default_path.exists():
        logger.info("Downloading default reference voice...")
        import urllib.request
        urllib.request.urlretrieve(DEFAULT_VOICE_URL, default_path)
        logger.info("Default voice downloaded")
    return default_path


def wav_to_bytes(wav_tensor: torch.Tensor, sample_rate: int) -> bytes:
    """Convert PyTorch tensor to WAV bytes."""
    # Ensure tensor is on CPU and correct shape
    wav = wav_tensor.cpu()
    if wav.dim() == 1:
        wav = wav.unsqueeze(0)
    
    # Convert to bytes
    buffer = io.BytesIO()
    ta.save(buffer, wav, sample_rate, format="wav")
    buffer.seek(0)
    return buffer.read()


# =========================================
# Pydantic Models
# =========================================

class TTSRequest(BaseModel):
    """OpenAI-compatible TTS request."""
    model: str = "chatterbox-turbo"  # "chatterbox-turbo" or "chatterbox"
    input: str
    voice: str = "default"  # Voice ID or "default"
    response_format: str = "wav"
    speed: float = 1.0
    # Chatterbox-specific options
    exaggeration: float = 0.5  # 0-1, expressiveness
    cfg_weight: float = 0.5  # 0-1, adherence to reference


class VoiceInfo(BaseModel):
    """Voice information."""
    id: str
    name: str
    is_cloned: bool = False
    language: str = "en"


class CloneResponse(BaseModel):
    """Voice cloning response."""
    voice_id: str
    name: str
    message: str


# =========================================
# API Endpoints
# =========================================

@app.on_event("startup")
async def startup():
    """Load models on startup."""
    load_models()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "turbo_loaded": turbo_model is not None,
        "standard_loaded": standard_model is not None,
        "device": get_device()
    }


@app.get("/v1/audio/voices")
async def list_voices():
    """List available voices."""
    voices = [
        VoiceInfo(id="default", name="Default (Female)", is_cloned=False)
    ]
    
    # Add cloned voices
    for voice_file in VOICES_DIR.glob("*.wav"):
        if voice_file.name != "default.wav":
            voice_id = voice_file.stem
            voices.append(VoiceInfo(
                id=voice_id,
                name=f"Cloned: {voice_id}",
                is_cloned=True
            ))
    
    return {"voices": [v.dict() for v in voices]}


@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """Generate speech from text (OpenAI-compatible)."""
    
    # Select model
    if request.model == "chatterbox-turbo" and turbo_model is not None:
        model = turbo_model
        use_turbo = True
    elif standard_model is not None:
        model = standard_model
        use_turbo = False
    elif turbo_model is not None:
        model = turbo_model
        use_turbo = True
    else:
        raise HTTPException(status_code=503, detail="No TTS model available")
    
    # Get voice reference path
    if request.voice == "default":
        voice_path = get_default_voice_path()
    else:
        voice_path = VOICES_DIR / f"{request.voice}.wav"
        if not voice_path.exists():
            raise HTTPException(status_code=404, detail=f"Voice '{request.voice}' not found")
    
    try:
        logger.info(f"Generating speech: model={'turbo' if use_turbo else 'standard'}, voice={request.voice}, text={request.input[:50]}...")
        
        if use_turbo:
            # Turbo model - simpler API
            wav = model.generate(
                request.input,
                audio_prompt_path=str(voice_path)
            )
        else:
            # Standard model - more options
            wav = model.generate(
                request.input,
                audio_prompt_path=str(voice_path),
                exaggeration=request.exaggeration,
                cfg_weight=request.cfg_weight
            )
        
        # Convert to bytes
        audio_bytes = wav_to_bytes(wav, model.sr)
        
        logger.info(f"Generated {len(audio_bytes)} bytes of audio")
        
        return Response(
            content=audio_bytes,
            media_type="audio/wav"
        )
    
    except Exception as e:
        logger.error(f"TTS generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/audio/clone")
async def clone_voice(
    name: str = Form(...),
    audio: UploadFile = File(...)
):
    """Clone a voice from reference audio.
    
    Upload a 10+ second audio clip to create a cloned voice.
    """
    # Read audio file
    audio_bytes = await audio.read()
    
    # Generate voice ID from name
    voice_id = hashlib.md5(name.encode()).hexdigest()[:8]
    
    # Save reference audio
    voice_path = VOICES_DIR / f"{voice_id}.wav"
    
    try:
        # Load and resample if needed
        buffer = io.BytesIO(audio_bytes)
        wav, sr = ta.load(buffer)
        
        # Resample to 24kHz if needed (Chatterbox expects this)
        if sr != 24000:
            resampler = ta.transforms.Resample(sr, 24000)
            wav = resampler(wav)
        
        # Save
        ta.save(str(voice_path), wav, 24000)
        
        logger.info(f"Voice cloned: {name} -> {voice_id}")
        
        return CloneResponse(
            voice_id=voice_id,
            name=name,
            message=f"Voice '{name}' cloned successfully. Use voice_id='{voice_id}' in TTS requests."
        )
    
    except Exception as e:
        logger.error(f"Voice cloning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/audio/voices/{voice_id}")
async def delete_voice(voice_id: str):
    """Delete a cloned voice."""
    if voice_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default voice")
    
    voice_path = VOICES_DIR / f"{voice_id}.wav"
    if not voice_path.exists():
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")
    
    voice_path.unlink()
    return {"message": f"Voice '{voice_id}' deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8881)
