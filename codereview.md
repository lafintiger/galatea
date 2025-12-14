# Galatea Code Review: Comprehensive Assessment

**Reviewer:** AI Code Review  
**Date:** December 13, 2024  
**Codebase Version:** Phase 5

---

## Executive Summary

| Category | Rating | Notes |
|----------|--------|-------|
| **Code Quality** | ⭐⭐⭐⭐ (4/5) | Well-written, clean Python/TypeScript |
| **Consistency** | ⭐⭐⭐ (3/5) | Some patterns vary, error handling inconsistent |
| **Modularity** | ⭐⭐⭐ (3/5) | Good service separation, but tight coupling to specific providers |
| **Documentation** | ⭐⭐⭐⭐⭐ (5/5) | Excellent AGENTS.md, clear architecture |
| **Maintainability** | ⭐⭐⭐ (3/5) | main.py is too large, hard to swap providers |

---

## Strengths

### 1. Excellent Documentation

The `AGENTS.md` is one of the best onboarding docs I've seen. Architecture diagrams, WebSocket message flows, API endpoints, gotchas - all documented.

### 2. Good Service Separation

Each concern has its own service file with clear responsibilities:

```
services/
├── ollama.py          # LLM
├── wyoming.py         # STT (Whisper) / TTS (Piper)
├── kokoro.py          # TTS (alternative)
├── vision.py          # Static image analysis
├── vision_live.py     # Real-time face recognition
├── domain_router.py   # Specialist model routing
├── command_router.py  # Intent detection
├── web_search.py      # SearXNG/Perplexica
├── embedding.py       # LanceDB RAG
├── model_manager.py   # VRAM management
├── background_worker.py # Async embedding
├── user_profile.py    # Onboarding
├── conversation_history.py # Save/load
└── settings_manager.py # Persistence
```

### 3. Consistent Singleton Pattern

All services use the same pattern:

```python
class SomeService:
    def __init__(self):
        # ...
        
# Singleton instance
some_service = SomeService()
```

### 4. Type Hints Throughout

Both Python and TypeScript use proper typing:

```python
async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
```

```typescript
export interface UserSettings {
  assistant_name: string
  selected_model: string
  // ...
}
```

### 5. Clean State Management (Frontend)

Zustand stores are well-organized with clear interfaces.

---

## Areas of Concern

### 1. main.py is a God Object (2,357 lines!)

This single file handles:
- FastAPI app setup
- REST endpoints (~500 lines)
- WebSocket handler (~400 lines)
- Intent detection functions (~400 lines)
- Response generation (~400 lines)
- Command handlers (~200 lines)
- Text cleaning for TTS

**Recommendation:** Split into:

```
backend/app/
├── main.py              # App setup only (~100 lines)
├── routers/
│   ├── api.py           # REST endpoints
│   ├── websocket.py     # WebSocket handler
│   └── __init__.py
├── core/
│   ├── intent.py        # Intent detection
│   ├── response.py      # LLM + TTS orchestration
│   └── audio.py         # Audio processing
```

### 2. Tight Coupling to Ollama - NOT Modular for LLM Swapping

Currently, Ollama is directly imported and used in multiple places:

**Files that directly call Ollama:**
- `main.py` - Chat generation, model warmup
- `services/ollama.py` - Core LLM service
- `services/command_router.py` - Function calling
- `services/vision.py` - Vision model inference
- `services/embedding.py` - Embedding generation
- `services/model_manager.py` - Model loading/unloading
- `services/domain_router.py` - Specialist model config

**Impact of switching to LMStudio or vLLM:**

| File | Lines to Change | Complexity |
|------|-----------------|------------|
| `config.py` | ~10 | Low |
| `services/ollama.py` | ~200 | High |
| `services/command_router.py` | ~50 | Medium |
| `services/vision.py` | ~50 | Medium |
| `services/embedding.py` | ~30 | Medium |
| `services/model_manager.py` | ~100 | High |
| `services/domain_router.py` | ~20 | Low |
| `main.py` | ~50 | Medium |

**Total: ~500+ lines across 8 files**

### 3. TTS Abstraction is Incomplete

The `synthesize_tts()` function in main.py does abstract TTS choice:

```python
async def synthesize_tts(text, voice, provider="piper", ...):
    if provider == "kokoro":
        return await kokoro_service.synthesize(...)
    else:
        return await piper_service.synthesize(...)
```

But it's a function, not a proper interface. Adding a third TTS means modifying this function.

### 4. Duplicate Intent Detection Logic

Two systems doing intent detection:

1. **Regex-based** in `detect_workspace_command()`, `detect_search_intent()`, `detect_vision_command()` (~500 lines of regex patterns)

2. **LLM-based** in `command_router.py` using Ministral for function calling

The code tries LLM first, then falls back to regex. This is redundant and adds latency.

### 5. Inconsistent Error Handling

```python
# Pattern 1: Return error dicts
return {"success": False, "error": str(e)}

# Pattern 2: Raise exceptions
raise Exception(f"Kokoro TTS HTTP error: {e.response.status_code}")

# Pattern 3: Print and continue
print(f"Warning: Could not get Piper voices: {e}")
result["piper"] = []
```

**Recommendation:** Standardize on:
- Return error dicts for expected failures (user errors, missing resources)
- Raise exceptions for unexpected failures (network errors, bugs)
- Use proper logging instead of print()

### 6. Settings Access Inconsistency

```python
# Defensive getattr (suggests schema uncertainty)
provider=getattr(user_settings, 'tts_provider', 'piper'),
speed=getattr(user_settings, 'voice_speed', 1.0)

# Direct access (assumes schema is correct)
voice=user_settings.selected_voice,
model=user_settings.selected_model,
```

If the Pydantic schema is correct, `getattr` with defaults shouldn't be needed.

### 7. Print Statements Instead of Logging

```python
print(f"[WS] Client connected")
print(f"[Vision] Gala's eyes opened")
print(f"[CommandRouter] Routing: '{user_input}'")
```

**Recommendation:** Use Python logging with proper levels and structured data.

---

## Recommended Provider Abstraction

### Abstract Base Classes

```python
# services/providers/base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

class LLMProvider(ABC):
    """Abstract base for LLM providers (Ollama, LMStudio, vLLM, etc.)"""
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        model: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict]] = None
    ) -> dict:
        """Non-streaming chat (for function calling)"""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        images: Optional[list[str]] = None
    ) -> str:
        """Single-shot generation (for vision, embeddings)"""
        pass
    
    @abstractmethod
    async def embed(self, text: str, model: str) -> list[float]:
        """Generate embeddings"""
        pass
    
    @abstractmethod
    async def list_models(self) -> list[dict]:
        """List available models"""
        pass
    
    @abstractmethod
    async def load_model(self, model: str) -> bool:
        """Pre-load model into memory"""
        pass
    
    @abstractmethod
    async def unload_model(self, model: str) -> bool:
        """Unload model from memory"""
        pass


class TTSProvider(ABC):
    """Abstract base for TTS providers"""
    
    @abstractmethod
    async def synthesize(self, text: str, voice: str, **kwargs) -> bytes:
        """Synthesize text to WAV audio"""
        pass
    
    @abstractmethod
    async def list_voices(self) -> list[dict]:
        """List available voices"""
        pass


class STTProvider(ABC):
    """Abstract base for STT providers"""
    
    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """Transcribe audio to text"""
        pass
```

### Provider Factory

```python
# services/providers/__init__.py
from .base import LLMProvider, TTSProvider, STTProvider
from .ollama import OllamaProvider
from .wyoming import WyomingSTTProvider, WyomingTTSProvider
from .kokoro import KokoroTTSProvider

def get_llm_provider(provider_type: str, **kwargs) -> LLMProvider:
    """Factory function to get LLM provider"""
    providers = {
        "ollama": OllamaProvider,
        # Future: "lmstudio": LMStudioProvider,
        # Future: "vllm": VLLMProvider,
    }
    if provider_type not in providers:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
    return providers[provider_type](**kwargs)

def get_tts_provider(provider_type: str, **kwargs) -> TTSProvider:
    """Factory function to get TTS provider"""
    providers = {
        "piper": WyomingTTSProvider,
        "kokoro": KokoroTTSProvider,
    }
    if provider_type not in providers:
        raise ValueError(f"Unknown TTS provider: {provider_type}")
    return providers[provider_type](**kwargs)

def get_stt_provider(provider_type: str, **kwargs) -> STTProvider:
    """Factory function to get STT provider"""
    providers = {
        "whisper": WyomingSTTProvider,
    }
    if provider_type not in providers:
        raise ValueError(f"Unknown STT provider: {provider_type}")
    return providers[provider_type](**kwargs)
```

---

## Refactoring Priority

### Phase 1: Quick Wins (1-2 hours)
1. Replace `print()` with proper logging
2. Standardize error handling
3. Remove `getattr` defensive coding

### Phase 2: Split main.py (4-6 hours)
1. Extract REST endpoints to `routers/api.py`
2. Extract WebSocket handler to `routers/websocket.py`
3. Extract intent detection to `core/intent.py`
4. Extract response generation to `core/response.py`

### Phase 3: Provider Abstraction (8-12 hours)
1. Create abstract `LLMProvider`, `TTSProvider`, `STTProvider` interfaces
2. Implement `OllamaProvider` using existing code
3. Create provider factory/registry
4. Update all services to use interfaces
5. Add config for provider selection

### Phase 4: Cleanup (2-4 hours)
1. Consolidate intent detection (choose regex OR LLM)
2. Move domain patterns to config files
3. Consider shared schema generation (Python → TypeScript)

---

## Performance Considerations

### Current Latency Sources

1. **Intent Detection** - Running both Ministral router AND regex patterns
2. **Model Loading** - Models loaded on-demand, not pre-warmed
3. **Sequential TTS** - Each sentence waits for previous to complete synthesis
4. **No Connection Pooling** - New HTTP connections for each request

### Potential Improvements

1. **Remove dual intent detection** - Use only LLM router OR regex, not both
2. **Keep models warm** - Background worker to ping models periodically
3. **Parallel TTS** - Generate next sentence while current is playing
4. **HTTP connection reuse** - Use httpx client pools
5. **WebSocket binary frames** - Send audio as binary, not base64

---

## Docker Architecture Recommendation

Current architecture has Ollama running natively. Consider containerizing for:
- Consistent environment across machines
- Easier deployment
- Better resource isolation
- Simpler configuration

```yaml
# docker-compose.yml additions
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

This would make the connection URL consistent (`http://ollama:11434`) and allow the backend to reference it by service name within the Docker network.

---

## Conclusion

The codebase is well-written for a rapidly-developed project. The main issues are:

1. **main.py is too large** - Split into focused modules
2. **LLM provider coupling** - Abstract to interfaces for flexibility
3. **Inconsistent patterns** - Standardize error handling and logging
4. **Dual intent detection** - Redundant complexity

With the recommended refactoring, the codebase would be:
- Easier to maintain
- Flexible for different LLM providers
- More performant (removing redundant operations)
- Better for debugging (proper logging)

