# Galatea - Local Voice AI Companion

## Product Requirements Document (PRD)
**Version:** 1.0  
**Date:** December 6, 2024  
**Codename:** Galatea (Gala)

---

## 1. Vision & Overview

### 1.1 Product Vision
Galatea is a local, privacy-first AI voice companion that enables seamless, natural conversation with locally-running language models. Named after the mythological figure brought to life by Pygmalion, Galatea represents the aspiration to create a truly lifelike AI companion that grows and evolves with its user.

### 1.2 Core Philosophy
- **Privacy First**: All processing happens locally—no data leaves the user's machine
- **Seamless Interaction**: Voice-first experience that feels natural and fluid
- **Extensible Foundation**: Modular architecture designed for continuous capability expansion
- **User Empowerment**: Users control their AI's personality, voice, memory, and capabilities

### 1.3 Target Platform
- Primary: Windows PC (RTX 5090 24GB VRAM, 64GB RAM)
- Secondary: macOS (future)
- Deployment: Local-first, with potential for LAN access later

---

## 2. Technical Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GALATEA WEB UI (React + TypeScript)             │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │  Voice Interface │  │   Controls   │  │   Work Area (Phase 3+)   │  │
│  │  - Visualizer    │  │   - Settings │  │   - Documents            │  │
│  │  - Status        │  │   - Model    │  │   - Images               │  │
│  │  - Transcript    │  │   - Voice    │  │   - Code                 │  │
│  └──────────────────┘  └──────────────┘  └───────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ WebSocket (bidirectional audio + events)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GALATEA CORE (Python + FastAPI)                      │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                   Conversation Orchestrator                     │    │
│  │  - Context Management    - Memory Injection    - Persona        │    │
│  │  - Time Awareness        - Tool Dispatch       - Multi-turn     │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │ STT Service │ │ LLM Service │ │ TTS Service │ │ Memory Service  │   │
│  │ (Whisper)   │ │ (Ollama)    │ │ (Piper)     │ │ (ChromaDB+SQL)  │   │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └────────┬────────┘   │
│         │               │               │                  │            │
│  ┌──────┴───────────────┴───────────────┴──────────────────┴────────┐  │
│  │                      Tool Registry (Extensible)                   │  │
│  │  Phase 1: Core    Phase 3: Search    Phase 4: Vision, Image Gen  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Wyoming       │    │    Ollama     │    │ Wyoming       │
│ Whisper       │    │  localhost    │    │ Piper         │
│ :10300        │    │  :11434       │    │ :10200        │
│ (Docker)      │    │               │    │ (Docker)      │
└───────────────┘    └───────────────┘    └───────────────┘
                                                 │
                            ┌────────────────────┴────────────────────┐
                            │         Future Integrations             │
                            │  - Perplexica (:3000) / SearXNG (:4000) │
                            │  - Stable Diffusion / ComfyUI           │
                            │  - Code Execution Sandbox               │
                            │  - Camera / Vision Models               │
                            └─────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | React 18 + TypeScript + Vite | Component architecture, type safety, fast HMR |
| **Styling** | Tailwind CSS + CSS Variables | Rapid styling, easy theming |
| **Audio** | Web Audio API + MediaRecorder | Native browser audio handling |
| **State** | Zustand | Lightweight, flexible state management |
| **Backend** | Python 3.11 + FastAPI | Async, ML ecosystem, WebSocket support |
| **Real-time** | WebSockets | Bidirectional audio streaming |
| **Database** | SQLite → PostgreSQL | Conversations, settings, user data |
| **Vector Store** | ChromaDB | Local embeddings for RAG |
| **LLM** | Ollama | Local model serving |
| **STT** | Faster-Whisper (Wyoming) | Fast, accurate transcription |
| **TTS** | Piper (Wyoming) | Natural speech synthesis |

### 2.3 Service Endpoints

| Service | Protocol | Host | Port |
|---------|----------|------|------|
| Galatea Backend | HTTP/WS | localhost | 8000 |
| Galatea Frontend | HTTP | localhost | 5173 |
| Ollama | HTTP | localhost | 11434 |
| Whisper (STT) | Wyoming | localhost | 10300 |
| Piper (TTS) | Wyoming | localhost | 10200 |
| Perplexica | HTTP | localhost | 3000 |
| SearXNG | HTTP | localhost | 4000 |

---

## 3. Feature Specification

### 3.1 Phase 1: Walking (MVP) 🚶
**Goal:** Establish the core voice conversation loop

#### 3.1.1 Voice Input
- [x] Push-to-talk button (hold to record)
- [x] Visual feedback during recording (waveform/visualizer)
- [x] Audio capture via MediaRecorder API
- [x] Stream audio to backend via WebSocket
- [x] Real-time transcription display

#### 3.1.2 LLM Integration
- [x] Connect to Ollama API
- [x] Model selection dropdown (persisted preference)
- [x] Default model: `huihui_ai/qwen3-abliterated:8b`
- [x] System prompt with Galatea persona
- [x] Streaming response support

#### 3.1.3 Voice Output
- [x] Text-to-speech via Piper (Wyoming protocol)
- [x] Audio playback in browser
- [x] Manual interrupt button (stop speaking)
- [x] Female voice (configurable)

#### 3.1.4 Basic UI
- [x] Futuristic dark theme
- [x] Central voice interaction area
- [x] Audio visualizer (input + output)
- [x] Status indicators (listening, thinking, speaking)
- [x] Settings panel (model, voice, assistant name)

#### 3.1.5 Settings (Phase 1)
- [x] Assistant name (default: Galatea, nickname: Gala)
- [x] LLM model selection
- [x] Voice selection (female EN-US and EN-GB voices)
- [x] Response style toggle (concise/conversational)

### 3.2 Phase 2: Running 🏃
**Goal:** Add intelligence and memory

#### 3.2.1 Voice Activation
- [ ] Voice Activity Detection (VAD)
- [ ] Configurable silence threshold
- [ ] Visual indicator when VAD active

#### 3.2.2 Memory System
- [ ] Conversation history persistence (SQLite)
- [ ] Session management (new/continue conversation)
- [ ] ChromaDB integration for semantic memory
- [ ] RAG: Inject relevant memories into context
- [ ] User profile storage (facts about user)

#### 3.2.3 Enhanced UI
- [ ] Transcript panel (toggleable)
- [ ] Conversation history browser
- [ ] Memory viewer/editor

### 3.3 Phase 3: Flying ✈️
**Goal:** Contextual awareness and content handling

#### 3.3.1 Time Awareness
- [ ] Current time/date injection
- [ ] Time since last conversation
- [ ] Holiday awareness
- [ ] Contextual greetings (morning/evening)

#### 3.3.2 Wake Word
- [ ] Local wake word detection
- [ ] Configurable wake phrase
- [ ] Always-listening mode (optional)

#### 3.3.3 Work Area
- [ ] Document upload/display
- [ ] Text extraction from documents
- [ ] URL content fetching
- [ ] Context injection from work area

#### 3.3.4 Multi-language
- [ ] Language detection
- [ ] Multi-language TTS voices
- [ ] Translation capabilities

### 3.4 Phase 4: Soaring 🚀
**Goal:** Advanced capabilities and tool use

#### 3.4.1 Tool System
- [ ] Extensible tool registry
- [ ] Web search (Perplexica/SearXNG integration)
- [ ] Code execution sandbox
- [ ] File operations

#### 3.4.2 Image Generation
- [ ] Stable Diffusion / ComfyUI integration
- [ ] Voice-triggered image generation
- [ ] Image display in work area

#### 3.4.3 Vision Capabilities
- [ ] Vision model for work area (`qwen3-vl:8b`)
- [ ] Camera access for user observation
- [ ] Emotion detection
- [ ] Multi-model coordination

#### 3.4.4 Advanced UI
- [ ] Theme system (multiple visual styles)
- [ ] Avatar/visual representation
- [ ] Customizable layouts

---

## 4. Data Models

### 4.1 User Settings
```typescript
interface UserSettings {
  id: string;
  assistantName: string;           // default: "Galatea"
  assistantNickname: string;       // default: "Gala"
  selectedModel: string;           // Ollama model ID
  selectedVoice: string;           // Piper voice ID
  responseStyle: 'concise' | 'conversational';
  activationMode: 'push-to-talk' | 'vad' | 'wake-word';
  wakeWord?: string;
  transcriptVisible: boolean;
  theme: string;
  language: string;
}
```

### 4.2 Conversation
```typescript
interface Conversation {
  id: string;
  title: string;
  createdAt: DateTime;
  updatedAt: DateTime;
  messages: Message[];
  summary?: string;              // For memory/RAG
}

interface Message {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  audioUrl?: string;            // Stored audio file
  timestamp: DateTime;
  metadata?: {
    model?: string;
    voice?: string;
    processingTime?: number;
  };
}
```

### 4.3 Memory Entry (RAG)
```typescript
interface MemoryEntry {
  id: string;
  content: string;
  embedding: number[];          // Vector for similarity search
  type: 'fact' | 'preference' | 'event' | 'conversation';
  source: string;               // conversation ID or manual
  createdAt: DateTime;
  lastAccessed?: DateTime;
  importance: number;           // For memory prioritization
}
```

---

## 5. API Specification

### 5.1 WebSocket Events

#### Client → Server
```typescript
// Start recording
{ type: 'audio_start' }

// Audio chunk (base64 encoded)
{ type: 'audio_chunk', data: string }

// Stop recording
{ type: 'audio_stop' }

// Interrupt AI speech
{ type: 'interrupt' }

// Text input (alternative to voice)
{ type: 'text_message', content: string }
```

#### Server → Client
```typescript
// Transcription result
{ type: 'transcription', text: string, final: boolean }

// LLM response chunk (streaming)
{ type: 'llm_chunk', text: string }

// LLM response complete
{ type: 'llm_complete', fullText: string }

// Audio chunk for playback
{ type: 'audio_chunk', data: string, format: 'wav' }

// Audio playback complete
{ type: 'audio_complete' }

// Status updates
{ type: 'status', state: 'listening' | 'processing' | 'speaking' | 'idle' }

// Error
{ type: 'error', message: string, code: string }
```

### 5.2 REST Endpoints

```
GET  /api/settings              - Get user settings
PUT  /api/settings              - Update user settings
GET  /api/models                - List available Ollama models
GET  /api/voices                - List available Piper voices
GET  /api/conversations         - List conversations
GET  /api/conversations/:id     - Get conversation with messages
POST /api/conversations         - Create new conversation
DELETE /api/conversations/:id   - Delete conversation
GET  /api/health                - Health check
```

---

## 6. Piper Voice Configuration

### 6.1 Required Voices (Female, English)
Download and configure the following Piper voices:

#### US English (en_US)
| Voice | Quality | Style |
|-------|---------|-------|
| en_US-amy-medium | Medium | Neutral |
| en_US-amy-low | Low | Neutral |
| en_US-lessac-medium | Medium | Expressive |
| en_US-lessac-high | High | Expressive |
| en_US-libritts-high | High | Various |
| en_US-ljspeech-medium | Medium | Audiobook |
| en_US-ljspeech-high | High | Audiobook |

#### British English (en_GB)
| Voice | Quality | Style |
|-------|---------|-------|
| en_GB-alba-medium | Medium | Scottish |
| en_GB-jenny_dioco-medium | Medium | Southern British |
| en_GB-cori-medium | Medium | Welsh |

### 6.2 Default Voice
`en_US-lessac-medium` - Good balance of quality and naturalness

---

## 7. Ollama Model Configuration

### 7.1 Recommended Models

| Purpose | Model | Size | Notes |
|---------|-------|------|-------|
| **Default Chat** | `huihui_ai/qwen3-abliterated:8b` | 5GB | Fast, natural conversation |
| **High Quality** | `huihui_ai/qwen3-abliterated:32b` | 19GB | Slower but more capable |
| **Vision** | `qwen3-vl:8b` | 6.1GB | For work area / documents |
| **Embeddings** | `bge-m3:latest` | 1.2GB | For RAG memory system |

### 7.2 System Prompt Template
```
You are {assistant_name}, a thoughtful and engaging AI companion. Your nickname is {nickname}.

Personality traits:
- Warm and genuine in conversation
- Intellectually curious
- Supportive and encouraging
- Occasionally playful with a subtle wit

Response style: {response_style}
- If "concise": Keep responses brief and to the point. 1-3 sentences unless more detail is requested.
- If "conversational": Be more expansive and natural. Share thoughts, ask follow-up questions, engage deeply.

Context:
- Current time: {current_time}
- User name: {user_name}
- Relevant memories: {memories}

Remember: You are having a voice conversation. Keep responses natural for speech - avoid bullet points, 
code blocks (unless specifically discussing code), and overly structured formatting.
```

---

## 8. Project Structure

```
galatea/
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── VoiceInterface/  # Main voice interaction
│   │   │   ├── AudioVisualizer/ # Waveform display
│   │   │   ├── Settings/        # Settings panel
│   │   │   ├── Transcript/      # Chat transcript
│   │   │   └── WorkArea/        # Document/content area (Phase 3)
│   │   ├── hooks/
│   │   │   ├── useAudioRecorder.ts
│   │   │   ├── useWebSocket.ts
│   │   │   └── useAudioPlayer.ts
│   │   ├── stores/
│   │   │   ├── settingsStore.ts
│   │   │   └── conversationStore.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── styles/
│   │   │   └── themes/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                     # Python FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Configuration
│   │   ├── routers/
│   │   │   ├── websocket.py     # WebSocket handler
│   │   │   ├── settings.py      # Settings endpoints
│   │   │   ├── models.py        # Model listing
│   │   │   └── conversations.py # Conversation CRUD
│   │   ├── services/
│   │   │   ├── stt.py           # Whisper/Wyoming client
│   │   │   ├── tts.py           # Piper/Wyoming client
│   │   │   ├── llm.py           # Ollama client
│   │   │   ├── memory.py        # Memory/RAG service
│   │   │   └── orchestrator.py  # Conversation flow
│   │   ├── models/
│   │   │   ├── settings.py      # Pydantic models
│   │   │   └── conversation.py
│   │   └── database/
│   │       ├── db.py            # Database connection
│   │       └── migrations/
│   ├── requirements.txt
│   └── pyproject.toml
│
├── docker/                      # Docker configurations
│   └── docker-compose.yml       # For additional services
│
├── data/                        # Local data storage
│   ├── galatea.db               # SQLite database
│   ├── chroma/                  # ChromaDB vector store
│   └── audio/                   # Stored audio files
│
├── PRD.md                       # This document
├── README.md                    # Setup instructions
└── .env.example                 # Environment template
```

---

## 9. Development Phases & Milestones

### Phase 1: Walking (MVP) - Week 1-2
**Milestone:** Complete voice conversation loop

- [ ] Project scaffolding (frontend + backend)
- [ ] Wyoming protocol client (STT + TTS)
- [ ] Ollama integration with streaming
- [ ] WebSocket communication
- [ ] Basic UI with visualizer
- [ ] Settings persistence
- [ ] Push-to-talk recording
- [ ] Audio playback
- [ ] Manual interrupt

**Success Criteria:** User can have a continuous voice conversation with Galatea

### Phase 2: Running - Week 3-4
**Milestone:** Memory and natural interaction

- [ ] VAD implementation
- [ ] SQLite conversation storage
- [ ] ChromaDB setup
- [ ] RAG memory injection
- [ ] Transcript UI
- [ ] Conversation history

**Success Criteria:** Galatea remembers past conversations and user preferences

### Phase 3: Flying - Week 5-6
**Milestone:** Contextual awareness

- [ ] Time awareness system
- [ ] Wake word detection
- [ ] Work area UI
- [ ] Document handling
- [ ] Multi-language support

**Success Criteria:** Galatea is contextually aware and can handle documents

### Phase 4: Soaring - Week 7+
**Milestone:** Advanced capabilities

- [ ] Tool system framework
- [ ] Web search integration
- [ ] Image generation
- [ ] Vision capabilities
- [ ] Theme system

**Success Criteria:** Galatea can use tools and see content

---

## 10. Success Metrics

### Core Experience
- **Latency:** Voice input to speech start < 2 seconds
- **Accuracy:** Transcription WER < 10%
- **Naturalness:** TTS sounds natural and appropriate
- **Reliability:** 99% success rate for conversation turns

### Engagement
- **Session Length:** Average conversation > 5 minutes
- **Return Rate:** User returns within 24 hours
- **Feature Usage:** Memory recalled in 30%+ of conversations

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wyoming protocol complexity | High | Build abstraction layer, fallback to HTTP |
| Audio latency | High | Stream in chunks, optimize buffer sizes |
| Memory context overflow | Medium | Implement summarization, relevance filtering |
| Model response quality | Medium | Careful prompt engineering, model selection |
| Cross-platform audio | Medium | Use Web Audio API standards, test early |

---

## 12. Future Considerations

### Potential Integrations
- **Home Assistant:** Use existing Wyoming infrastructure
- **Mobile App:** React Native companion app
- **Browser Extension:** Quick access to Galatea
- **API Mode:** Let other apps use Galatea as a service

### Advanced Features
- **Proactive Mode:** Galatea initiates conversation based on context
- **Learning Mode:** Fine-tune responses based on user feedback
- **Multi-user:** Support for multiple user profiles
- **Offline Mode:** Fully offline operation with local models

---

## Appendix A: Wyoming Protocol Reference

The Wyoming protocol is a simple TCP-based protocol for voice services.

### Connection
```python
# Connect to service
reader, writer = await asyncio.open_connection(host, port)
```

### Message Format
```python
# Send message
message = json.dumps({"type": "transcribe", "data": {...}})
writer.write(f"{len(message)}\n{message}".encode())

# Receive message
length = int(await reader.readline())
data = await reader.read(length)
message = json.loads(data)
```

### STT (Whisper) Events
- `transcribe` - Send audio for transcription
- `transcript` - Receive transcription result

### TTS (Piper) Events
- `synthesize` - Send text for synthesis
- `audio-start` - Audio stream starting
- `audio-chunk` - Audio data chunk
- `audio-stop` - Audio stream complete

---

## Appendix B: Environment Variables

```bash
# Backend
OLLAMA_HOST=http://localhost:11434
WHISPER_HOST=localhost
WHISPER_PORT=10300
PIPER_HOST=localhost
PIPER_PORT=10200
DATABASE_URL=sqlite:///./data/galatea.db
CHROMA_PATH=./data/chroma

# Optional
PERPLEXICA_URL=http://localhost:3000
SEARXNG_URL=http://localhost:4000
```

---

*"What the user dreams, the engineer builds, and Galatea speaks."*



