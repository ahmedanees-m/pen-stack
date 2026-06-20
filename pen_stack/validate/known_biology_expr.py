"""Known-biology recovery for the v6.7 position-effect model (WS-V).

The model should REDISCOVER position-effect biology without it being hard-coded: raising H3K9me3 (constitutive
heterochromatin) at a site should RAISE the silencing probability and LOWER predicted expression; raising H3K27ac
(active chromatin) should do the opposite. This is a directional sanity check on the learned function, not a
performance claim.
"""
from __future__ import annotations

import pandas as pd


def _probe(model, overrides: dict) -> tuple[float, float]:
    base = {f: 0.30 for f in model.features}
    cassette = next(iter(model.cassette_means), "_")
    row = pd.DataFrame([{**base, **{k: v for k, v in overrides.items() if k in model.features}, "cassette": cassette}])
    return float(model.predict_expression(row)[0]), float(model.predict_silenced(row)[0])


def heterochromatin_silencing(model) -> dict:
    """H3K9me3 low vs high (other marks fixed): expect silencing up, expression down with heterochromatin."""
    e_lo, p_lo = _probe(model, {"H3K9me3": 0.05})
    e_hi, p_hi = _probe(model, {"H3K9me3": 0.95})
    return {"p_silenced_low_het": round(p_lo, 4), "p_silenced_high_het": round(p_hi, 4),
            "expr_low_het": round(e_lo, 4), "expr_high_het": round(e_hi, 4),
            "silencing_increases_with_heterochromatin": bool(p_hi > p_lo),
            "expression_decreases_with_heterochromatin": bool(e_hi < e_lo)}


def active_chromatin_expression(model) -> dict:
    """H3K27ac low vs high: expect expression up, silencing down with active chromatin (if the mark is present)."""
    if "H3K27ac" not in model.features:
        return {"available": False}
    e_lo, p_lo = _probe(model, {"H3K27ac": 0.05})
    e_hi, p_hi = _probe(model, {"H3K27ac": 0.95})
    return {"available": True, "expr_low_active": round(e_lo, 4), "expr_high_active": round(e_hi, 4),
            "expression_increases_with_active_chromatin": bool(e_hi > e_lo),
            "silencing_decreases_with_active_chromatin": bool(p_hi < p_lo)}
