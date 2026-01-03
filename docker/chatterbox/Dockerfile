# Chatterbox TTS Server
# GPU-accelerated TTS with voice cloning support

# Use Python base for cross-platform support (ARM64 + AMD64)
# For NVIDIA GPU: use pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Note: PyTorch will auto-detect CUDA if available
RUN pip install --no-cache-dir \
    torch \
    torchaudio \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    chatterbox-tts

# Copy server code
COPY server.py .

# Create voices directory
RUN mkdir -p /app/voices

# Expose port
EXPOSE 8881

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8881/health || exit 1

# Run server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8881"]
