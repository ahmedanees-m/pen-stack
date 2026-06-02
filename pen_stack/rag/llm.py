"""Optional LLM phrasing layer for the RAG (Phase 2, §2B).

Reads the single LLM switch (``configs/llm.yaml``) and calls the local Ollama OpenAI-compatible endpoint
to *rephrase* already-grounded facts into fluent prose. It is strictly a presentation layer: it is given
the tool-derived facts and must not introduce numbers or citations. Every quantitative claim and every
citation still comes from the deterministic tool/retrieval path in ``qa.py``.

Graceful by design: if the config, the endpoint, or the model is unavailable, ``phrase()`` returns
``None`` and the caller falls back to the deterministic answer — the contract holds with no LLM at all.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import yaml

_CFG = Path(__file__).resolve().parents[2] / "configs" / "llm.yaml"

_SYSTEM = ("You rephrase already-verified genome-writing facts into one clear paragraph for a wet-lab "
           "scientist. Use ONLY the facts provided. Do NOT invent or alter any number, gene, or citation. "
           "Do not give clinical advice. Keep it under 90 words.")


def load_llm_config(path: str | Path = _CFG) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def available(cfg: dict | None = None, timeout: int = 3) -> bool:
    cfg = cfg or load_llm_config()
    base = cfg.get("api_base", "http://localhost:11434")
    try:
        urllib.request.urlopen(f"{base}/api/tags", timeout=timeout)
        return True
    except Exception:  # noqa: BLE001
        return False


def phrase(facts: str, cfg: dict | None = None, timeout: int = 60) -> str | None:
    """Rephrase grounded facts via Ollama. Returns None on any failure (caller keeps the tool answer)."""
    cfg = cfg or load_llm_config()
    base = cfg.get("api_base", "http://localhost:11434")
    model = str(cfg.get("model", "qwen2.5:7b-instruct")).split("/")[-1]
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": _SYSTEM},
                     {"role": "user", "content": f"Facts:\n{facts}\n\nRephrase as one paragraph."}],
        "stream": False,
        "options": {"temperature": float(cfg.get("temperature", 0.1))},
    }
    try:
        req = urllib.request.Request(f"{base}/api/chat",
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        return data.get("message", {}).get("content", "").strip() or None
    except Exception:  # noqa: BLE001
        return None
