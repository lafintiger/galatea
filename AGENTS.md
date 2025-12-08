# Galatea - AI Agent Onboarding Guide

> This document is for AI agents continuing development on this project. Read this first to understand the codebase, architecture, and roadmap.

## 🎯 Project Overview

**Galatea** is a local voice AI companion - think Alexa/Siri but running entirely on the user's hardware with no cloud dependencies. Named after the Greek myth of Pygmalion and Galatea.

### Core Value Proposition
- **100% Local**: All processing happens on user's machine (privacy-focused)
- **Real-time Voice Chat**: Seamless conversation with low latency
- **Customizable**: User can choose LLM models, voices, and personality
- **Extensible**: Architecture designed for future integrations (vision, tools, memory)

### Current Status: Phase 3 ✅
- Voice input (STT) via Faster-Whisper
- LLM chat via Ollama
- Voice output (TTS) via **Piper** (fast) or **Kokoro** (HD quality)
- Sentence-level streaming for low latency
- Push-to-talk and Open Mic (VAD) modes
- Settings persistence
- **Time Awareness** - Gala knows time of day, weekends, holidays
- **Keyboard Shortcuts** - Spacebar for PTT, Escape to interrupt
- **Clean Interruption** - Instantly stops audio, clears queue
- **Export Conversations** - Save as Markdown, Text, or JSON
- **Enhanced Status Bar** - Shows model info, TTS provider, retry button
- **Conversation History** - Save/load past conversations with rename/delete
- **Web Search** - Search via SearXNG or Perplexica, natural language triggers
- **RAG System** - Background embedding with LanceDB + Ollama (Qwen3-Embedding-8B)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  React + TypeScript + Vite + Tailwind CSS                       │
│  Port: 5173 (dev)                                               │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ VoiceInterface │ │  Settings   │  │  useWebSocket (hook)    │ │
│  │ (mic, visual) │ │  (config)   │  │  (real-time comms)      │ │
│  └──────┬───────┘  └─────────────┘  └───────────┬─────────────┘ │
│         │                                        │               │
│         └────────────── WebSocket ───────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│  FastAPI + Python + WebSockets                                  │
│  Port: 8000                                                     │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ main.py     │  │ ollama.py   │  │  wyoming.py             │ │
│  │ (WS handler)│  │ (LLM client)│  │  (STT/TTS clients)      │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌─────────────────────────┐ │
│  │web_search.py│  │conversation │  │  RAG Services           │ │
│  │(SearXNG/    │  │_history.py  │  │  embedding.py (LanceDB) │ │
│  │ Perplexica) │  │(save/load)  │  │  model_manager.py       │ │
│  └──────┬──────┘  └─────────────┘  │  background_worker.py   │ │
│         │                          └───────────┬─────────────┘ │
└─────────┼──────────────────────────────────────┼───────────────┘
          │                                       │
          ▼                                       ▼
    ┌──────────┐    ┌──────────┐    ┌──────────────────────────┐
    │  Ollama  │    │ SearXNG  │    │   Wyoming Whisper (STT)  │
    │  (LLM)   │    │ (search) │    │   Docker: :10300         │
    │ :11434   │    │ :4000    │    └──────────────────────────┘
    └──────────┘    └──────────┘    ┌──────────────────────────┐
                    ┌──────────┐    │   Wyoming Piper (TTS)    │
                    │Perplexica│    │   Docker: :10200         │
                    │(AI srch) │    └──────────────────────────┘
                    │ :3000    │    ┌──────────────────────────┐
                    └──────────┘    │   Kokoro (HD TTS)        │
                                    │   Docker: :8880          │
                                    └──────────────────────────┘
```

### Docker Services Required
```bash
# Whisper (STT) - Wyoming protocol
docker run -d --name wyoming-whisper \
  -p 10300:10300 \
  rhasspy/wyoming-whisper --model small --language en

# Piper (TTS) - Wyoming protocol (Fast, CPU-friendly)
docker run -d --name piper \
  -p 10200:10200 \
  -v /path/to/voices:/config \
  lscr.io/linuxserver/piper

# Kokoro (TTS) - OpenAI-compatible API (HD quality)
docker run -d --name kokoro-tts \
  -p 8880:8880 \
  ghcr.io/remsky/kokoro-fastapi-cpu:latest

# SearXNG (Web Search) - Meta-search engine
docker run -d --name searxng \
  -p 4000:8080 \
  -v ./searxng:/etc/searxng \
  searxng/searxng

# Perplexica (AI Search) - Optional, AI-powered search with summaries
# See https://github.com/ItzCrazyKns/Perplexica for setup
```

**TTS Options:**
- **Piper**: Fast, lightweight, good for CPU. Wyoming protocol.
- **Kokoro**: Higher quality, more natural. OpenAI-compatible API. User can switch in Settings.

**Web Search Options:**
- **SearXNG**: Privacy-focused meta-search. Fast, aggregates from multiple engines.
- **Perplexica**: AI-powered search with built-in summaries. Uses Ollama for AI.

---

## 📁 Codebase Structure

```
galatea/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, WebSocket handler, core logic
│   │   ├── config.py            # Pydantic settings (hosts, ports, defaults)
│   │   ├── services/
│   │   │   ├── ollama.py        # Ollama LLM client with streaming + time awareness
│   │   │   ├── wyoming.py       # Wyoming protocol clients (Whisper/Piper)
│   │   │   ├── kokoro.py        # Kokoro TTS client (OpenAI-compatible API)
│   │   │   ├── web_search.py    # SearXNG/Perplexica search integration
│   │   │   ├── conversation_history.py  # Save/load conversations
│   │   │   ├── settings_manager.py  # User settings persistence
│   │   │   ├── embedding.py     # LanceDB vector embeddings via Ollama
│   │   │   ├── model_manager.py # Ollama model load/unload for VRAM
│   │   │   └── background_worker.py  # Background embedding processor
│   │   └── models/
│   │       └── schemas.py       # Pydantic models (UserSettings, etc.)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app layout
│   │   ├── components/
│   │   │   ├── VoiceInterface.tsx   # Mic button, status, visualizer, search
│   │   │   ├── Settings.tsx         # Settings panel
│   │   │   ├── AudioVisualizer.tsx  # Canvas-based audio viz
│   │   │   ├── Transcript.tsx       # Conversation display + export
│   │   │   ├── StatusBar.tsx        # Connection status
│   │   │   └── HistoryPanel.tsx     # Conversation history sidebar
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts      # WebSocket + audio queue
│   │   │   └── useAudioRecorder.ts  # Mic recording + VAD
│   │   ├── stores/
│   │   │   ├── settingsStore.ts     # Zustand store for settings
│   │   │   └── conversationStore.ts # Zustand store for chat state
│   │   └── styles/
│   │       └── index.css            # Tailwind + custom cyber theme
│   ├── package.json
│   └── vite.config.ts           # Proxy config for dev
│
├── scripts/
│   └── download_voices.py       # Script to download Piper voices
│
├── PRD.md                       # Product requirements document
├── README.md                    # Setup instructions
└── AGENTS.md                    # This file
```

---

## 🔑 Key Implementation Details

### 1. WebSocket Message Flow

**Frontend → Backend:**
```json
{"type": "audio_data", "audio": "<base64 wav>"}
{"type": "text_message", "content": "Hello Gala"}
{"type": "web_search", "query": "RTX 5090 specs", "provider": "auto"}
{"type": "interrupt"}
{"type": "settings_update", "settings": {...}}
{"type": "clear_history"}
```

**Backend → Frontend:**
```json
{"type": "status", "state": "idle|processing|thinking|speaking|searching"}
{"type": "transcription", "text": "...", "final": true}
{"type": "llm_chunk", "text": "..."}
{"type": "llm_complete", "text": "..."}
{"type": "audio_chunk", "audio": "<base64 wav>", "sentence": "..."}
{"type": "search_start", "query": "..."}
{"type": "search_results", "data": {...}}
{"type": "error", "message": "..."}
```

### 2. Sentence-Level TTS Streaming

To reduce latency, we don't wait for the full LLM response. Instead:
1. Buffer LLM chunks
2. When a sentence boundary is detected (`. ! ?`), send that sentence to Piper
3. Stream audio chunks to frontend immediately
4. Frontend queues and plays audio sequentially

See `generate_response()` in `backend/app/main.py`.

### 3. Voice Activity Detection (VAD)

In `useAudioRecorder.ts`:
- `startVAD()` - Starts continuous mic listening
- Detects speech start when audio level > `VAD_SPEECH_THRESHOLD`
- Detects speech end after `VAD_SILENCE_DURATION` ms of silence
- Automatically converts and sends audio when speech ends

### 4. Text Cleaning for TTS

The `clean_for_speech()` function in `main.py` removes:
- Emojis and Unicode symbols
- Action markers: `*smiles*`, `(laughs)`, `[nods]`
- `<think>` blocks from thinking models
- Markdown formatting

### 5. Thinking Model Handling

For models like Qwen3 that have chain-of-thought:
- System prompt includes `/no_think` instruction
- User messages get `/no_think` appended
- `<think>` blocks are filtered from stream before display

### 6. Time Awareness

The `get_time_context()` function in `ollama.py` provides:
- Time of day (morning/afternoon/evening/night)
- Day of week (weekday vs weekend)
- Holiday detection (major US holidays)
- Greeting suggestions for the LLM

### 7. Interruption System

When user presses Escape or clicks stop:
1. Frontend: `stopAllAudio()` immediately stops playback
2. Frontend: Clears audio queue (`audioQueueRef.current = []`)
3. Backend: Sets `should_interrupt = True` 
4. Backend: Stops TTS generation for remaining sentences
5. Both: Reset to idle state

### 8. Keyboard Shortcuts

| Key | Action | Condition |
|-----|--------|-----------|
| **Spacebar** (hold) | Push-to-talk record | In PTT mode, idle state |
| **Spacebar** (release) | Stop recording & send | Recording active |
| **Escape** | Interrupt Gala | Speaking/processing |

Shortcuts are disabled when typing in text input.

### 9. Web Search Integration

Gala can search the web using SearXNG or Perplexica. Search can be triggered:

**Via Voice/Text (Natural Language):**
```
"Search for RTX 5090 specs"
"Look up the weather in Paris"
"Find out about quantum computing"
"Google best pizza in NYC"
"What is the latest AI news?"
```

**Via Search Button:**
- Click the 🔍 button next to the text input
- Enter query in the popup dialog
- Results are summarized by Gala

**Architecture:**
```
User says "search for X" → detect_search_intent() → web_search.py
                                                         ↓
                              ┌─────────────────────────────────────┐
                              │  SearXNG (port 4000)                │
                              │  - Fast meta-search                 │
                              │  - Aggregates Google/Bing/DDG       │
                              ├─────────────────────────────────────┤
                              │  Perplexica (port 3000) - Optional  │
                              │  - AI-powered search                │
                              │  - Built-in summaries via Ollama    │
                              └─────────────────────────────────────┘
                                                         ↓
                              Results formatted → LLM summarizes → TTS speaks
```

**Search Trigger Phrases:**
| Pattern | Example |
|---------|---------|
| `search for...` | "Search for electric cars" |
| `look up...` | "Look up Python tutorials" |
| `find out about...` | "Find out about quantum computing" |
| `google...` | "Google best restaurants" |
| `check the...` | "Check the weather" |

**Auto-Search Topics** (always triggers search):
| Topic | Examples |
|-------|----------|
| **Weather** | "What's the weather?", "Will it rain tomorrow?", "Check the forecast" |
| **News** | "What's happening in tech?", "Latest news on AI", "Recent developments" |
| **Prices** | "How much does iPhone cost?", "Bitcoin price", "Stock price of Apple" |
| **Sports** | "Who won the game?", "NBA standings", "Match score" |
| **Schedules** | "When does the store open?", "Release date of...", "Hours of..." |
| **Products** | "RTX 5090 specs", "Best laptop for gaming", "iPhone 16 reviews" |
| **Movies** | "What movies are playing?", "Show times tonight" |
| **Location** | "Restaurants nearby", "Directions to...", "Phone number for..." |

**System Prompt Integration**: Gala's system prompt instructs her to search when she doesn't know something. She'll say "Let me look that up" and the system will automatically perform the search.

### 10. Conversation History

Save and load past conversations via the History panel (🕐 button in header).

**Features:**
- **Save Current** - Saves current conversation with auto-generated title
- **New** - Clears current conversation and starts fresh
- **Load** - Click any saved conversation to restore it
- **Rename** - Click edit icon to rename a conversation
- **Delete** - Click trash icon to remove a conversation

**Storage:** Conversations saved as JSON in `backend/data/conversations/`

**API Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/conversations` | List all saved conversations |
| GET | `/api/conversations/{id}` | Get specific conversation |
| POST | `/api/conversations` | Save new/update existing |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| PATCH | `/api/conversations/{id}` | Rename conversation |

### 11. RAG System (Background Embeddings)

Gala uses LanceDB + Ollama embeddings for semantic memory. Embeddings are processed **in the background** to avoid interrupting conversation flow.

**Architecture:**
```
User saves conversation → JSON stored immediately
                            ↓
                       Added to embedding queue
                            ↓
                       (User is idle for 5 minutes)
                            ↓
        ┌─────────────────────────────────────┐
        │  Background Worker                  │
        │  1. Unload chat model (free VRAM)   │
        │  2. Load embedding model (5.4GB)    │
        │  3. Embed all pending conversations │
        │  4. Store vectors in LanceDB        │
        │  5. Unload embedding model          │
        │  6. Reload chat model               │
        └─────────────────────────────────────┘
                            ↓
        User asks question → RAG retrieves similar context
                            ↓
        Context injected into system prompt → Better answers!
```

**Components:**

| File | Purpose |
|------|---------|
| `embedding.py` | LanceDB storage + Ollama embedding API calls |
| `model_manager.py` | Load/unload Ollama models for VRAM management |
| `background_worker.py` | Idle detection + batch processing |

**Configuration:**
- **Embedding Model**: `ZimaBlueAI/Qwen3-Embedding-8B:Q5_K_M` (5.4GB, high quality)
- **Idle Timeout**: 5 minutes of no activity before processing
- **Vector Dimensions**: 4096 (Qwen3-Embedding output)

**API Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rag/status` | Worker status, pending count, embedding stats |
| POST | `/api/rag/process` | Manually trigger embedding (bypass idle wait) |
| GET | `/api/rag/search?query=...` | Search the knowledge base directly |

**SanctumWriter Compatibility:**
This RAG implementation uses the same stack as SanctumWriter:
- **LanceDB** for vector storage
- **Ollama embeddings** API
- Same embedding model options

Future integration will allow shared memory between Gala and SanctumWriter.

---

## 🎨 UI/UX Decisions

- **Futuristic Cyberpunk Theme**: Cyan accents, dark backgrounds, glow effects
- **Minimal Text**: Voice-first interface, transcript is optional
- **Visual Feedback**: 
  - Audio visualizer shows mic levels
  - Color-coded states (green=listening, yellow=recording, cyan=speaking)
  - Pulse animations for active states
  - Emoji status indicators (● 🎙️ 🧠 🗣️)

### Status Bar Features
- Connection status with retry button on error
- Model name + size (e.g., "qwen3-abliterated (5.0GB)")
- Voice name + TTS provider badge (Fast/HD)
- Dismissible error messages

### Transcript Features
- Auto-scrolling conversation view
- Export dropdown (Markdown, Text, JSON)
- Clear conversation button
- User/Assistant message styling with timestamps

---

## 🛠️ Development Workflow

### Start Services
```bash
# Terminal 1: Backend
cd backend
.\venv\Scripts\activate  # Windows
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Required Docker containers must be running
docker start wyoming-whisper piper
```

### Key Files to Edit

| Feature | Files |
|---------|-------|
| LLM behavior | `backend/app/services/ollama.py` (system prompt) |
| Voice settings | `backend/app/models/schemas.py` (UserSettings) |
| WebSocket logic | `backend/app/main.py` |
| Web search | `backend/app/services/web_search.py` |
| Conversation history | `backend/app/services/conversation_history.py` |
| UI components | `frontend/src/components/*.tsx` |
| State management | `frontend/src/stores/*.ts` |
| Audio handling | `frontend/src/hooks/useAudioRecorder.ts` |
| Search config | `backend/app/config.py` (searxng/perplexica hosts)

---

## 🗺️ Roadmap

### ✅ Completed (December 2024)

| Feature | Description |
|---------|-------------|
| **Kokoro TTS** | High-quality TTS option alongside Piper |
| **Time Awareness** | Gala knows time of day, day of week, holidays, weekends |
| **Better Interruption** | Escape key stops audio instantly, clears queue |
| **Keyboard Shortcuts** | Spacebar for push-to-talk, Escape to interrupt |
| **Export Conversation** | Download as Markdown, Plain Text, or JSON |
| **Clear Conversation** | Trash button in transcript |
| **Better Status Indicators** | Emoji icons for each state (🎙️🧠🗣️🔍) |
| **Enhanced Status Bar** | Model size, TTS provider badge, retry button |
| **Conversation History** | Save/load past conversations with rename/delete |
| **Web Search** | SearXNG + Perplexica integration with natural language triggers |
| **RAG System** | LanceDB + Ollama embeddings with background processing |

### 📋 Phase 4: Future Features

| Feature | Description | Complexity |
|---------|-------------|------------|
| **Multiple Personas** | Switch between Gala "personalities" | Medium |
| **Vision** | Describe images/screenshots | High |
| **Tool Calling** | File ops, code execution, smart home | High |
| **Multi-language** | Support other languages for voice | Medium |
| **Emotion Detection** | Analyze user sentiment | High |

**Not Planned** (per user preference):
- Wake Word ("Hey Gala") - Privacy concern, user prefers manual activation

---

## ⚠️ Known Issues & Gotchas

1. **Thinking Models**: Qwen3 and similar need `/no_think` - already handled
2. **Microphone Permissions**: Browser must grant access, show clear error
3. **Wyoming Protocol**: Use official `wyoming` package, not custom implementation
4. **Piper Voice Location**: LinuxServer Piper container uses `/config/` not `/data/`
5. **Audio Playback**: Must handle browser autoplay policies (AudioContext resume)

---

## 💡 Tips for Agents

1. **Read the PRD.md** for full feature requirements
2. **Check schemas.py** before adding new settings
3. **Test with Open Mic mode** - it's more complex than push-to-talk
4. **Backend auto-reloads** with `--reload` flag
5. **Frontend HMR** - but sometimes needs full refresh
6. **User has 5090 GPU** with 24GB VRAM - can run large models

---

## 📞 User Preferences

- **Name**: User prefers "Gala" as nickname for the assistant
- **Voice**: Prefers Kokoro TTS (HD quality) - `af_heart` voice
- **Model**: Using Qwen3 abliterated (needs thinking disabled for speed)
- **Style**: Prefers conversational, natural responses
- **Clean Speech**: No emojis, no action markers, no thinking aloud
- **Privacy**: No always-on listening, no wake word - user controls when mic is active
- **Hardware**: RTX 5090 (24GB VRAM), powerful CPU with NPU

---

## 🔗 Related Projects

- **SanctumWriter** (`local-doc-editor/`): Local AI writing app
  - Uses same LanceDB + Ollama embeddings for RAG
  - Future integration planned: shared memory between Gala and SanctumWriter

---

*Last updated: December 8, 2024*
*Phase: 2 (Conversation History + Web Search)*
*Repository: https://github.com/lafintiger/galatea*



