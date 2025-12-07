# Galatea - AI Agent Onboarding Guide

> This document is for AI agents continuing development on this project. Read this first to understand the codebase, architecture, and roadmap.

## 🎯 Project Overview

**Galatea** is a local voice AI companion - think Alexa/Siri but running entirely on the user's hardware with no cloud dependencies. Named after the Greek myth of Pygmalion and Galatea.

### Core Value Proposition
- **100% Local**: All processing happens on user's machine (privacy-focused)
- **Real-time Voice Chat**: Seamless conversation with low latency
- **Customizable**: User can choose LLM models, voices, and personality
- **Extensible**: Architecture designed for future integrations (vision, tools, memory)

### Current Status: Phase 1 Complete ✅
- Voice input (STT) via Faster-Whisper
- LLM chat via Ollama
- Voice output (TTS) via Piper
- Sentence-level streaming for low latency
- Push-to-talk and Open Mic (VAD) modes
- Settings persistence

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
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
    ┌──────────┐    ┌──────────┐    ┌──────────────────────────┐
    │  Ollama  │    │ Wyoming  │    │   Wyoming Piper          │
    │  (LLM)   │    │ Whisper  │    │   (TTS)                  │
    │ :11434   │    │ (STT)    │    │   Docker: :10200         │
    └──────────┘    │ :10300   │    └──────────────────────────┘
                    └──────────┘
```

### Docker Services Required
```bash
# Whisper (STT) - Wyoming protocol
docker run -d --name wyoming-whisper \
  -p 10300:10300 \
  rhasspy/wyoming-whisper --model small --language en

# Piper (TTS) - Wyoming protocol  
docker run -d --name piper \
  -p 10200:10200 \
  -v /path/to/voices:/config \
  lscr.io/linuxserver/piper
```

---

## 📁 Codebase Structure

```
galatea/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, WebSocket handler, core logic
│   │   ├── config.py            # Pydantic settings (hosts, ports, defaults)
│   │   ├── services/
│   │   │   ├── ollama.py        # Ollama LLM client with streaming
│   │   │   ├── wyoming.py       # Wyoming protocol clients (Whisper/Piper)
│   │   │   └── settings_manager.py  # User settings persistence
│   │   └── models/
│   │       └── schemas.py       # Pydantic models (UserSettings, etc.)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app layout
│   │   ├── components/
│   │   │   ├── VoiceInterface.tsx   # Mic button, status, visualizer
│   │   │   ├── Settings.tsx         # Settings panel
│   │   │   ├── AudioVisualizer.tsx  # Canvas-based audio viz
│   │   │   ├── Transcript.tsx       # Conversation display
│   │   │   └── StatusBar.tsx        # Connection status
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
{"type": "interrupt"}
{"type": "settings_update", "settings": {...}}
{"type": "clear_history"}
```

**Backend → Frontend:**
```json
{"type": "status", "state": "idle|processing|thinking|speaking"}
{"type": "transcription", "text": "...", "final": true}
{"type": "llm_chunk", "text": "..."}
{"type": "llm_complete", "text": "..."}
{"type": "audio_chunk", "audio": "<base64 wav>", "sentence": "..."}
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

---

## 🎨 UI/UX Decisions

- **Futuristic Cyberpunk Theme**: Cyan accents, dark backgrounds, glow effects
- **Minimal Text**: Voice-first interface, transcript is optional
- **Visual Feedback**: 
  - Audio visualizer shows mic levels
  - Color-coded states (green=listening, yellow=recording, cyan=speaking)
  - Pulse animations for active states

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
| UI components | `frontend/src/components/*.tsx` |
| State management | `frontend/src/stores/*.ts` |
| Audio handling | `frontend/src/hooks/useAudioRecorder.ts` |

---

## 🗺️ Roadmap (Phase 2+)

### Immediate Priorities
1. **Memory/RAG** - Store and retrieve conversation history
   - Add ChromaDB for vector storage
   - Implement conversation summarization
   - Add relevant context to prompts

2. **Time Awareness** - Gala knows current time, day, holidays
   - Already passing `current_time` to system prompt
   - Extend with holiday detection, "last conversation" tracking

3. **Better Interruption** - Stop Gala mid-sentence smoothly
   - Cancel TTS generation
   - Clear audio queue
   - Graceful state transition

### Future Features
4. **Wake Word** - "Hey Gala" activation
5. **Multi-language** - Support other languages for voice
6. **Vision** - Camera/screen capture for context
7. **Tool Calling** - Web search, file operations, code execution
8. **Image Generation** - Stable Diffusion / ComfyUI integration
9. **Emotion Detection** - Analyze user sentiment from voice/camera

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
- **Voice**: Currently using `en_GB-cori-high` (Welsh English, sounds natural)
- **Model**: Using Qwen3 (needs thinking disabled for speed)
- **Style**: Prefers conversational, natural responses
- **Clean Speech**: No emojis, no action markers, no thinking aloud

---

*Last updated: December 2024*
*Repository: https://github.com/lafintiger/galatea*

