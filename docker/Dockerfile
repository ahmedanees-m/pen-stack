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

# Install PEN-STACK upstream data-layer packages from pinned GitHub tags
# (PyPI only has early placeholders; real implementations live in these repos)
RUN pip install --no-cache-dir \
    "git+https://github.com/ahmedanees-m/genome-atlas.git@v0.7.2" \
    "git+https://github.com/ahmedanees-m/mech-class.git@v0.5.4" \
    "git+https://github.com/ahmedanees-m/pen-score.git@v0.1.3" \
    "git+https://github.com/ahmedanees-m/pen-assemble.git@v0.5.2"

# Install pen-stack with all extras
WORKDIR /workspace
COPY . /workspace/pen-stack
RUN pip install --no-cache-dir -e "/workspace/pen-stack[full]"

# Pre-download ESM-2 650M model weights (~1.3 GB; cached in Docker layer)
# Done at build time so first run is instant.
# NOTE: written as a one-liner so Docker does not mis-parse the Python
# 'from' keyword as a Dockerfile FROM instruction.
RUN python3 -c "from transformers import EsmModel, EsmTokenizer; \
    EsmModel.from_pretrained('facebook/esm2_t33_650M_UR50D', cache_dir='/root/.cache/esm2'); \
    EsmTokenizer.from_pretrained('facebook/esm2_t33_650M_UR50D', cache_dir='/root/.cache/esm2'); \
    print('ESM-2 650M pre-downloaded')"

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Ports: 8501=Streamlit  8000=FastAPI  11434=Ollama
EXPOSE 8501 8000 11434

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
