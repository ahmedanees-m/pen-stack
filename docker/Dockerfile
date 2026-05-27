# pen-stack:1.0.0 — Full platform container
# Build: docker build -t pen-stack:1.0.0 -f docker/Dockerfile .
# Run:   docker-compose -f docker/docker-compose.yml up
FROM python:3.11-slim

LABEL org.opencontainers.image.title="PEN-STACK Platform"
LABEL org.opencontainers.image.description="Comprehensive platform for non-destructive genome engineering"
LABEL org.opencontainers.image.source="https://github.com/ahmedanees-m/pen-stack"

# System dependencies
# - build-essential, g++: C/C++ compilation for pybedtools and other native exts
# - zlib1g-dev, libbz2-dev, liblzma-dev: headers needed by pybedtools (zlib.h etc.)
# - zstd: required by Ollama installer (v0.4+) for archive extraction
# - tabix samtools bedtools: genomics CLI tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential ca-certificates wget zstd \
    zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev \
    tabix samtools bedtools \
    && rm -rf /var/lib/apt/lists/*

# Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install PEN-STACK upstream data-layer packages from pinned GitHub tags
# (PyPI only has early placeholder versions; real implementations in GitHub)
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
# Uses a dedicated script to avoid shell-quoting / Dockerfile FROM-ambiguity issues
RUN python3 /workspace/pen-stack/scripts/predownload_esm2.py

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Ports: 8501=Streamlit  8000=FastAPI  11434=Ollama
EXPOSE 8501 8000 11434

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
