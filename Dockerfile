# PEN-STACK 8.0.5 - a reproducible image for the genome-writing science stack.
# Portable: no GPU, builds and runs on any machine with Docker.
#
#   docker build -t pen-stack:8.0.5 .
#   docker run --rm pen-stack:8.0.5                  # reproduce the committed-data results (make repro)
#   docker run --rm pen-stack:8.0.5 pytest -q        # run the full test suite
#   docker run --rm pen-stack:8.0.5 pen-stack info   # stack status
#
# This installs the core package with its test and benchmark dependencies - the exact set the CI runs and
# the same one verified end to end on a clean clone. The one non-pip system dependency is libgomp1, the
# OpenMP runtime that LightGBM links against.
#
# Optional heavier layers (add on top as needed; some are large or externally licensed):
#   pip install pen-stack[bio]      genome-ops libraries (pyBigWig, pysam, pybedtools, biopython, ViennaRNA)
#   pip install pen-stack[server]   the REST API (fastapi, uvicorn)
#   pip install pen-stack[bridge]   the bridge RNA designer (install in its own environment; its transitive
#                                   pins do not co-resolve with [bio] under pip)
# Components whose optional backend is absent (the foundation-model oracles, the netMHC binaries) return an
# "not available" rather than crashing, in keeping with the no-fabrication invariant.

FROM python:3.12-slim

LABEL org.opencontainers.image.title="PEN-STACK" \
      org.opencontainers.image.version="8.0.5" \
      org.opencontainers.image.source="https://github.com/ahmedanees-m/pen-stack" \
      org.opencontainers.image.description="Open infrastructure for genome writing (the Writable Genome)." \
      org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# The only non-pip system dependency: LightGBM's OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 make && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /pen-stack
COPY . .

RUN python -m pip install --upgrade pip && \
    pip install -e ".[dev]"

# Build-time smoke: the package imports and the demo-atlas quickstart runs, or the build fails.
RUN python -c "import pen_stack; print('PEN-STACK', pen_stack.__version__)" && \
    PEN_ATLAS_DIR=data/demo pen-stack writable --gene AAVS1 --ct k562 | head -3

# Default: reproduce the committed-data results (demo atlas, grounding eval, agentic baseline, headline
# metrics) with no download and no API key.
CMD ["make", "repro"]
