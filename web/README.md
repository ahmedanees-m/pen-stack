# PEN-STACK Web Platform (v6.2)

The human surface for genome writing: a **grounded co-scientist** chat plus structured feature pages, over the
same typed v6.1 API the AI surface uses. The LLM narrates and routes; the **engine sources every number**, and a
grounding guard strikes any value the model can't trace to a tool result. Every quantitative output renders with
its **confidence band, provenance, and an explicit ledger of what PEN-STACK can't tell you**.

## One-command self-host (Docker)

From the repo root:

```bash
# optional: hosted-LLM fallback (else fully local via Ollama, or deterministic with no LLM)
export NVIDIA_API_KEY=nvapi-...        # or omit

docker compose up web ollama          # builds the frontend (node:20) + serves the gateway on :8000
docker compose exec ollama ollama pull qwen2.5:7b-instruct   # first run, for LLM narration
```

Then open **http://localhost:8000**. The gateway serves the built frontend and the API from one origin.

- LLM order: **Ollama** (local, free) → **Nemotron** (hosted free tier) → **deterministic narrator** (no LLM).
- Turn the LLM off entirely with `PEN_STACK_NO_LLM=1` — the app still answers, just without the prose layer.

## Develop the frontend

The frontend is React + Vite + Tailwind (built with Node 20; the repo's own Node version doesn't matter for the
Docker path). To iterate locally with hot reload, run the gateway and the Vite dev server side by side:

```bash
uvicorn pen_stack.web.server:app --port 8000        # the API gateway (needs the `server` extra)
cd web && npm install && npm run dev                # Vite on :5173, proxying /api + /chat to :8000
```

## Pages

Co-Scientist · Site Finder · Writer Atlas · Designer · Verify · Delivery & Immunity · Digital Twin · Guardian ·
Experiments · Challenge · Scope & About — each calls the typed API and renders through the honest-UX component
library (`ConfidenceBand`, `ProvenanceChip`, `ScopeLedger`, `SafetyBadge`, `ImmuneProfileCard`).

## Honesty contract

Decision-support, not a clinical directive. The web platform improves **usability and adoption** — it adds no
scientific capability and no validation. The science lives in the engine; the UI only renders what the engine
computes, and never a number the engine didn't.
