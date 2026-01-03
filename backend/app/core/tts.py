"""TTS (Text-to-Speech) synthesis utilities.

Provides a unified interface for TTS synthesis across providers:
- Piper: Fast, CPU-friendly, Wyoming protocol
- Kokoro: High quality, OpenAI-compatible API
- Chatterbox: State-of-the-art with voice cloning
"""
from ..core import get_logger
from ..services.kokoro import kokoro_service
from ..services.wyoming import piper_service
from ..services.chatterbox import chatterbox_service

logger = get_logger(__name__)


async def synthesize_tts(
    text: str,
    voice: str,
    provider: str = "piper",
    speed: float = 1.0,
    variation: float = 0.8,
    phoneme_var: float = 0.6,
    # Chatterbox-specific options
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
) -> bytes:
    """Synthesize text to speech using the specified provider.
    
    Args:
        text: Text to synthesize
        voice: Voice ID
        provider: TTS provider ("piper", "kokoro", or "chatterbox")
        speed: Speaking speed (1.0 = normal)
        variation: Voice variation/expressiveness (Piper only)
        phoneme_var: Phoneme timing variation (Piper only)
        exaggeration: Expressiveness 0-1 (Chatterbox only)
        cfg_weight: Reference adherence 0-1 (Chatterbox only)
        
    Returns:
        WAV audio bytes
    """
    if provider == "chatterbox":
        return await chatterbox_service.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )
    elif provider == "kokoro":
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


async def get_available_providers() -> list[dict]:
    """Get list of available TTS providers with their status."""
    providers = []
    
    # Check Piper
    try:
        # Piper doesn't have a health check, assume available
        providers.append({
            "id": "piper",
            "name": "Piper",
            "description": "Fast, CPU-friendly TTS",
            "available": True,
            "features": ["fast", "lightweight"]
        })
    except Exception:
        pass
    
    # Check Kokoro
    try:
        kokoro_available = await kokoro_service.is_available()
        providers.append({
            "id": "kokoro",
            "name": "Kokoro",
            "description": "High-quality TTS",
            "available": kokoro_available,
            "features": ["high_quality", "multiple_voices"]
        })
    except Exception:
        pass
    
    # Check Chatterbox
    try:
        chatterbox_available = await chatterbox_service.is_available()
        providers.append({
            "id": "chatterbox",
            "name": "Chatterbox",
            "description": "State-of-the-art TTS with voice cloning",
            "available": chatterbox_available,
            "features": ["voice_cloning", "paralinguistics", "highest_quality"]
        })
    except Exception:
        pass
    
    return providers
