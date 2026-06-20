"""Virtual-cell outcome oracles (v5.9, WS-VCELL), Arc STATE / scGPT under the v4.0 OracleResult contract.

A perturbation-response prediction is a CANDIDATE (a hypothesis), never a claim. It is OOD-gated: a cell context
or perturbation outside the model's documented validity envelope sets `extrapolating=True` / `in_scope=False`,
because the field's own evidence (Arc's Virtual Cell Challenge) is that perturbation models do not yet
consistently beat naive baselines and do not generalize to unseen contexts. Heavy backends run on-demand and are
cached; absent → deferred / cache replay (the value may be None, never fabricated).
"""
from __future__ import annotations

import os

from pen_stack.oracles import build_result, cache_get, cache_put
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
    key_obj = build_result("vcell", model, inputs=inputs)
    hit = cache_get(key_obj.provenance.cache_key)
    if hit is not None:
        return build_result("vcell", model, inputs=inputs, value=hit.get("value"),
                            native_uncertainty=hit.get("native_uncertainty"), available=True, cached=True,
                            source="cache", extrapolating=extrap, in_scope=not extrap,
                            note="replayed from committed oracle cache")
    # Live hook (uniform with the other oracles): a State *Transition* server can be stood up to predict a
    # perturbation response; if PEN_STACK_VCELL_URL is set + up, use it. No such server ships by default,
    # Arc STATE's SE-600M only EMBEDS cells (needs an scRNA AnnData), while a real perturbation OUTCOME needs
    # the ST model + a reference cell population. So this path normally defers, and we DO NOT fabricate a number.
    url = os.getenv("PEN_STACK_VCELL_URL")
    if os.getenv("PEN_STACK_ORACLE_NET") == "1" and url:
        try:
            import requests
            resp = requests.post(f"{url.rstrip('/')}/predict",
                                 json={"cell_state": cell_state, "perturbation": perturbation},
                                 timeout=float(os.getenv("PEN_STACK_MODEL_TIMEOUT", "300"))).json()
            cache_put(key_obj.provenance.cache_key, {"value": resp})
            return build_result("vcell", model, inputs=inputs, value=resp, available=True, source="local_gpu",
                                extrapolating=extrap, in_scope=not extrap,
                                note="Arc STATE transition server prediction (OOD-gated). Still a candidate hypothesis.")
        except Exception: # noqa: BLE001 - server absent/down → defer
            pass
    # default: deferred (value None), the contract + OOD gate are real; the OUTCOME is a known-unknown
    return build_result("vcell", model, inputs=inputs, value=None, available=False,
                        extrapolating=extrap, in_scope=not extrap,
                        note=(f"{model} perturbation-OUTCOME deferred; OOD={extrap}. The Arc STATE model is "
                              "installable (`pip install arc-state`; SE-600M embeds cells), but a trustworthy "
                              "perturbation response needs the State-Transition model + a reference scRNA "
                              "population, and even SOTA does not yet consistently beat naive baselines (Arc VCC), "
                              "so the magnitude stays a known-unknown rather than a fabricated number."))
