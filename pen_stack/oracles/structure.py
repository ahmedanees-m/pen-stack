"""Structure oracles (v4.0, WS-O2), AlphaFold3 / Boltz-2 / Chai-1 / Protenix, with cross-oracle consistency.

Each predictor returns structure confidence (pLDDT-like) under the oracle contract, with the model's native
uncertainty surfaced (1 − pLDDT). Where redundant oracles are available, `consistency()` combines them: their
agreement is a confidence signal and **their disagreement widens the reported interval** (v4.0 Principle 3).
Heavy backends run on-demand (hosted/local GPU) and are cached; absent → deferred / cache replay.
"""
from __future__ import annotations

from pen_stack.oracles import build_result, cache_get, consensus
from pen_stack.oracles.schema import OracleResult

_STRUCT_MODELS = ["alphafold3", "boltz-2", "chai-1", "protenix"]
_BACKEND = {"alphafold3": "alphafold3", "boltz-2": "boltz", "chai-1": "chai_lab", "protenix": "protenix"}


def predict_structure(sequence: str, model: str = "boltz-2") -> OracleResult:
    """Predict a structure's confidence with one model (pLDDT-like). Deferred / cache-replayed if absent."""
    if model not in _STRUCT_MODELS:
        raise ValueError(f"unknown structure model {model!r}; choose from {_STRUCT_MODELS}")
    inputs = {"seq_len": len(sequence), "seq": sequence.upper(), "model": model}
    r = build_result("structure", model, inputs=inputs, available=False,
                     note=f"{model} backend not installed (on-demand hosted/local GPU)")
    hit = cache_get(r.provenance.cache_key)
    if hit is not None:
        return build_result("structure", model, inputs=inputs, value=hit.get("value"),
                            native_uncertainty=hit.get("native_uncertainty"), available=True, cached=True,
                            source="cache", note="replayed from committed oracle cache")
    try:
        __import__(_BACKEND[model])
    except Exception: # noqa: BLE001
        return r
    return build_result("structure", model, inputs=inputs, available=False,
                        note=f"{model} present; wire the predictor for the live pLDDT/PAE value")


def consistency(sequence: str, models: list[str] | None = None) -> OracleResult:
    """Cross-oracle self-consistency over the available structure predictors; divergence widens the interval."""
    models = models or _STRUCT_MODELS
    results = [predict_structure(sequence, m) for m in models]
    out = consensus(results, oracle="structure")
    out.note = (out.note or "") + f" | members tried: {models}"
    return out
