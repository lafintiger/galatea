"""Core module - logging, exceptions, and shared utilities."""
from .logging import get_logger, setup_logging
from .exceptions import (
    GalateaError,
    ServiceUnavailableError,
    ModelNotFoundError,
    AudioProcessingError,
    TranscriptionError,
    TTSError,
    LLMError,
    ConfigurationError,
)
from .audio import clean_for_speech, split_into_sentences, detect_sentence_boundary
from .intent import detect_search_intent, detect_vision_command, detect_workspace_command
from .tts import synthesize_tts

__all__ = [
    # Logging
    "get_logger",
    "setup_logging",
    # Exceptions
    "GalateaError",
    "ServiceUnavailableError", 
    "ModelNotFoundError",
    "AudioProcessingError",
    "TranscriptionError",
    "TTSError",
    "LLMError",
    "ConfigurationError",
    # Audio utilities
    "clean_for_speech",
    "split_into_sentences",
    "detect_sentence_boundary",
    # Intent detection
    "detect_search_intent",
    "detect_vision_command",
    "detect_workspace_command",
    # TTS
    "synthesize_tts",
]

