# Deploying PEN-STACK (self-hosted, one command)

PEN-STACK ships as a `docker-compose` stack - API + Streamlit UI + MCP server + an LLM backend.
Everything can run locally and free; **no paid API is required.**

**Hybrid LLM (one switch, `configs/llm.yaml`).** The agent/RAG/PEN-MONITOR use a strong hosted model for
reasoning/tool-use (default `provider: nvidia`, NVIDIA Nemotron, free, OpenAI-compatible) with automatic
**fallback** to the local Ollama model (`fallback: ollama`), then to a deterministic no-LLM path. To use
the hosted model, provide a key via the `NVIDIA_API_KEY` env var or a gitignored `configs/nvidia_api_key.txt`
(in docker-compose, pass it to the `api`/`ui`/`mcp` services as `NVIDIA_API_KEY`). To run fully local,
set `provider: ollama`. The LLM is non-load-bearing - all numbers/citations come from validated tools.

## Prerequisites
- Docker + Docker Compose, an NVIDIA GPU (16 GB is enough) with the NVIDIA Container Toolkit.
- The project image `penstack:phase1` (or build via `docker/Dockerfile`).

## Bring it up
```bash
docker compose up -d
# first run only - pull the local model once (~4.7 GB):
docker compose exec ollama ollama pull qwen2.5:7b-instruct
```

| Service | URL | What |
|---|---|---|
| API | http://localhost:8000 | REST: `/atlas`, `/crosslink/*`, `/writable`, `/plan`, `/ask` |
| UI | http://localhost:8501 | Streamlit platform (Writable Genome, Writer Atlas, Planner, Ask, **Agent**) |
| MCP | localhost:8765 | Model Context Protocol server (see `docs/MCP.md`) |
| Ollama | http://localhost:11434 | local LLM backing the RAG + agent |

## Data
Mount the Phase-1 writability atlas (`atlas_<ct>.parquet`) under `./data/out/` (fetched from the Zenodo
release) so the Writable Genome, cross-link, and Planner have per-locus data. The Writer Atlas
(`pen_stack/atlas/atlas.parquet`) ships in the image.

## Notes
- The Agent page returns a cited plan with a visible, auditable trace and the decision-support
  disclaimer. If the LLM is unreachable it degrades to the deterministic Planner (no fabrication).
- All numbers come from validated tool calls; the LLM only phrases/orchestrates.
