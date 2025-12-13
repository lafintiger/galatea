"""TTS (Text-to-Speech) synthesis utilities.

Provides a unified interface for TTS synthesis across providers.
"""
from ..core import get_logger
from ..services.kokoro import kokoro_service
from ..services.wyoming import piper_service

logger = get_logger(__name__)


async def synthesize_tts(
    text: str,
    voice: str,
    provider: str = "piper",
    speed: float = 1.0,
    variation: float = 0.8,
    phoneme_var: float = 0.6,
) -> bytes:
    """Synthesize text to speech using the specified provider.
    
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
