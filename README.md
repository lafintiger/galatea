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

## Platform Support

✅ **Windows** - Fully supported  
✅ **macOS** - Fully supported (Intel & Apple Silicon)  
✅ **Linux** - Fully supported  

All components (Python, Node.js, Docker, Ollama) are cross-platform.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
- **Ollama** - [Download here](https://ollama.ai/)

## Quick Start

### 1. Install Docker Containers (STT & TTS)

First, install and start the required Docker containers for speech-to-text (Whisper) and text-to-speech (Piper):

#### Wyoming Whisper (Faster-Whisper STT)

```bash
# Pull and run the Wyoming Whisper container
docker run -d \
  --name wyoming-whisper \
  --restart unless-stopped \
  -p 10300:10300 \
  rhasspy/wyoming-whisper \
  --model small \
  --language en
```

**Multi-Language Support:** To enable automatic language detection (speak any language!), remove the `--language en` flag:
```bash
docker run -d \
  --name wyoming-whisper \
  --restart unless-stopped \
  -p 10300:10300 \
  rhasspy/wyoming-whisper \
  --model small
```

Then select a matching voice in Gala's Settings (e.g., Japanese voice for Japanese speech).

**Options:**
- `--model` - Whisper model size: `tiny`, `base`, `small`, `medium`, `large-v3` (larger = more accurate but slower)
- `--language` - Language code (e.g., `en`, `es`, `fr`, `de`)

#### Option A: Piper TTS (Fast, CPU-based)

Best for: Quick responses, lower-end hardware, CPU-only systems

```bash
# Create a directory for voices
mkdir -p piper-voices

# Pull and run the Piper container
docker run -d \
  --name piper \
  --restart unless-stopped \
  -p 10200:10200 \
  -v $(pwd)/piper-voices:/data \
  rhasspy/wyoming-piper \
  --voice en_US-lessac-medium
```

**Windows PowerShell:** Replace `$(pwd)` with `${PWD}` or the full path:
```powershell
docker run -d `
  --name piper `
  --restart unless-stopped `
  -p 10200:10200 `
  -v ${PWD}/piper-voices:/data `
  rhasspy/wyoming-piper `
  --voice en_US-lessac-medium
```

**Popular Piper voices:**
- `en_US-lessac-medium` - American English (natural)
- `en_GB-cori-high` - British/Welsh English (recommended)
- `en_US-amy-medium` - American English (female)

Browse all Piper voices at: https://rhasspy.github.io/piper-samples/

---

#### Option B: Kokoro TTS (High Quality, GPU-accelerated) ⭐ Recommended

Best for: Natural-sounding speech, systems with NVIDIA GPU

Kokoro is a newer, higher-quality TTS model that produces more natural, expressive speech.

**For GPU (NVIDIA - Recommended):**
```bash
docker run -d \
  --name kokoro-tts \
  --gpus all \
  --restart unless-stopped \
  -p 8880:8880 \
  ghcr.io/remsky/kokoro-fastapi-gpu
```

**For CPU (slower but works anywhere):**
```bash
docker run -d \
  --name kokoro-tts \
  --restart unless-stopped \
  -p 8880:8880 \
  ghcr.io/remsky/kokoro-fastapi-cpu
```

**Windows PowerShell (GPU):**
```powershell
docker run -d `
  --name kokoro-tts `
  --gpus all `
  --restart unless-stopped `
  -p 8880:8880 `
  ghcr.io/remsky/kokoro-fastapi-gpu
```

**Popular Kokoro voices:**
- `af_heart` - American Female, warm (recommended)
- `af_bella` - American Female, clear
- `af_nova` - American Female, energetic
- `bf_emma` - British Female, natural
- `am_adam` - American Male, friendly
- `bm_george` - British Male, professional

Access the Kokoro web UI at: http://localhost:8880/web

> **Note:** You can install both Piper and Kokoro and switch between them in the settings!

#### Verify Containers are Running

```bash
docker ps

# Should show:
# wyoming-whisper on port 10300
# piper on port 10200 (if using Piper)
# kokoro-tts on port 8880 (if using Kokoro)
```

### 2. Install Ollama and a Model

```bash
# After installing Ollama from https://ollama.ai/
# Pull a recommended model:
ollama pull qwen2.5:7b

# Or for more capable conversations:
ollama pull qwen2.5:14b
```

### 3. Clone and Setup Backend

```bash
git clone https://github.com/lafintiger/galatea.git
cd galatea

# Create Python virtual environment
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Setup Frontend

```bash
cd ../frontend
npm install
```

### 5. Start the Application

**Terminal 1 - Backend:**
```bash
cd backend

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
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

# Start containers if stopped
docker start wyoming-whisper piper

# View logs if issues occur
docker logs wyoming-whisper
docker logs piper
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

**Check Ollama:**
```bash
curl http://localhost:11434/api/tags
```

**Check Whisper (port 10300):**
```bash
# macOS/Linux:
nc -zv localhost 10300

# Windows PowerShell:
Test-NetConnection localhost -Port 10300
```

**Check Piper (port 10200):**
```bash
# macOS/Linux:
nc -zv localhost 10200

# Windows PowerShell:
Test-NetConnection localhost -Port 10200
```

### Docker Issues

```bash
# Restart containers
docker restart wyoming-whisper piper

# Recreate containers if needed
docker rm -f wyoming-whisper piper
# Then run the docker run commands from Quick Start again
```

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


