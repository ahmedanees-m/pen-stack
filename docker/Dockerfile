# pen-stack:1.0.0 — Full platform container
# Build: docker build -t pen-stack:1.0.0 -f docker/Dockerfile .
# Run:   docker-compose -f docker/docker-compose.yml up
FROM python:3.11-slim

LABEL org.opencontainers.image.title="PEN-STACK Platform"
LABEL org.opencontainers.image.description="Comprehensive platform for non-destructive genome engineering"
LABEL org.opencontainers.image.source="https://github.com/ahmedanees-m/pen-stack"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential ca-certificates wget \
    tabix samtools bedtools \
    && rm -rf /var/lib/apt/lists/*

# Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install all PEN-STACK upstream packages (frozen versions)
RUN pip install --no-cache-dir \
    "genome-atlas>=0.7.2,<0.8.0" \
    "mech-class>=0.5.4,<0.6.0" \
    "pen-score>=0.1.3,<0.2.0" \
    "pen-assemble>=0.5.2,<0.6.0"

# Install pen-stack with all extras
WORKDIR /workspace
COPY . /workspace/pen-stack
RUN pip install -e "/workspace/pen-stack[full]"

# Pre-download ESM-2 650M model weights (~1.3 GB; cached in Docker layer)
# Done at build time so first run is instant
RUN python -c "
from transformers import EsmModel, EsmTokenizer
model = EsmModel.from_pretrained('facebook/esm2_t33_650M_UR50D', cache_dir='/root/.cache/esm2')
tokenizer = EsmTokenizer.from_pretrained('facebook/esm2_t33_650M_UR50D', cache_dir='/root/.cache/esm2')
print('ESM-2 650M pre-downloaded')
"

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Ports: 8501=Streamlit  8000=FastAPI  11434=Ollama
EXPOSE 8501 8000 11434

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
