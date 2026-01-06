# Parakeet ASR Server
# NVIDIA Parakeet Speech-to-Text with low latency

# Use NVIDIA PyTorch base for GPU support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    soundfile \
    torchaudio \
    transformers \
    huggingface_hub

# Install NeMo toolkit (for full Parakeet support)
# Note: This is a large install, comment out if using HF only
RUN pip install --no-cache-dir \
    nemo_toolkit[asr] \
    || echo "NeMo install failed, will use HuggingFace fallback"

# Copy server code
COPY server.py .

# Environment variables
ENV PARAKEET_MODEL=nvidia/parakeet-ctc-1.1b
ENV HF_HOME=/app/models

# Create models directory
RUN mkdir -p /app/models

# Expose port
EXPOSE 50052

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:50052/health || exit 1

# Run server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "50052"]
