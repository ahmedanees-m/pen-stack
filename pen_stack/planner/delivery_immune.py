"""Immune-coupled delivery selection (v6.11 PEN-DELIVER, D-WS4).

Fuses the cross-modality deliverability recommendation (Stage D) with the per-axis immune-risk profile (Stage G) and
surfaces the **dose <-> immunogenicity tradeoff** as a VECTOR, never collapsed into one number. The point: a vehicle
that is most deliverable may carry the highest immune liability (e.g. AAV: efficient in vivo, but pre-existing NAbs +
capsid CD8 + dose-dependent innate sensing), and that tension must be visible, not hidden.

the immune axes are population-level proxies (Stage G); the realized in-vivo magnitude / patient titer is a
declared known-unknown. The dose<->immune tradeoff is informative, NOT a clinical dosing directive.
"""
from __future__ import annotations


def _highest_risk_axis(design: dict) -> dict | None:
    """The in-scope immune axis with the LOWEST score (= highest risk) from the Stage G profile, with its value."""
    from pen_stack.planner.immune_profile import immune_profile
    axes = immune_profile(dict(design)).get("axes", {})
    in_scope = {k: a for k, a in axes.items() if a.get("in_scope") and a.get("value") is not None}
    if not in_scope:
        return None
    k = min(in_scope, key=lambda x: in_scope[x]["value"])
    return {"axis": k, "score": in_scope[k]["value"], "note": in_scope[k].get("note")}


def delivery_immune_tradeoff(cargo_form: str, cargo_bp: int | None = None, target_tissue: str | None = None,
                             *, writer_family: str | None = None, serotype: str | None = None,
                             safety_weight: float = 0.5, in_vivo: bool | None = None) -> dict:
    """Rank deliverability AND attach each vehicle's Stage G immune profile, surfacing the dose<->immune tradeoff per
    vehicle as a vector. Never collapses deliverability and immunogenicity into one score."""
    from pen_stack.planner.delivery_predict import recommend_delivery_plus
    rec = recommend_delivery_plus(cargo_form, cargo_bp, target_tissue, safety_weight=safety_weight, in_vivo=in_vivo)
    coupled = []
    for prof in rec.get("ranked", []) or rec.get("eligible", []) or []:
        veh = prof.get("vehicle") or prof.get("name")
        if not veh:
            continue
        design = {"delivery_vehicle": veh, "serotype": serotype, "writer_family": writer_family}
        risk = _highest_risk_axis(design)
        coupled.append({
            "vehicle": veh,
            "deliverability_balance": prof.get("balance"),
            "efficacy_score": prof.get("efficacy_score"),
            "immune_highest_risk_axis": risk, # the dominant immune liability (Stage G)
            "tradeoff": (f"deliverability {prof.get('balance')} vs dominant immune liability "
                         f"'{risk['axis']}' (score {risk['score']})" if risk else
                         "deliverability ranked; immune axes abstain for this vehicle"),
        })
    return {
        "cargo_form": cargo_form, "cargo_bp": cargo_bp, "target_tissue": target_tissue,
        "serotype_tropism_prior": rec.get("serotype_tropism_prior"),
        "coupled": coupled,
        "collapsed_score": None, # deliberately None, dose<->immune is a vector, NEVER fused
        "dose_immune_note": ("AAV/viral vehicles are efficient in vivo but carry the highest immune liability "
                             "(pre-existing NAbs, capsid CD8, dose-dependent innate sensing); higher dose raises both "
                             "transduction AND immunogenicity. The tradeoff is surfaced per vehicle, never collapsed."),
        "known_unknowns": ["in_vivo_immunogenicity_magnitude", "patient_specific_titer", "realized_dose_response"],
        "honesty": "immune axes are population-level proxies (Stage G); realized magnitude/titer is a known-unknown; "
                   "this is decision-support, NOT a clinical dosing directive. No collapsed score.",
        "no_fabrication": True,
    }
