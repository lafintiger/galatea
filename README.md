# Galatea - Local Voice AI Companion 🎭

A privacy-first, local AI voice assistant that runs entirely on your machine. Named after the mythological figure brought to life by Pygmalion.

![Galatea](frontend/public/galatea.svg)

## Features

- 🎤 **Voice Conversation** - Natural voice input and output
- 🤖 **Local LLM** - Powered by Ollama (runs on your GPU)
- 🔒 **Privacy First** - All processing happens locally
- 🎨 **Futuristic UI** - Beautiful cyberpunk-inspired interface
- ⚡ **Real-time** - WebSocket-based streaming responses
- 🎛️ **Customizable** - Choose your model, voice, and personality

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend                        │
│         (Voice Interface, Settings, Transcript)         │
└─────────────────────────┬───────────────────────────────┘
                          │ WebSocket
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                        │
│            (Orchestration, Settings, Memory)            │
└──────┬─────────────────┬─────────────────┬──────────────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Whisper    │  │    Ollama    │  │    Piper     │
│  (Wyoming)   │  │    (LLM)     │  │  (Wyoming)   │
│   :10300     │  │   :11434     │  │   :10200     │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** running locally
- **Docker** with:
  - Wyoming Whisper (faster-whisper) on port 10300
  - Piper TTS on port 10200

## Quick Start

### 1. Clone and Setup

```bash
cd Local-voice-chat

# Create Python virtual environment
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Download Piper Voices

```bash
# Install requests if needed
pip install requests

# Run the voice downloader
python ../scripts/download_voices.py

# Copy voices to Piper Docker container
docker cp voices/. piper:/data/
```

### 3. Setup Frontend

```bash
cd ../frontend
npm install
```

### 4. Start the Backend

```bash
cd ../backend
.\venv\Scripts\activate  # Windows
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start the Frontend

```bash
cd frontend
npm run dev
```

### 6. Open Galatea

Navigate to `http://localhost:5173` in your browser.

## Configuration

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=huihui_ai/qwen3-abliterated:8b
WHISPER_HOST=localhost
WHISPER_PORT=10300
PIPER_HOST=localhost
PIPER_PORT=10200
DEFAULT_VOICE=en_US-lessac-medium
```

### Docker Services

Ensure your Docker containers are running:

```bash
# Check running containers
docker ps

# Expected services:
# - wyoming-whisper on port 10300
# - piper on port 10200
```

## Usage

1. **Push-to-Talk**: Click and hold the microphone button to record
2. **Text Input**: Type a message as an alternative to voice
3. **Interrupt**: Click the stop button while Galatea is speaking
4. **Settings**: Click the gear icon to customize:
   - Assistant name and nickname
   - AI model selection
   - Voice selection
   - Response style (concise/conversational)

## Project Structure

```
galatea/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI app entry
│   │   ├── config.py       # Configuration
│   │   ├── services/       # Ollama, Wyoming clients
│   │   └── models/         # Pydantic schemas
│   └── requirements.txt
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── hooks/         # Custom hooks
│   │   ├── stores/        # Zustand stores
│   │   └── styles/        # CSS/Tailwind
│   └── package.json
│
├── scripts/               # Utility scripts
│   └── download_voices.py # Voice downloader
│
├── data/                  # Local data storage
├── PRD.md                 # Product Requirements
└── README.md              # This file
```

## Troubleshooting

### Connection Issues

1. **Check Ollama**: `curl http://localhost:11434/api/tags`
2. **Check Whisper**: `Test-NetConnection localhost -Port 10300`
3. **Check Piper**: `Test-NetConnection localhost -Port 10200`

### Audio Issues

- Ensure microphone permissions are granted in browser
- Check browser console for audio errors
- Try using Chrome/Edge (best Web Audio API support)

### Voice Not Working

- Verify Piper has the selected voice installed
- Check Piper container logs: `docker logs piper`
- Try downloading voices again

## Roadmap

- [x] Phase 1: Core voice conversation
- [ ] Phase 2: Memory and RAG
- [ ] Phase 3: Time awareness, wake word
- [ ] Phase 4: Tool use, image generation

## License

MIT

---

*"What the user dreams, the engineer builds, and Galatea speaks."*

