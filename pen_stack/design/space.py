"""Candidate-space generation for the generative designer (v5.8, WS-GEN support).

`candidate_space(goal)` enumerates candidate end-to-end writing systems — writer x site x cargo x delivery —
by wrapping the validated Phase-3 inverse-design planner (`plan_write`) for the site x writer x scores, then
pairing each with every *compatible* delivery vehicle from the curated palette (cargo fits the vehicle
capacity). Every candidate carries the planner's grounded scores (safety / p_durable / writer_activity) so the
verifier-as-discriminator can compute a calibrated confidence and the v5.6 immune profile downstream.

Atlas-dependent: when the Phase-1 writability atlas is absent (e.g. a bare laptop checkout), `plan_write`
yields nothing and `candidate_space` returns []. The discriminator/Pareto logic is independent of the atlas and
is exercised on explicit candidates (tests/bench fixtures); the atlas path runs on the VM/with data.
"""
from __future__ import annotations

from typing import Any

from pen_stack.planner.delivery_vehicles import names as _vehicle_names
from pen_stack.planner.delivery_vehicles import vehicle as _vehicle

# edit-intent -> write_type (the router/verifier dispatches on write_type)
_INTENT_WRITE_TYPE = {
    "safe_harbour_insertion": "insertion",
    "high_durability_insertion": "insertion",
    "knock_in_with_disruption": "insertion",
    "landing_pad_insertion": "landing_pad",
    "regulatory_element_excision": "excision",
    "repeat_excision": "excision",
    "regulatory_rewrite": "regulatory_rewrite",
}


def _compatible_vehicles(cargo_bp: int) -> list[str]:
    """Vehicles whose curated cargo capacity fits the cargo (capacity None = no DNA-packaging limit)."""
    out = []
    for n in _vehicle_names():
        cap = (_vehicle(n) or {}).get("cargo_capacity_bp")
        if cap is None or cargo_bp <= cap:
            out.append(n)
    return out


def deliverability_score(vehicle_name: str, cargo_bp: int) -> float:
    """Grounded deliverability proxy: capacity headroom (more spare capacity = more deliverable),
    clipped to [0,1]. Vehicles with no packaging limit score 1.0. NOT a clinical claim."""
    cap = (_vehicle(vehicle_name) or {}).get("cargo_capacity_bp")
    if cap is None:
        return 1.0
    if cargo_bp > cap:
        return 0.0
    return max(0.0, min(1.0, (cap - cargo_bp) / cap))


def candidate_space(goal: dict, *, n: int = 200, k: int = 8) -> list[dict[str, Any]]:
    """Enumerate candidate designs for a goal {gene, intent, cargo_bp, cell_type}. Each candidate is a plain
    dict consumable by `verify()` and carries the planner's grounded scores. Returns [] if the atlas is absent."""
    gene = goal["gene"]
    intent = goal.get("intent") or goal.get("edit_intent") or "safe_harbour_insertion"
    cargo_bp = int(goal.get("cargo_bp") or goal.get("payload_bp") or 3000)
    ct = goal.get("cell_type") or goal.get("ct") or "k562"
    write_type = _INTENT_WRITE_TYPE.get(intent, "insertion")

    from pen_stack.planner.pipeline import plan_write
    try:
        plans = plan_write(gene, intent, cargo_bp, ct, k=k)
    except Exception:                       # atlas/data absent -> no candidates (discriminator/Pareto unaffected)
        return []

    vehicles = _compatible_vehicles(cargo_bp)
    cands: list[dict] = []
    for p in plans:
        for veh in vehicles:
            cands.append({
                "write_type": write_type, "gene": gene, "chrom": p["site"]["chrom"],
                "edit_intent": intent, "writer_family": p["writer"], "cargo_bp": cargo_bp,
                "cell_type": ct, "delivery_vehicle": veh,
                # grounded planner scores (model_extra) -> verify() calibrated confidence + downstream:
                "safety": p["safety"], "p_durable": p["durability"], "writer_activity": p["writer_activity"],
                "on_target": p["on_target"], "reachability_tier": p.get("reachability_tier"),
                "deliverability": deliverability_score(veh, cargo_bp),
                "_planner_score": p["score"],
                "provenance": {**p.get("provenance", {}), "candidate_space": "v5.8 plan_write x delivery palette"},
            })
            if len(cands) >= n:
                return cands
    return cands
