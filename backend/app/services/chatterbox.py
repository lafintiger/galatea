"""Chatterbox TTS Service - State-of-the-art TTS with voice cloning.

Chatterbox provides:
- High-quality zero-shot voice cloning
- Paralinguistic tags ([laugh], [cough], [chuckle])
- Turbo mode for low-latency voice agents
- 23+ language support (multilingual model)

Docker container runs on port 8881 with OpenAI-compatible API.
"""
import httpx
from typing import Optional
from pathlib import Path

from ..config import settings
from ..core import get_logger
from ..core.exceptions import TTSError, ServiceUnavailableError

logger = get_logger(__name__)


class ChatterboxService:
    """Chatterbox TTS Service using OpenAI-compatible API."""
    
    # Built-in voices (reference-based, can add more via cloning)
    VOICES = [
        {"id": "default", "name": "Default (Female)", "language": "en", "quality": "high", "gender": "female"},
    ]
    
    def __init__(self):
        # Use environment variable or default
        self.base_url = getattr(settings, 'chatterbox_base_url', 'http://localhost:8881')
        self.default_voice = "default"
        self._client: Optional[httpx.AsyncClient] = None
        self._is_available: Optional[bool] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)  # Longer timeout for TTS
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        model: str = "chatterbox-turbo",
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        **kwargs
    ) -> bytes:
        """Synthesize text to audio (WAV format).
        
        Args:
            text: Text to synthesize (can include [laugh], [cough], etc.)
            voice: Voice ID ("default" or a cloned voice ID)
            speed: Speaking speed (currently not used by Chatterbox)
            model: "chatterbox-turbo" (fast) or "chatterbox" (quality)
            exaggeration: 0-1, expressiveness (standard model only)
            cfg_weight: 0-1, adherence to reference voice (standard model only)
            
        Returns:
            WAV audio bytes
            
        Raises:
            TTSError: If synthesis fails
            ServiceUnavailableError: If Chatterbox is not reachable
        """
        voice = voice or self.default_voice
        url = f"{self.base_url}/v1/audio/speech"
        
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "wav",
            "speed": speed,
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            logger.debug(f"Synthesized {len(text)} chars with Chatterbox voice {voice}")
            return response.content
            
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Chatterbox at {self.base_url}")
            raise ServiceUnavailableError(
                service_name="Chatterbox",
                url=self.base_url,
                suggestion="Is the Chatterbox container running? Check: docker ps | grep chatterbox"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Chatterbox HTTP error: {e.response.status_code}")
            raise TTSError(
                provider="Chatterbox",
                voice=voice,
                text_length=len(text),
                cause=f"HTTP {e.response.status_code}: {e.response.text[:100]}"
            )
        except httpx.RequestError as e:
            logger.error(f"Chatterbox request failed: {e}")
            raise TTSError(
                provider="Chatterbox",
                voice=voice,
                cause=str(e)
            )
    
    async def clone_voice(
        self,
        name: str,
        audio_bytes: bytes,
        filename: str = "reference.wav"
    ) -> dict:
        """Clone a voice from reference audio.
        
        Args:
            name: Name for the cloned voice
            audio_bytes: WAV audio bytes (10+ seconds recommended)
            filename: Original filename
            
        Returns:
            Dict with voice_id and message
        """
        url = f"{self.base_url}/v1/audio/clone"
        
        try:
            files = {"audio": (filename, audio_bytes, "audio/wav")}
            data = {"name": name}
            
            response = await self.client.post(url, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Voice cloned: {name} -> {result.get('voice_id')}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Voice cloning failed: {e.response.status_code}")
            raise TTSError(
                provider="Chatterbox",
                cause=f"Voice cloning failed: {e.response.text[:100]}"
            )
        except Exception as e:
            logger.error(f"Voice cloning error: {e}")
            raise TTSError(
                provider="Chatterbox",
                cause=f"Voice cloning error: {str(e)}"
            )
    
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice.
        
        Args:
            voice_id: ID of the voice to delete
            
        Returns:
            True if deleted successfully
        """
        url = f"{self.base_url}/v1/audio/voices/{voice_id}"
        
        try:
            response = await self.client.delete(url)
            response.raise_for_status()
            logger.info(f"Voice deleted: {voice_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete voice {voice_id}: {e}")
            return False
    
    async def list_voices(self) -> list[dict]:
        """List available voices (built-in + cloned)."""
        try:
            url = f"{self.base_url}/v1/audio/voices"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                voices = []
                for v in data.get("voices", []):
                    voices.append({
                        "id": v.get("id", "default"),
                        "name": v.get("name", "Default"),
                        "language": v.get("language", "en"),
                        "quality": "high",
                        "gender": "female" if "female" in v.get("name", "").lower() else "unknown",
                        "is_cloned": v.get("is_cloned", False)
                    })
                if voices:
                    logger.debug(f"Fetched {len(voices)} voices from Chatterbox")
                    return voices
        except Exception as e:
            logger.debug(f"Could not fetch voices from Chatterbox: {e}")
        
        # Return static voice list as fallback
        return self.VOICES
    
    async def get_info(self) -> Optional[dict]:
        """Get Chatterbox server info."""
        try:
            url = f"{self.base_url}/health"
            response = await self.client.get(url, timeout=5.0)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Chatterbox health check failed: {e}")
        return None
    
    async def is_available(self) -> bool:
        """Check if Chatterbox service is available."""
        try:
            info = await self.get_info()
            self._is_available = info is not None and info.get("status") == "healthy"
            return self._is_available
        except Exception:
            self._is_available = False
            return False


# Singleton instance
chatterbox_service = ChatterboxService()
