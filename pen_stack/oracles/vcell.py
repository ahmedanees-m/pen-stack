"""Virtual-cell outcome oracles (v5.9, WS-VCELL) — Arc STATE / scGPT under the v4.0 OracleResult contract.

A perturbation-response prediction is a CANDIDATE (a hypothesis), never a claim. It is OOD-gated: a cell context
or perturbation outside the model's documented validity envelope sets `extrapolating=True` / `in_scope=False`,
because the field's own evidence (Arc's Virtual Cell Challenge) is that perturbation models do not yet
consistently beat naive baselines and do not generalize to unseen contexts. Heavy backends run on-demand and are
cached; absent → deferred / cache replay (the value may be None, never fabricated).
"""
from __future__ import annotations

from pen_stack.oracles import build_result, cache_get
from pen_stack.oracles.schema import OracleResult

# documented in-distribution envelope (representative trained human cell contexts + perturbation kinds).
_IN_DISTRIBUTION_CONTEXTS = {
    "k562", "hepg2", "jurkat", "hek293", "hek293t", "h1_hesc", "h1", "a549", "thp1", "raw264",
    "hela", "mcf7", "ipsc", "pbmc", "cd4_t", "cd8_t", "hspc",
}
_VALID_PERTURBATION_KINDS = {"genetic", "crispr", "knockout", "knockdown", "overexpression",
                             "chemical", "drug", "cytokine"}


def _normalize(s) -> str:
    return str(s or "").strip().lower().replace("-", "").replace(" ", "")


def in_distribution(cell_state: str, perturbation: dict) -> bool:
    """True iff the cell context is a documented trained context AND the perturbation kind is supported."""
    ctx_ok = _normalize(cell_state) in {_normalize(c) for c in _IN_DISTRIBUTION_CONTEXTS}
    kind = _normalize(perturbation.get("kind") or perturbation.get("type"))
    kind_ok = (not kind) or kind in {_normalize(k) for k in _VALID_PERTURBATION_KINDS}
    return bool(ctx_ok and kind_ok)


def predict_response(cell_state: str, perturbation: dict, *, model: str = "state",
                     live: bool = False) -> OracleResult:
    """Virtual-cell outcome oracle (Arc STATE / scGPT). OOD-gated: a context outside the scope card ->
    `extrapolating`, never a confident claim. Cached/deferred when the backend is absent (replay is CI default)."""
    extrap = not in_distribution(cell_state, perturbation)
    inputs = {"cell_state": cell_state, "perturbation": perturbation, "live": bool(live)}
    hit = cache_get(build_result("vcell", model, inputs=inputs).provenance.cache_key)
    if hit is not None:
        return build_result("vcell", model, inputs=inputs, value=hit.get("value"),
                            native_uncertainty=hit.get("native_uncertainty"), available=True, cached=True,
                            source="cache", extrapolating=extrap, in_scope=not extrap,
                            note="replayed from committed oracle cache")
    # backend not wired here -> deferred (value None), but the contract + OOD gate are real
    return build_result("vcell", model, inputs=inputs, value=None, available=False,
                        extrapolating=extrap, in_scope=not extrap,
                        note=(f"{model} virtual-cell backend deferred; OOD={extrap}. "
                              "Perturbation prediction does not yet consistently beat naive baselines (Arc VCC)."))
