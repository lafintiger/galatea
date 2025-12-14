"""Custom exceptions for Galatea.

These provide clear, actionable error messages for troubleshooting.

Exception Hierarchy:
    GalateaError (base)
    ├── ServiceUnavailableError - External service not responding
    ├── ModelNotFoundError - Requested model not available
    ├── AudioProcessingError - Audio encoding/decoding issues
    ├── TranscriptionError - STT failures
    ├── TTSError - Text-to-speech failures
    ├── LLMError - LLM generation failures
    └── ConfigurationError - Invalid configuration

Usage:
    from app.core import ServiceUnavailableError
    
    try:
        await ollama_client.chat(...)
    except httpx.ConnectError:
        raise ServiceUnavailableError(
            "Ollama",
            "http://localhost:11434",
            "Is Ollama running? Try: ollama serve"
        )
"""
from typing import Optional


class GalateaError(Exception):
    """Base exception for all Galatea errors.
    
    Attributes:
        message: Human-readable error description
        details: Optional additional context
    """
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON responses."""
        result = {"error": self.message, "type": self.__class__.__name__}
        if self.details:
            result["details"] = self.details
        return result


class ServiceUnavailableError(GalateaError):
    """An external service (Ollama, Whisper, etc.) is not responding.
    
    Attributes:
        service_name: Name of the service (e.g., "Ollama", "Whisper")
        url: The URL we tried to reach
        suggestion: How to fix it
    """
    
    def __init__(
        self, 
        service_name: str,
        url: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        self.service_name = service_name
        self.url = url
        self.suggestion = suggestion
        
        message = f"{service_name} is not responding"
        details = None
        
        if url:
            message += f" at {url}"
        
        if suggestion:
            details = suggestion
        
        super().__init__(message, details)


class ModelNotFoundError(GalateaError):
    """A requested model is not available.
    
    Attributes:
        model_name: The model that was requested
        available_models: List of models that are available
    """
    
    def __init__(
        self,
        model_name: str,
        available_models: Optional[list[str]] = None
    ):
        self.model_name = model_name
        self.available_models = available_models
        
        message = f"Model '{model_name}' not found"
        details = None
        
        if available_models:
            details = f"Available models: {', '.join(available_models[:5])}"
            if len(available_models) > 5:
                details += f" (+{len(available_models) - 5} more)"
        
        super().__init__(message, details)


class AudioProcessingError(GalateaError):
    """Audio encoding/decoding failed.
    
    Attributes:
        operation: What we were trying to do (encode, decode, convert)
        format: The audio format involved
    """
    
    def __init__(
        self,
        operation: str,
        format: Optional[str] = None,
        cause: Optional[str] = None
    ):
        self.operation = operation
        self.format = format
        
        message = f"Audio {operation} failed"
        if format:
            message += f" for {format} format"
        
        super().__init__(message, cause)


class TranscriptionError(GalateaError):
    """Speech-to-text transcription failed.
    
    Attributes:
        provider: The STT provider (e.g., "Whisper")
        audio_duration: Duration of the audio in seconds
    """
    
    def __init__(
        self,
        provider: str = "Whisper",
        audio_duration: Optional[float] = None,
        cause: Optional[str] = None
    ):
        self.provider = provider
        self.audio_duration = audio_duration
        
        message = f"{provider} transcription failed"
        details = cause
        
        if audio_duration is not None:
            if audio_duration < 0.5:
                details = "Audio too short (< 0.5s)"
            elif audio_duration > 300:
                details = "Audio too long (> 5 minutes)"
        
        super().__init__(message, details)


class TTSError(GalateaError):
    """Text-to-speech synthesis failed.
    
    Attributes:
        provider: The TTS provider (e.g., "Piper", "Kokoro")
        voice: The voice that was requested
        text_length: Length of text being synthesized
    """
    
    def __init__(
        self,
        provider: str,
        voice: Optional[str] = None,
        text_length: Optional[int] = None,
        cause: Optional[str] = None
    ):
        self.provider = provider
        self.voice = voice
        self.text_length = text_length
        
        message = f"{provider} TTS synthesis failed"
        details = cause
        
        if voice:
            message += f" for voice '{voice}'"
        
        if text_length and text_length > 5000:
            details = "Text too long - try shorter segments"
        
        super().__init__(message, details)


class LLMError(GalateaError):
    """LLM generation failed.
    
    Attributes:
        provider: The LLM provider (e.g., "Ollama")
        model: The model being used
        operation: What we were trying to do (chat, generate, embed)
    """
    
    def __init__(
        self,
        provider: str = "Ollama",
        model: Optional[str] = None,
        operation: str = "generation",
        cause: Optional[str] = None
    ):
        self.provider = provider
        self.model = model
        self.operation = operation
        
        message = f"{provider} {operation} failed"
        if model:
            message += f" with model '{model}'"
        
        super().__init__(message, cause)


class ConfigurationError(GalateaError):
    """Invalid or missing configuration.
    
    Attributes:
        setting: The setting that's problematic
        current_value: What the value currently is
        expected: What it should be
    """
    
    def __init__(
        self,
        setting: str,
        current_value: Optional[str] = None,
        expected: Optional[str] = None
    ):
        self.setting = setting
        self.current_value = current_value
        self.expected = expected
        
        message = f"Configuration error: {setting}"
        details = None
        
        if current_value is not None and expected:
            details = f"Got '{current_value}', expected {expected}"
        elif expected:
            details = f"Expected {expected}"
        
        super().__init__(message, details)

