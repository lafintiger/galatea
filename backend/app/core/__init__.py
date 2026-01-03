"""Core module - logging, exceptions, constants, and shared utilities."""
from .logging import get_logger, setup_logging
from .constants import (
    MessageType,
    ResponseType,
    Status,
    VisionCommand,
    WorkspaceAction,
    MCPAction,
    ToolName,
    TTSProvider,
    ResponseStyle,
    ActivationMode,
)
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
from .intent import detect_search_intent, detect_vision_command, detect_workspace_command, detect_describe_view_command
from .tts import synthesize_tts

__all__ = [
    # Logging
    "get_logger",
    "setup_logging",
    # Constants
    "MessageType",
    "ResponseType",
    "Status",
    "VisionCommand",
    "WorkspaceAction",
    "MCPAction",
    "ToolName",
    "TTSProvider",
    "ResponseStyle",
    "ActivationMode",
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
    "detect_describe_view_command",
    # TTS
    "synthesize_tts",
]

