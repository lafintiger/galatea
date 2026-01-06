"""NVIDIA Parakeet STT Service - Fast streaming speech recognition.

Parakeet is NVIDIA's state-of-the-art ASR model from the NeMo toolkit:
- Parakeet-CTC: Fast, streaming capable
- Parakeet-TDT: Higher accuracy Token-Duration Transducer

Advantages over Whisper:
- Real-time streaming support
- Lower latency (~50-100ms vs ~1-2s)
- TensorRT optimized for NVIDIA GPUs

Docker container runs on port 50052 with REST/gRPC API.
"""
import httpx
from typing import Optional
import base64

from ..config import settings
from ..core import get_logger
from ..core.exceptions import TranscriptionError, ServiceUnavailableError

logger = get_logger(__name__)


class ParakeetService:
    """NVIDIA Parakeet ASR Service.
    
    Provides speech-to-text using NVIDIA's Parakeet model,
    which offers lower latency than Whisper for real-time applications.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'parakeet_base_url', 'http://localhost:50052')
        self.model = getattr(settings, 'parakeet_model', 'parakeet-ctc-1.1b')
        self._client: Optional[httpx.AsyncClient] = None
        self._is_available: Optional[bool] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en",
        sample_rate: int = 16000,
    ) -> str:
        """Transcribe audio to text.
        
        Args:
            audio_data: Raw audio bytes (WAV or raw PCM)
            language: Language code (e.g., "en", "es")
            sample_rate: Audio sample rate in Hz
            
        Returns:
            Transcribed text
            
        Raises:
            STTError: If transcription fails
            ServiceUnavailableError: If Parakeet is not reachable
        """
        url = f"{self.base_url}/v1/audio/transcriptions"
        
        # Encode audio as base64 for JSON transport
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        payload = {
            "audio": audio_b64,
            "model": self.model,
            "language": language,
            "sample_rate": sample_rate,
            "response_format": "json"
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            text = result.get("text", "").strip()
            
            logger.debug(f"Parakeet transcribed: {text[:50]}...")
            return text
            
        except httpx.ConnectError as e:
            logger.warning(f"Cannot connect to Parakeet at {self.base_url}")
            raise ServiceUnavailableError(
                service_name="Parakeet",
                url=self.base_url,
                suggestion="Is the Parakeet container running? Start with: docker compose --profile parakeet up"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Parakeet HTTP error: {e.response.status_code}")
            raise TranscriptionError(
                provider="Parakeet",
                cause=f"HTTP {e.response.status_code}: {e.response.text[:100]}"
            )
        except Exception as e:
            logger.error(f"Parakeet transcription failed: {e}")
            raise TranscriptionError(
                provider="Parakeet",
                cause=str(e)
            )
    
    async def transcribe_streaming(
        self,
        audio_chunk: bytes,
        session_id: str,
        is_final: bool = False,
    ) -> Optional[str]:
        """Stream audio for real-time transcription.
        
        Args:
            audio_chunk: Audio chunk bytes
            session_id: Session ID for maintaining context
            is_final: Whether this is the final chunk
            
        Returns:
            Partial or final transcription, or None if still processing
        """
        url = f"{self.base_url}/v1/audio/transcriptions/stream"
        
        audio_b64 = base64.b64encode(audio_chunk).decode('utf-8')
        
        payload = {
            "audio": audio_b64,
            "session_id": session_id,
            "is_final": is_final,
            "model": self.model
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("is_partial"):
                # Partial result - could show in UI
                return result.get("partial_text")
            elif result.get("text"):
                return result.get("text").strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Parakeet streaming error: {e}")
            return None
    
    async def get_info(self) -> Optional[dict]:
        """Get Parakeet server info."""
        try:
            url = f"{self.base_url}/health"
            response = await self.client.get(url, timeout=5.0)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Parakeet health check failed: {e}")
        return None
    
    async def is_available(self) -> bool:
        """Check if Parakeet service is available."""
        try:
            info = await self.get_info()
            self._is_available = info is not None and info.get("status") == "healthy"
            return self._is_available
        except Exception:
            self._is_available = False
            return False
    
    async def list_models(self) -> list[dict]:
        """List available Parakeet models."""
        try:
            url = f"{self.base_url}/v1/models"
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.json().get("models", [])
        except Exception as e:
            logger.debug(f"Could not list Parakeet models: {e}")
        
        # Return default models
        return [
            {"id": "parakeet-ctc-1.1b", "name": "Parakeet CTC 1.1B", "type": "ctc", "streaming": True},
            {"id": "parakeet-tdt-1.1b", "name": "Parakeet TDT 1.1B", "type": "tdt", "streaming": True},
        ]


# Singleton instance
parakeet_service = ParakeetService()
