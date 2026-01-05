# Galatea - Local Voice AI Companion 🎭

A privacy-first, local AI voice assistant that runs entirely on your machine. Named after the mythological figure brought to life by Pygmalion.

![Galatea](frontend/public/galatea.svg)

## Features

- 🎤 **Voice Conversation** - Natural voice input and output
- 🤖 **Local LLM** - Powered by Ollama (runs on your GPU)
- 👁️ **Vision** - "What do you see?" - Gala can describe you and your surroundings
- 🔒 **Privacy First** - All processing happens locally
- 🎨 **Futuristic UI** - Beautiful cyberpunk-inspired interface
- ⚡ **Real-time** - WebSocket-based streaming responses
- 🎛️ **Customizable** - Choose your model, voice, and personality
- 🔍 **Web Search** - Ask about weather, news, prices (via SearXNG/Perplexica)
- 📝 **Workspace** - Voice-controlled notes, todos, and data tracking

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

- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
- **Ollama** - [Download here](https://ollama.ai/) (or use Docker version)

## Quick Start (Docker Compose) ⭐ Recommended

The easiest way to run Galatea - one command starts everything!

### 1. Clone and Start

```bash
# Clone the repository
git clone https://github.com/lafintiger/galatea.git
cd galatea

# Start Galatea (uses your existing Ollama installation)
docker compose up -d

# Or start EVERYTHING including Ollama:
docker compose --profile full up -d
```

### 2. Install Required Ollama Models

```bash
# Command router + vision (required)
ollama pull ministral-3:latest

# Chat model (pick one)
ollama pull qwen2.5:7b
```

### 3. Open Galatea

Navigate to **http://localhost:5173** in your browser. That's it! 🎉

### Optional Profiles

```bash
# With Chatterbox voice cloning (requires HF_TOKEN + NVIDIA GPU)
export HF_TOKEN=your_huggingface_token
docker compose --profile chatterbox up -d

# With Vision (Gala can see you)
docker compose --profile vision up -d

# Everything at once
docker compose --profile full --profile chatterbox --profile vision up -d
```

### Access Points

| Service | URL |
|---------|-----|
| **Galatea** | http://localhost:5173 |
| **Backend API** | http://localhost:8010 |
| **Kokoro TTS Web UI** | http://localhost:8880/web |

---

## Manual Setup (For Development)

If you want to run services individually or develop locally:

### Prerequisites for Manual Setup

- **Python 3.11+**
- **Node.js 18+**
- **Docker Desktop**
- **Ollama**

### 1. Install Voice Services (STT & TTS)

You can run these individually or let docker-compose handle them:

#### Wyoming Whisper (Faster-Whisper STT)

> **Note:** If using `docker compose up`, this is already included! These commands are for manual setup only.

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

---

#### Option C: Chatterbox TTS (State-of-the-Art + Voice Cloning) 🎭

Best for: Highest quality speech, voice cloning, expressive emotions

Chatterbox is a cutting-edge TTS from Resemble AI with zero-shot voice cloning and paralinguistic tags.

**Features:**
- 🎭 **Voice Cloning** - Clone any voice from just 10 seconds of audio
- 😄 **Paralinguistic Tags** - Add `[laugh]`, `[chuckle]`, `[cough]` naturally
- 🌍 **Multilingual** - 23+ languages supported
- ⚡ **Turbo Mode** - Optimized for low-latency voice agents

**Requirements:**
1. **Hugging Face Token** - Get one at https://huggingface.co/settings/tokens
2. **Accept Model Terms** - Visit https://huggingface.co/ResembleAI/chatterbox and click "Agree"
3. **NVIDIA GPU** - Recommended for good performance

**Setup:**

```bash
# Set your Hugging Face token
export HF_TOKEN=hf_your_token_here

# Or add to .env file:
# HF_TOKEN=hf_your_token_here

# Start Galatea with Chatterbox
docker compose --profile chatterbox up --build
```

**For NVIDIA GPU (recommended):**

Edit `docker-compose.yml` and uncomment the GPU section under the chatterbox service:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

**Usage:**
1. Open Settings in Galatea
2. Click **Clone** button in Voice Engine section
3. Use "Default" voice or upload audio to clone your own voice

**Voice Cloning in the UI:**

1. Go to **Settings** → **Voice Engine** → Click **Clone**
2. Enter a name for the voice (e.g., "Dad's Voice")
3. Either:
   - **Record Live**: Click "Start Recording" and have them speak for 15-30 seconds
   - **Upload File**: Click "Upload File" to use an existing audio file
4. Click **Clone This Voice**
5. The new voice appears in your voice list!

**Recording Tips for Best Results:**

| Tip | Why |
|-----|-----|
| **15-30 seconds** | More audio = better quality clone |
| **Quiet room** | Minimizes background noise |
| **Natural speech** | Don't be too formal or stiff |
| **Vary emotion** | Helps capture vocal range |
| **Close to mic** | Clearer audio capture |

**Sample Script** (have them read this):
> "Hello, my name is [name] and I'm recording my voice. I like to speak 
> naturally with different emotions. Sometimes I'm excited! Other times 
> I'm calm and thoughtful. Let me tell you about my day..."

**Voice Cloning via API:**
```bash
# Clone a voice from audio file
curl -X POST http://localhost:8881/v1/audio/clone \
  -F "name=MyVoice" \
  -F "audio=@reference.wav"

# Use cloned voice
curl -X POST http://localhost:8881/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world!", "voice": "your_voice_id"}'
```

> **Note:** You can install all three TTS engines (Piper, Kokoro, Chatterbox) and switch between them in settings!

#### Verify Containers are Running

```bash
docker ps

# Should show:
# wyoming-whisper on port 10300
# piper on port 10200 (if using Piper)
# kokoro-tts on port 8880 (if using Kokoro)
```

### 2. Install Ollama and Models (if not using docker-compose)

```bash
# After installing Ollama from https://ollama.ai/

# REQUIRED: Ministral-3 for command routing + vision (fast, 3B)
ollama pull ministral-3:latest

# Chat model (choose one):
ollama pull qwen2.5:7b          # Balanced
ollama pull qwen2.5:14b         # More capable
ollama pull huihui_ai/qwen3-abliterated:4b  # Uncensored
```

### 3. Run Backend Locally (Development)

```bash
git clone https://github.com/lafintiger/galatea.git
cd galatea/backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

### 4. Run Frontend Locally (Development)

```bash
cd galatea/frontend
npm install
npm run dev
```

### 5. Open Galatea

Navigate to `http://localhost:5173` in your browser.

## Configuration

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=ministral-3:8b
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


