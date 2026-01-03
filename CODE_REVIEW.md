# Galatea Code Review - January 2026

## ✅ REFACTORING COMPLETE - January 3, 2026

The recommendations in this review have been **implemented**. Key changes:

| Component | Before | After | Improvement |
|-----------|--------|-------|-------------|
| `websocket.py` | 1,258 lines | 127 lines | **90% reduction** |
| Handler modules | N/A | 6 files, 1,481 lines | Separated concerns |
| Constants | Magic strings | `constants.py` | Type-safe enums |
| Frontend schemas | Out of sync | Synced | Full parity |

See [Refactoring Summary](#-refactoring-completed) below.

---

## Executive Summary

**Overall Assessment: A- (Solid foundation, ready for scaling)**

Galatea has evolved from a simple voice assistant to a sophisticated multi-modal AI companion. The December 2024 refactoring significantly improved maintainability (main.py went from 2,357 lines to 90). However, as we add more features, architectural patterns need tightening to prevent the codebase from becoming unwieldy.

---

## 📊 Metrics Overview

| Component | Lines | Complexity | Notes |
|-----------|-------|------------|-------|
| `websocket.py` | 1,258 | **HIGH** | Largest file, needs splitting |
| `api.py` | 811 | Medium | Well-organized REST endpoints |
| `command_router.py` | 686 | Medium | Tool definitions + routing logic mixed |
| `vision_live.py` | 504 | Medium | Good separation |
| `user_profile.py` | 491 | Low | Data-heavy, well-structured |
| **Backend Total** | ~6,500 | - | Reasonable for feature set |
| **Frontend Total** | ~3,800 | - | Manageable |

---

## ✅ What's Working Well

### 1. Clean Entry Point
```python
# main.py is exemplary - 90 lines, clear responsibilities
app = FastAPI(title="Galatea", lifespan=lifespan)
app.include_router(api_router)
app.include_router(websocket_router)
```

### 2. Centralized Configuration
- `config.py` uses Pydantic Settings (type-safe, env-aware)
- All service URLs in one place
- Easy to override via `.env`

### 3. Service Isolation
- Each external service has its own module (`ollama.py`, `kokoro.py`, `wyoming.py`)
- Clean async interfaces
- Good error handling at service boundaries

### 4. Unified Logging
- `get_logger(__name__)` pattern established
- Centralized in `core/logging.py`
- Custom exceptions in `core/exceptions.py`

### 5. Frontend State Management
- Zustand stores are clean and focused
- `settingsStore.ts`, `conversationStore.ts`, `workspaceStore.ts`
- Atomic `updateSettings()` for batch updates

---

## ⚠️ Areas of Concern

### 1. **websocket.py is a God Object** (Critical)

At 1,258 lines with 11 handler functions, this file does too much:

```
websocket_endpoint()      # Main loop
handle_voice_input()      # STT + routing + response
handle_text_input()       # Text + routing + response  
handle_web_search()       # Search orchestration
handle_workspace_command() # Todo/notes management
handle_workspace_result()  # Workspace response
handle_vision_command()    # Open/close eyes
handle_describe_view()     # Vision analysis
handle_mcp_command()      # Docker + Home Assistant
speak_response()          # TTS orchestration
generate_response()       # LLM streaming + TTS
```

**Problem:** Adding new capabilities means adding more handlers here.
**Impact:** Hard to test, hard to understand, merge conflicts.

### 2. **Inconsistent Error Handling**

```python
# Pattern A: Swallow and continue
except Exception as e:
    logger.warning(f"Non-fatal error: {e}")
    return None

# Pattern B: Re-raise with context
except httpx.HTTPStatusError as e:
    raise ServiceUnavailableError("Ollama", str(e))

# Pattern C: Send error to client
except Exception as e:
    await websocket.send_json({"type": "error", "message": str(e)})
```

**Problem:** No consistent strategy for error recovery.

### 3. **Frontend/Backend Schema Drift**

```python
# Backend: schemas.py
class UserSettings(BaseModel):
    user_location: str = ""  # Added
    vision_enabled: bool = False
    domain_routing_enabled: bool = True
```

```typescript
// Frontend: settingsStore.ts
interface UserSettings {
  // Missing: user_location, vision_enabled, domain_routing_enabled
}
```

**Problem:** TypeScript interface doesn't match Python schema.

### 4. **No Dependency Injection**

Services are imported as module-level singletons:
```python
from ..services.ollama import ollama_service
from ..services.vision import vision_service
```

**Problem:** Can't mock services for testing, can't swap implementations.

### 5. **Missing Tests**

- Only 2 test files found (`test_full_flow.py`, `test_router.py`)
- No unit tests for services
- No integration tests
- No frontend tests

### 6. **Magic Strings Everywhere**

```python
msg_type == "audio_data"
msg_type == "text_message"
msg_type == "open_eyes"
{"type": "llm_complete", "text": ...}
{"type": "status", "state": "idle"}
```

**Problem:** No enum/constants, easy to typo, hard to refactor.

---

## 🔧 Recommended Refactors

### Priority 1: Split websocket.py (High Impact)

Create a handler registry pattern:

```python
# handlers/__init__.py
from .voice import VoiceHandler
from .vision import VisionHandler
from .workspace import WorkspaceHandler
from .search import SearchHandler

HANDLERS = {
    "audio_data": VoiceHandler(),
    "text_message": VoiceHandler(),
    "open_eyes": VisionHandler(),
    "close_eyes": VisionHandler(),
    "describe_view": VisionHandler(),
    "web_search": SearchHandler(),
    # ...
}

# websocket.py (simplified)
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    while True:
        data = await websocket.receive_json()
        handler = HANDLERS.get(data["type"])
        if handler:
            await handler.handle(websocket, state, data, settings)
```

**Files to create:**
```
routers/
├── websocket.py          # 150 lines (main loop only)
└── handlers/
    ├── __init__.py       # Handler registry
    ├── base.py           # BaseHandler class
    ├── voice.py          # Voice input/output
    ├── vision.py         # Vision commands
    ├── workspace.py      # Notes/todos
    ├── search.py         # Web search
    └── mcp.py            # Docker/HomeAssistant
```

### Priority 2: Message Type Constants

```python
# core/constants.py
class MessageType:
    AUDIO_DATA = "audio_data"
    TEXT_MESSAGE = "text_message"
    OPEN_EYES = "open_eyes"
    LLM_COMPLETE = "llm_complete"
    STATUS = "status"
    # ...

class Status:
    IDLE = "idle"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    THINKING = "thinking"
```

### Priority 3: Sync Frontend Schema

```typescript
// types/settings.ts (auto-generate from Python?)
interface UserSettings {
  assistant_name: string
  assistant_nickname: string
  selected_model: string
  selected_voice: string
  response_style: 'concise' | 'conversational'
  activation_mode: 'push-to-talk' | 'vad' | 'wake-word'
  wake_word?: string
  transcript_visible: boolean
  theme: string
  language: string
  tts_provider: 'piper' | 'kokoro'
  voice_speed: number
  voice_variation: number
  voice_phoneme_var: number
  // NEW - sync with backend
  user_location: string
  vision_enabled: boolean
  domain_routing_enabled: boolean
  specialist_models: SpecialistModels
}
```

### Priority 4: Dependency Injection (For Testing)

```python
# services/container.py
from dataclasses import dataclass

@dataclass
class ServiceContainer:
    ollama: OllamaService
    vision: VisionService
    tts: TTSService
    stt: STTService
    search: SearchService
    
# In handlers
class VisionHandler(BaseHandler):
    def __init__(self, services: ServiceContainer):
        self.vision = services.vision
        self.ollama = services.ollama
```

### Priority 5: Testing Strategy

```
tests/
├── unit/
│   ├── test_ollama_service.py
│   ├── test_vision_service.py
│   ├── test_command_router.py
│   └── test_audio_utils.py
├── integration/
│   ├── test_voice_flow.py
│   ├── test_vision_flow.py
│   └── test_search_flow.py
└── fixtures/
    ├── audio_samples/
    └── mock_responses.py
```

---

## 📋 Action Items

### Immediate (Before Next Feature)
- [ ] Create `core/constants.py` with message types
- [ ] Sync `settingsStore.ts` with `schemas.py`
- [ ] Add type hints to all function signatures

### Short Term (Next Sprint)
- [ ] Split `websocket.py` into handler modules
- [ ] Add unit tests for `command_router.py`
- [ ] Add unit tests for `vision.py`

### Medium Term (Next Month)
- [ ] Implement dependency injection
- [ ] Add integration tests for main flows
- [ ] Set up CI/CD with test gates

### Long Term (Architecture)
- [ ] Consider event-driven architecture for handlers
- [ ] Evaluate message queue for background tasks
- [ ] Consider TypeScript code generation from Python schemas

---

## 🏗️ Scalability Assessment

### Will Scale Well
- ✅ Service isolation (easy to add new services)
- ✅ Configuration management (env-based)
- ✅ LLM abstraction (Ollama can switch models easily)
- ✅ Frontend state management (Zustand is lightweight)

### Won't Scale Well Without Changes
- ❌ Single WebSocket handler (needs splitting)
- ❌ No message queue (background tasks are hacky)
- ❌ No caching layer (repeated LLM calls)
- ❌ Schema drift (manual sync between FE/BE)

### Feature Addition Difficulty (Current State)
| Feature Type | Difficulty | Why |
|--------------|------------|-----|
| New MCP tool | Easy | Add to command_router + handler |
| New TTS provider | Easy | Add new service file |
| New vision capability | Medium | Modify vision.py + handler |
| New conversation mode | Hard | Touches multiple handlers |
| Multi-user support | Very Hard | No user/session abstraction |

---

## 💡 Recommendation

**Before adding new features:**

1. **Split websocket.py** (2-3 hours of work, high ROI)
2. **Add constants file** (30 minutes)
3. **Sync schemas** (1 hour)

This investment will:
- Make the codebase easier to understand
- Reduce merge conflicts when adding features
- Enable testing of individual components
- Prepare for larger architectural changes

**The house is built on good soil, but needs some interior walls.**

---

---

## ✅ Refactoring Completed

### Handler Architecture (January 3, 2026)

The monolithic `websocket.py` has been split into focused handler modules:

```
backend/app/
├── handlers/
│   ├── __init__.py      # Handler registry
│   ├── base.py          # BaseHandler, HandlerContext
│   ├── voice.py         # Audio/text input, LLM, TTS
│   ├── vision.py        # Open/close eyes, describe
│   ├── workspace.py     # Notes, todos, data
│   ├── search.py        # Web search
│   └── mcp.py           # Docker, Home Assistant
└── core/
    └── constants.py     # Message types, status enums
```

### websocket.py - Before vs After

**Before (1,258 lines):**
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # ... 1,200+ lines of handlers mixed together
```

**After (127 lines):**
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Clean routing to handlers
    if msg_type in [MessageType.AUDIO_DATA, MessageType.TEXT_MESSAGE]:
        await voice_handler.safe_handle(ctx)
    elif msg_type in [MessageType.OPEN_EYES, MessageType.CLOSE_EYES]:
        await vision_handler.safe_handle(ctx)
    # ... clean, readable routing
```

### Adding New Features Now

To add a new capability (e.g., calendar integration):

1. **Create handler:** `handlers/calendar.py`
2. **Add constants:** Update `constants.py` with new message types
3. **Register:** Add to `handlers/__init__.py`
4. **Route:** Add routing in `websocket.py` (2-3 lines)

No more modifying a 1,000+ line file!

### Frontend Schema Sync

`settingsStore.ts` now includes all backend fields:
- `user_location`
- `vision_enabled`
- `domain_routing_enabled`
- `specialist_models`

### Constants (Type Safety)

```python
# Before - easy to typo
msg_type == "audio_data"

# After - IDE autocomplete, compile-time checks
msg_type == MessageType.AUDIO_DATA
```

---

*Review completed: January 3, 2026*
*Refactoring completed: January 3, 2026*
*Reviewer: AI Agent (Claude)*
*Next review recommended: After adding 2-3 more features*
