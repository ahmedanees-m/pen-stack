# PEN-STACK v6.2, the Web Platform image (one container: built frontend + the FastAPI gateway over the engine).
# Multi-stage so the host Node version is irrelevant: stage 1 builds the React/Vite frontend with Node 20, stage
# 2 is a slim Python that serves the gateway and the built dist/. The LLM (Ollama) runs as a SEPARATE service
# (see docker-compose.yml), this image never bundles a model; if Ollama is unreachable the gateway degrades to
# the deterministic narrator, so the container is useful on its own.

# ---- stage 1: build the frontend ---------------------------------------------------------------------
FROM node:20-alpine AS frontend
WORKDIR /web
COPY web/package.json ./
RUN npm install --no-audit --no-fund
COPY web/ ./
RUN npm run build # -> /web/dist

# ---- stage 2: the Python gateway ---------------------------------------------------------------------
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/work PIP_NO_CACHE_DIR=1
# libgomp1 is the OpenMP runtime LightGBM needs at import time.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /work
# install the engine + server extra first (better layer caching), then copy the source.
COPY pyproject.toml README.md ./
COPY pen_stack/ ./pen_stack/
RUN pip install ".[server]"
# v6.4: the AlphaGenome client so the hosted variant-effect oracle is callable when keys + PEN_STACK_ORACLE_NET=1
# are provided (Evo2 needs only `requests`, already present). Live execution stays opt-in at runtime.
RUN pip install alphagenome
# the rest of the repo (configs, benchmarks for the Challenge routes, examples) + the built frontend.
COPY . /work
COPY --from=frontend /web/dist /work/web/dist
EXPOSE 8000
CMD ["uvicorn", "pen_stack.web.server:app", "--host", "0.0.0.0", "--port", "8000"]
