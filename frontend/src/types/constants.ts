/**
 * Constants for WebSocket message types - must match backend constants.py
 */

// Client -> Server message types
export const MessageType = {
  AUDIO_DATA: 'audio_data',
  TEXT_MESSAGE: 'text_message',
  SPEAK_TEXT: 'speak_text',
  INTERRUPT: 'interrupt',
  SETTINGS_UPDATE: 'settings_update',
  CLEAR_HISTORY: 'clear_history',
  OPEN_EYES: 'open_eyes',
  CLOSE_EYES: 'close_eyes',
  GET_VISION_STATUS: 'get_vision_status',
  WORKSPACE_RESULT: 'workspace_result',
  WEB_SEARCH: 'web_search',
} as const

export type MessageTypeValue = (typeof MessageType)[keyof typeof MessageType]

// Server -> Client response types
export const ResponseType = {
  STATUS: 'status',
  ERROR: 'error',
  INTERRUPTED: 'interrupted',
  SETTINGS_UPDATED: 'settings_updated',
  HISTORY_CLEARED: 'history_cleared',
  TRANSCRIPTION: 'transcription',
  LLM_CHUNK: 'llm_chunk',
  LLM_COMPLETE: 'llm_complete',
  AUDIO_CHUNK: 'audio_chunk',
  VISION_STATUS: 'vision_status',
  VISION_UPDATE: 'vision_update',
  SEARCH_START: 'search_start',
  SEARCH_RESULTS: 'search_results',
  WORKSPACE_COMMAND: 'workspace_command',
  DOMAIN_SWITCH: 'domain_switch',
} as const

export type ResponseTypeValue = (typeof ResponseType)[keyof typeof ResponseType]

// Application status states
export const Status = {
  IDLE: 'idle',
  LISTENING: 'listening',
  PROCESSING: 'processing',
  THINKING: 'thinking',
  SPEAKING: 'speaking',
  SEARCHING: 'searching',
} as const

export type StatusValue = (typeof Status)[keyof typeof Status]

// Workspace actions
export const WorkspaceAction = {
  ADD_TODO: 'add_todo',
  ADD_NOTE: 'add_note',
  COMPLETE_TODO: 'complete_todo',
  LOG_DATA: 'log_data',
  OPEN_WORKSPACE: 'open_workspace',
  READ_TODOS: 'read_todos',
  READ_NOTES: 'read_notes',
  CLEAR_TODOS: 'clear_todos',
  CLEAR_NOTES: 'clear_notes',
} as const

export type WorkspaceActionValue = (typeof WorkspaceAction)[keyof typeof WorkspaceAction]
