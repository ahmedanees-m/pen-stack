"""ESM3-open model server (PEN-STACK live oracle, local GPU).

A tiny FastAPI wrapper around ESM3-open (EvolutionaryScale `esm3-sm-open-v1`, 1.4B, ungated) so the pen_stack
oracle adapter can call a REAL generative protein-design backend over localhost. The adapter
(`oracles/protein_design.py::esm3_design`) POSTs a (masked) sequence here and gets back a generated protein;
when the service is down the adapter defers (never fabricates). Output is a CANDIDATE.

The model is loaded LAZILY on the first /generate so a bare /health (or an unused service) holds no GPU.
Run (on the VM, in the esm3 image): uvicorn server:app --host 0.0.0.0 --port 9012
"""
from __future__ import annotations

import os
import threading

from fastapi import FastAPI, HTTPException

app = FastAPI(title="ESM3-open model server", version="1.0")
_model = None
_lock = threading.Lock()
_MODEL_NAME = os.getenv("ESM3_MODEL", "esm3-sm-open-v1")


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                import torch
                from esm.models.esm3 import ESM3
                dev = "cuda" if torch.cuda.is_available() else "cpu"
                _model = ESM3.from_pretrained(_MODEL_NAME).to(dev)
    return _model


@app.get("/health")
def health() -> dict:
    import torch
    return {"status": "ok", "model": _MODEL_NAME, "cuda": torch.cuda.is_available(),
            "loaded": _model is not None,
            "device": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")}


@app.post("/generate")
def generate(req: dict) -> dict:
    """Body: {sequence?: str (use '_' for masked positions), length?: int, num_steps?: int, temperature?: 0.7}.
    Returns {sequence, length, backend, num_steps}. A generated protein — a CANDIDATE."""
    from esm.sdk.api import ESMProtein, GenerationConfig
    length = int((req or {}).get("length", 0))
    seq = req.get("sequence") or ("_" * length)
    if not seq:
        raise HTTPException(422, "provide 'sequence' (with '_' masks) or a positive 'length'")
    n_masked = seq.count("_") or len(seq)
    num_steps = int(req.get("num_steps", max(1, n_masked // 2)))
    temp = float(req.get("temperature", 0.7))
    model = _get_model()
    protein = ESMProtein(sequence=seq)
    out = model.generate(protein, GenerationConfig(track="sequence", num_steps=num_steps, temperature=temp))
    gen = getattr(out, "sequence", None)
    if not isinstance(gen, str):
        raise HTTPException(500, "ESM3 returned no sequence")
    return {"sequence": gen, "length": len(gen), "backend": _MODEL_NAME, "num_steps": num_steps,
            "temperature": temp, "prompt_masked": seq.count("_")}
