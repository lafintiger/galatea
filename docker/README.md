# Galatea Docker Deployment

**Your Local Vocal AI Suite**

## 📦 What's Included

| Service | Purpose | Port |
|---------|---------|------|
| 🗣️ **Galatea** | Voice AI companion | 5173 |
| 🦙 **Ollama** | Local LLM inference | 11434 |
| 🎤 **Whisper** | Speech-to-Text | 10300 |
| 🔊 **Piper** | Fast TTS | 10200 |
| 🔊 **Kokoro** | HD TTS | 8880 |
| 🔍 **SearXNG** | Private search | 4000 |
| 🧠 **Perplexica** | AI research | 3000 |

---

## 🚀 Quick Start Scenarios

### Scenario 1: Fresh Install (Everything in Docker)

You have nothing installed - this starts everything:

```bash
git clone https://github.com/lafintiger/galatea
cd galatea
docker compose --profile full up -d
```

First run downloads ~10GB of models. Wait for it:
```bash
docker logs -f galatea-ollama-init
```

### Scenario 2: Existing Ollama (Native/Metal)

You have Ollama installed natively on your machine:

```bash
git clone https://github.com/lafintiger/galatea
cd galatea

# Mac/Linux
OLLAMA_HOST=http://host.docker.internal:11434 docker compose --profile with-search up -d

# Windows (PowerShell)
$env:OLLAMA_HOST="http://host.docker.internal:11434"
docker compose --profile with-search up -d
```

### Scenario 3: Existing Ollama + Perplexica/SearXNG

You have Ollama native AND Perplexica/SearXNG already in Docker:

```bash
git clone https://github.com/lafintiger/galatea
cd galatea

# Create .env file with your existing services
cat > .env << EOF
OLLAMA_HOST=http://host.docker.internal:11434
SEARXNG_HOST=host.docker.internal
SEARXNG_PORT=4000
PERPLEXICA_HOST=host.docker.internal
PERPLEXICA_PORT=3001
EOF

# Start just Galatea + voice services
docker compose up -d
```

This starts only:
- ✅ Galatea backend & frontend
- ✅ Whisper (STT)
- ✅ Piper (TTS)
- ✅ Kokoro (HD TTS)

And connects to your existing:
- 🦙 Ollama (native)
- 🔍 SearXNG (existing Docker)
- 🧠 Perplexica (existing Docker)

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Point to native Ollama
OLLAMA_HOST=http://host.docker.internal:11434

# Point to existing search services
SEARXNG_HOST=host.docker.internal
SEARXNG_PORT=4000
PERPLEXICA_HOST=host.docker.internal
PERPLEXICA_PORT=3001

# TTS provider: "piper" (fast) or "kokoro" (HD)
TTS_PROVIDER=kokoro

# Timezone
TZ=America/Los_Angeles
```

### Profiles

| Profile | What it starts |
|---------|----------------|
| (none) | Galatea + Voice only |
| `--profile with-ollama` | + Ollama in Docker |
| `--profile with-search` | + SearXNG + Perplexica |
| `--profile full` | Everything |

---

## 🖥️ Access Points

After starting, open your browser:

| Service | URL |
|---------|-----|
| **Galatea** | http://localhost:5173 |
| **SearXNG** | http://localhost:4000 |
| **Perplexica** | http://localhost:3000 |

---

## 🛠️ Commands

```bash
# Start services
docker compose up -d                           # Default (Galatea + voice)
docker compose --profile full up -d            # Everything

# View logs
docker compose logs -f                         # All services
docker compose logs -f galatea-backend         # Just backend

# Stop services
docker compose down

# Update images
docker compose pull
docker compose up -d

# Download more Ollama models
docker exec -it galatea-ollama ollama pull qwen3:8b
```

---

## 💾 Data & Backups

Data persists in Docker volumes:

| Volume | Contents |
|--------|----------|
| `galatea-data` | Conversations, settings, embeddings |
| `galatea-ollama-models` | LLM models |
| `galatea-whisper-models` | Speech recognition |
| `galatea-piper-voices` | TTS voices |

### Backup

```bash
docker run --rm -v galatea-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/galatea-backup.tar.gz /data
```

---

## 🔧 Troubleshooting

### "Connection refused" to Ollama

If using native Ollama, make sure it's running:
```bash
ollama list  # Should show models
```

And use `host.docker.internal`:
```bash
OLLAMA_HOST=http://host.docker.internal:11434 docker compose up -d
```

### Voice not working

Check voice service logs:
```bash
docker logs galatea-whisper
docker logs galatea-kokoro
```

### Port conflicts

If ports are in use, edit `docker-compose.yml` or stop conflicting services.

---

## 📋 System Requirements

| | Minimum | Recommended |
|--|---------|-------------|
| **RAM** | 16GB | 32GB |
| **Storage** | 20GB | 50GB |
| **GPU** | None (CPU) | 8GB+ VRAM |
