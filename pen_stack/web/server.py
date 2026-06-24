"""The PEN-STACK web gateway (v6.2, WS-BACKEND), one typed HTTP surface over the engine + the grounded chat.

This is a *gateway, not a rewrite*. It mounts the v6.1 AI-surface app (``/verify``, ``/safety``, ``/immune``,
``/generate``, ``/predict``, ``/suggest``, ``/session``, ``/capabilities``, ``/scope`` + the atlas/crosslink
routes) and adds the human-facing pieces: the grounded ``/chat`` (and a streaming ``/chat/stream``), CORS for
the React frontend, and static serving of the built frontend when present. Every quantity still comes from the
engine; the chat's LLM only narrates (see ``pen_stack.web.llm``).

Run: ``uvicorn pen_stack.web.server:app --host 0.0.0.0 --port 8000`` (needs the ``server`` extra).
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
except ImportError as e: # pragma: no cover - server extra optional
    raise ImportError("FastAPI not installed: pip install 'pen-stack[server]'") from e

from pen_stack import __version__
from pen_stack.server.api import app as _engine_app # the v6.1 typed engine surface (reused verbatim)


def _require_message(req: dict) -> str:
    msg = (req or {}).get("message")
    if not isinstance(msg, str) or not msg.strip():
        raise HTTPException(422, "field 'message' is required and must be a non-empty string")
    return msg

app = FastAPI(
    title="PEN-STACK, Web Platform",
    version=__version__,
    description=("The human surface for genome writing: a grounded co-scientist chat + every engine feature, "
                 "with provenance-first UX (confidence bands, provenance, scope ledger, safety badges). The LLM narrates "
                 "and routes but never sources a number."),
)

# CORS, the Vite dev server (5173) and the bundled static frontend both talk to this gateway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # self-hosted, single-tenant; tighten via PEN_STACK_CORS if deployed
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the entire v6.1 engine surface under the same app so the frontend has ONE base URL/one OpenAPI.
app.mount("/api", _engine_app)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "surface": "web"}


@app.post("/chat", tags=["v6.2 co-scientist"])
def chat_route(req: dict) -> dict:
    """The grounded co-scientist: the LLM narrates over ENGINE tool outputs; every number comes from the tools
    and the grounding guard strikes any the model invents. Body: {message, history?}. Returns
    {reply, tool_results, grounded, backend}."""
    from pen_stack.web.llm import grounded_reply

    return grounded_reply(_require_message(req), history=req.get("history", []),
                          allow_llm=bool(req.get("allow_llm", True)))


@app.post("/chat/stream", tags=["v6.2 co-scientist"])
def chat_stream_route(req: dict) -> StreamingResponse:
    """Same grounded reply, streamed as Server-Sent Events. The reply is computed grounded first (guard already
    applied), then emitted word-by-word so the UI can render progressively; a final event carries the dossier."""
    from pen_stack.web.llm import grounded_reply

    result = grounded_reply(_require_message(req), history=req.get("history", []),
                            allow_llm=bool(req.get("allow_llm", True)))

    def _events():
        for word in result["reply"].split(" "):
            yield f"data: {json.dumps({'token': word + ' '})}\n\n"
        yield ("event: done\ndata: " + json.dumps(
            {"tool_results": result.get("tool_results"), "backend": result["backend"],
             "grounded": result["grounded"], "mode": result.get("mode"),
             "provenance": result.get("provenance"), "angles": result.get("angles"),
             "facts": result.get("facts"), "sources": result.get("sources"),
             "status": result.get("status")}, default=str) + "\n\n")

    return StreamingResponse(_events(), media_type="text/event-stream")


# Serve the built React frontend (web/dist) when present, one-command self-host serves UI + API together.
_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
if _DIST.exists(): # pragma: no cover - only when the frontend has been built
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
