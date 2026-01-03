"""Kokoro TTS Service - High quality text-to-speech via OpenAI-compatible API

Uses Kokoro-FastAPI Docker container which provides an OpenAI-compatible TTS endpoint.
"""
import httpx
from typing import Optional

from ..config import settings
from ..core import get_logger
from ..core.exceptions import TTSError, ServiceUnavailableError

logger = get_logger(__name__)


class KokoroService:
    """Kokoro TTS Service using OpenAI-compatible API"""
    
    # Available Kokoro voices (af_ = American Female, am_ = American Male, bf_ = British Female, etc.)
    VOICES = [
        # American Female voices
        {"id": "af_alloy", "name": "Alloy (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_aoede", "name": "Aoede (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_bella", "name": "Bella (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_heart", "name": "Heart (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_jessica", "name": "Jessica (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_kore", "name": "Kore (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_nicole", "name": "Nicole (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_nova", "name": "Nova (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_river", "name": "River (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_sarah", "name": "Sarah (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        {"id": "af_sky", "name": "Sky (American Female)", "language": "en_US", "quality": "high", "gender": "female"},
        # American Male voices
        {"id": "am_adam", "name": "Adam (American Male)", "language": "en_US", "quality": "high", "gender": "male"},
        {"id": "am_echo", "name": "Echo (American Male)", "language": "en_US", "quality": "high", "gender": "male"},
        {"id": "am_eric", "name": "Eric (American Male)", "language": "en_US", "quality": "high", "gender": "male"},
        {"id": "am_fenrir", "name": "Fenrir (American Male)", "language": "en_US", "quality": "high", "gender": "male"},
        {"id": "am_liam", "name": "Liam (American Male)", "language": "en_US", "quality": "high", "gender": "male"},
        {"id": "am_michael", "name": "Michael (American Male)", "language": "en_US", "quality": "high", "gender": "male"},
        {"id": "am_onyx", "name": "Onyx (American Male)", "language": "en_US", "quality": "high", "gender": "male"},
        # British Female voices
        {"id": "bf_alice", "name": "Alice (British Female)", "language": "en_GB", "quality": "high", "gender": "female"},
        {"id": "bf_emma", "name": "Emma (British Female)", "language": "en_GB", "quality": "high", "gender": "female"},
        {"id": "bf_isabella", "name": "Isabella (British Female)", "language": "en_GB", "quality": "high", "gender": "female"},
        {"id": "bf_lily", "name": "Lily (British Female)", "language": "en_GB", "quality": "high", "gender": "female"},
        # British Male voices
        {"id": "bm_daniel", "name": "Daniel (British Male)", "language": "en_GB", "quality": "high", "gender": "male"},
        {"id": "bm_fable", "name": "Fable (British Male)", "language": "en_GB", "quality": "high", "gender": "male"},
        {"id": "bm_george", "name": "George (British Male)", "language": "en_GB", "quality": "high", "gender": "male"},
        {"id": "bm_lewis", "name": "Lewis (British Male)", "language": "en_GB", "quality": "high", "gender": "male"},
    ]
    
    def __init__(self):
        self.base_url = settings.kokoro_base_url
        self.default_voice = settings.kokoro_default_voice
        self._client: Optional[httpx.AsyncClient] = None
        self._is_available: Optional[bool] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs  # Accept but ignore Piper-specific params like noise_scale, noise_w
    ) -> bytes:
        """Synthesize text to audio (WAV format)
        
        Args:
            text: Text to synthesize
            voice: Kokoro voice ID (e.g., "af_bella", "bf_emma")
            speed: Speaking speed (0.5-2.0, default 1.0)
            
        Returns:
            WAV audio bytes
            
        Raises:
            TTSError: If synthesis fails
            ServiceUnavailableError: If Kokoro is not reachable
        """
        voice = voice or self.default_voice
        url = f"{self.base_url}/v1/audio/speech"
        
        payload = {
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": "wav",
            "speed": speed
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            logger.debug(f"Synthesized {len(text)} chars with voice {voice}")
            return response.content
            
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Kokoro at {self.base_url}")
            raise ServiceUnavailableError(
                service_name="Kokoro",
                url=self.base_url,
                suggestion="Is the Kokoro container running? Check: docker ps | grep kokoro"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Kokoro HTTP error: {e.response.status_code}")
            raise TTSError(
                provider="Kokoro",
                voice=voice,
                text_length=len(text),
                cause=f"HTTP {e.response.status_code}: {e.response.text[:100]}"
            )
        except httpx.RequestError as e:
            logger.error(f"Kokoro request failed: {e}")
            raise TTSError(
                provider="Kokoro",
                voice=voice,
                cause=str(e)
            )
    
    async def list_voices(self) -> list[dict]:
        """List available Kokoro voices"""
        try:
            url = f"{self.base_url}/v1/audio/voices"
            response = await self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                voices = []
                raw_voices = data.get("voices", [])
                for voice in raw_voices:
                    if isinstance(voice, str):
                        voice_id = voice
                    else:
                        voice_id = voice.get("id") or voice.get("voice_id") or str(voice)
                    
                    if voice_id.startswith("af_") or voice_id.startswith("am_"):
                        language = "en_US"
                    elif voice_id.startswith("bf_") or voice_id.startswith("bm_"):
                        language = "en_GB"
                    else:
                        language = "en"
                    
                    gender = "female" if voice_id.startswith("af_") or voice_id.startswith("bf_") else "male"
                    
                    name_part = voice_id.split("_", 1)[1] if "_" in voice_id else voice_id
                    prefix = voice_id.split("_")[0] if "_" in voice_id else ""
                    
                    prefix_map = {
                        "af": "American Female",
                        "am": "American Male", 
                        "bf": "British Female",
                        "bm": "British Male"
                    }
                    prefix_desc = prefix_map.get(prefix, "")
                    display_name = f"{name_part.title()} ({prefix_desc})" if prefix_desc else name_part.title()
                    
                    voices.append({
                        "id": voice_id,
                        "name": display_name,
                        "language": language,
                        "quality": "high",
                        "gender": gender
                    })
                if voices:
                    logger.debug(f"Fetched {len(voices)} voices from Kokoro API")
                    return voices
        except Exception as e:
            logger.debug(f"Could not fetch voices from Kokoro API: {e}")
        
        # Return static voice list as fallback
        return self.VOICES
    
    async def get_info(self) -> Optional[dict]:
        """Get Kokoro server info"""
        try:
            url = f"{self.base_url}/health"
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Kokoro health check failed: {e}")
        return None
    
    async def is_available(self) -> bool:
        """Check if Kokoro service is available"""
        try:
            info = await self.get_info()
            self._is_available = info is not None
            return self._is_available
        except Exception:
            self._is_available = False
            return False


# Singleton instance
kokoro_service = KokoroService()
