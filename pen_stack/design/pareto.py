"""Multi-objective Pareto frontier with a GROUNDED immune-risk axis (v5.8, WS-PARETO).

Returns the non-dominated set of generated candidates over the design tradeoff axes. The `neg_immune_risk` axis
is sourced from the v5.6 immune profile (no longer a placeholder): it is the WORST-CASE per-axis in-scope score
(lower score = higher risk) with the per-axis uncertainty carried as a band — never collapsing the profile into
one confident number, and keeping the in-vivo magnitude scope-flagged. Unknown axes enter as flagged bounds,
never fabricated points; the per-axis profile remains the source of truth.
"""
from __future__ import annotations

from typing import Any

# higher is better for every axis (neg_* are already oriented so that higher = better).
AXES = ("efficiency", "durability", "safety", "deliverability", "neg_immune_risk", "neg_cost")
_COST_CAP_BP = 10000


def neg_immune_risk(design: dict) -> dict:
    """Aggregate the v5.6 immune profile into ONE Pareto axis WITHOUT collapsing it into a confident number:
    worst-case per-axis in-scope value + the largest per-axis uncertainty as a band. Returns the value (or None
    when no axis is in scope) + the band + which axes were used + the standing in-vivo scope flag."""
    prof = (design.get("immune_profile") or {}).get("axes", {})
    in_scope = {k: a for k, a in prof.items()
                if a.get("in_scope") and a.get("value") is not None}
    worst = min((a["value"] for a in in_scope.values()), default=None)   # lower score = higher risk
    band = max((a.get("uncertainty") or 0.0 for a in in_scope.values()), default=0.0)
    return {"value": worst, "uncertainty": band, "axes_used": sorted(in_scope),
            "scope_flag": "in_vivo_magnitude_unknown"}


def _scores(design: dict) -> dict[str, float | None]:
    cargo = float(design.get("cargo_bp") or 0)
    nir = neg_immune_risk(design)
    return {
        "efficiency": _f(design.get("writer_activity")),
        "durability": _f(design.get("p_durable")),
        "safety": _f(design.get("safety")),
        "deliverability": _f(design.get("deliverability")),
        "neg_immune_risk": nir["value"],
        "neg_cost": max(0.0, 1.0 - min(cargo, _COST_CAP_BP) / _COST_CAP_BP),
    }


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _dominates(a: dict, b: dict) -> bool:
    """`a` dominates `b` iff a is >= on every COMPARABLE axis and strictly > on at least one. Axes that are
    None (unknown) on either design are skipped (a flagged bound never fabricates a winning point)."""
    comparable = [k for k in AXES if a["scores"][k] is not None and b["scores"][k] is not None]
    if not comparable:
        return False
    ge = all(a["scores"][k] >= b["scores"][k] for k in comparable)
    gt = any(a["scores"][k] > b["scores"][k] for k in comparable)
    return ge and gt


def pareto_front(designs: list[dict]) -> list[dict[str, Any]]:
    """Non-dominated set over AXES. Each returned design gets a `scores` dict and a `neg_immune_risk_detail`
    (value + uncertainty band + axes used + in-vivo scope flag). The immune axis is grounded by v5.6."""
    enriched = []
    for d in designs:
        d = {**d, "scores": _scores(d), "neg_immune_risk_detail": neg_immune_risk(d)}
        enriched.append(d)
    front = [d for d in enriched if not any(_dominates(o, d) for o in enriched if o is not d)]
    return front
