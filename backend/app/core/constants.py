"""Constants for Galatea - Message types, statuses, and other enums.

Using string enums for JSON serialization compatibility while providing
IDE autocomplete and preventing typos.
"""
from enum import Enum


class MessageType(str, Enum):
    """WebSocket message types - client to server."""
    # Audio/Voice
    AUDIO_DATA = "audio_data"
    TEXT_MESSAGE = "text_message"
    SPEAK_TEXT = "speak_text"
    INTERRUPT = "interrupt"
    
    # Settings
    SETTINGS_UPDATE = "settings_update"
    CLEAR_HISTORY = "clear_history"
    
    # Vision
    OPEN_EYES = "open_eyes"
    CLOSE_EYES = "close_eyes"
    GET_VISION_STATUS = "get_vision_status"
    
    # Workspace
    WORKSPACE_RESULT = "workspace_result"
    
    # Search
    WEB_SEARCH = "web_search"


class ResponseType(str, Enum):
    """WebSocket response types - server to client."""
    # Status
    STATUS = "status"
    ERROR = "error"
    INTERRUPTED = "interrupted"
    
    # Settings
    SETTINGS_UPDATED = "settings_updated"
    HISTORY_CLEARED = "history_cleared"
    
    # Transcription/LLM
    TRANSCRIPTION = "transcription"
    LLM_CHUNK = "llm_chunk"
    LLM_COMPLETE = "llm_complete"
    
    # Audio
    AUDIO_CHUNK = "audio_chunk"
    
    # Vision
    VISION_STATUS = "vision_status"
    VISION_UPDATE = "vision_update"
    
    # Search
    SEARCH_START = "search_start"
    SEARCH_RESULTS = "search_results"
    
    # Workspace
    WORKSPACE_COMMAND = "workspace_command"
    
    # Domain routing
    DOMAIN_SWITCH = "domain_switch"


class Status(str, Enum):
    """Application status states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    SEARCHING = "searching"


class VisionCommand(str, Enum):
    """Vision system commands."""
    OPEN = "open"
    CLOSE = "close"
    DESCRIBE = "describe"


class WorkspaceAction(str, Enum):
    """Workspace actions."""
    ADD_TODO = "add_todo"
    ADD_NOTE = "add_note"
    COMPLETE_TODO = "complete_todo"
    LOG_DATA = "log_data"
    OPEN_WORKSPACE = "open_workspace"
    READ_TODOS = "read_todos"
    READ_NOTES = "read_notes"
    CLEAR_TODOS = "clear_todos"
    CLEAR_NOTES = "clear_notes"


class MCPAction(str, Enum):
    """MCP (Model Context Protocol) actions."""
    # Docker
    DOCKER_LIST = "docker_list"
    DOCKER_RESTART = "docker_restart"
    DOCKER_STATUS = "docker_status"
    DOCKER_LOGS = "docker_logs"
    
    # Home Assistant
    HA_TURN_ON = "ha_turn_on"
    HA_TURN_OFF = "ha_turn_off"
    HA_SET_TEMPERATURE = "ha_set_temperature"
    HA_GET_STATE = "ha_get_state"
    HA_LIST_DEVICES = "ha_list_devices"


class ToolName(str, Enum):
    """Command router tool names."""
    ADD_TODO = "add_todo"
    ADD_NOTE = "add_note"
    COMPLETE_TODO = "complete_todo"
    SEARCH_WEB = "search_web"
    OPEN_EYES = "open_eyes"
    CLOSE_EYES = "close_eyes"
    DESCRIBE_VIEW = "describe_view"
    LOG_DATA = "log_data"
    OPEN_WORKSPACE = "open_workspace"
    READ_TODOS = "read_todos"
    READ_NOTES = "read_notes"
    CLEAR_TODOS = "clear_todos"
    CLEAR_NOTES = "clear_notes"
    # Docker
    DOCKER_LIST = "docker_list"
    DOCKER_RESTART = "docker_restart"
    DOCKER_STATUS = "docker_status"
    DOCKER_LOGS = "docker_logs"
    # Home Assistant
    HA_TURN_ON = "ha_turn_on"
    HA_TURN_OFF = "ha_turn_off"
    HA_SET_TEMPERATURE = "ha_set_temperature"
    HA_GET_STATE = "ha_get_state"
    HA_LIST_DEVICES = "ha_list_devices"


class TTSProvider(str, Enum):
    """TTS provider options."""
    PIPER = "piper"
    KOKORO = "kokoro"
    CHATTERBOX = "chatterbox"


class ResponseStyle(str, Enum):
    """LLM response style options."""
    CONCISE = "concise"
    CONVERSATIONAL = "conversational"


class ActivationMode(str, Enum):
    """Voice activation modes."""
    PUSH_TO_TALK = "push-to-talk"
    VAD = "vad"
    WAKE_WORD = "wake-word"
