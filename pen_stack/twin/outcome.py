"""Write-outcome prediction, the digital twin (v5.9, WS-OUTCOME).

Fuses what MECHANISM computes (cassette expression), what an IN-DISTRIBUTION virtual-cell model supports
(deferred/cache-replayed, OOD-gated), and the v5.6 IMMUNE profile (sourced, never invented) into a single
prediction with an interval that WIDENS under OOD and an explicit boundary at phenotype. The twin is a
hypothesis engine: every output is a CANDIDATE with an interval; phenotype, in-vivo behaviour, immunogenicity
magnitude, and durability beyond the computable stay scope-flagged.
"""
from __future__ import annotations

_BASE_HALF_WIDTH = 0.20 # heuristic band on the fused estimate (NOT a trained conformal interval)
_OOD_INFLATION = 1.6 # OOD widens the interval rather than over-trusting an extrapolating model


def _chromatin(cell_state: str, design: dict) -> dict:
    """Chromatin context for the mechanistic model. Uses a supplied accessibility if present, else neutral 1.0
    (and flags that a full epigenome was not supplied)."""
    acc = design.get("accessibility")
    if acc is None and isinstance(design.get("chromatin_ctx"), dict):
        acc = design["chromatin_ctx"].get("accessibility")
    return {"accessibility": float(acc) if acc is not None else 1.0,
            "accessibility_supplied": acc is not None}


def _as_perturbation(design: dict) -> dict:
    return {"kind": design.get("perturbation_kind") or "genetic",
            "target": design.get("gene"), "write_type": design.get("write_type")}


def _in_vivo(design: dict) -> bool:
    veh = design.get("delivery_vehicle")
    if not veh:
        return False
    from pen_stack.planner.delivery_vehicles import vehicle as _veh
    return bool((_veh(veh) or {}).get("in_vivo"))


def predict_outcome(design: dict, cell_state: str) -> dict:
    from pen_stack.oracles.vcell import predict_response
    from pen_stack.twin.mechanistic import cassette_expression
    from pen_stack.twin.position_effect import predict_stage_h

    mech = cassette_expression(design, _chromatin(cell_state, design))
    # v6.7 PEN-EXPRESS: when a chromatin CONTEXT is supplied and the trained artifact is present, Stage H serves
    # the learned, TRAINED-CONFORMAL position-effect model (interval + p_silenced + OOD widening). Without a
    # context (or the artifact) this is None and the closed-form heuristic below stands, backward compatible.
    learned = predict_stage_h(design)
    vc = predict_response(cell_state, _as_perturbation(design), model="state")
    imm = None
    if design.get("delivery_vehicle"):
        from pen_stack.planner.immune_profile import immune_profile
        imm = immune_profile(design)

    # fuse: the computable mechanistic estimate is the backbone; the VC model adds an in-distribution response
    # estimate ONLY when available (deferred backend -> None, never fabricated).
    est = mech["relative_expression"]
    vc_value = vc.value if (vc.available and not vc.extrapolating and vc.value) else None

    scope = list(mech["scope_flags"]) + ["in_vivo_magnitude_unknown"]
    if vc.extrapolating:
        scope.append("vcell_OOD")

    # in-vivo durability MAY be conditioned on pre-existing NAb (the GROUNDED v5.6 axis; no invented numbers)
    conditioned_note = None
    if imm is not None and _in_vivo(design):
        nab = (imm.get("axes", {}).get("preexisting_nab") or {})
        if nab.get("in_scope") and nab.get("value") is not None:
            est = round(est * float(nab["value"]), 4) # higher NAb score = less pre-existing immunity
            conditioned_note = f"in-vivo durability conditioned on grounded pre-existing NAb axis ({nab['value']})"

    half = _BASE_HALF_WIDTH * (_OOD_INFLATION if vc.extrapolating else 1.0)
    lo, hi = round(max(0.0, est - half), 4), round(est + half, 4)

    predicted = {"relative_expression": est, "vcell_response": vc_value, "units": mech["units"]}
    interval_kind = ("heuristic band (widens under OOD); NOT a trained conformal interval - no public "
                     "perturbation-outcome calibration set (Arc VCC: models do not yet beat naive baselines)")
    if learned is not None:
        # the learned model serves: surface its trained-conformal value + a relative rescale alongside the
        # mechanistic estimate; the mechanistic `interval` is retained for the relative-scale contract.
        predicted["relative_expression_learned"] = learned.get("relative_expression_learned")
        predicted["learned_log2_expression"] = learned.get("predicted_log2_expression")
        interval_kind = ("Stage H trained-conformal: see position_effect.interval_log2 (split-conformal on TRIP "
                         "supervision, OOD-widened). Mechanistic relative interval retained below.")
        scope = scope + ["stage_h_learned_trained_conformal"]

    return {
        "predicted_outcome": predicted,
        "interval": [lo, hi],
        "interval_kind": interval_kind,
        "position_effect": learned, # learned trained-conformal block (or None)
        "stage_h_mode": "learned_trained_conformal" if learned is not None else "heuristic",
        "immune_outcome": imm, # v5.6 profile (or None if no vehicle)
        "extrapolating": bool(vc.extrapolating),
        "conditioned_on_preexisting_nab": conditioned_note,
        "scope_flags": scope,
        "provenance": {"mechanistic": mech["assumptions"], "vcell": vc.provenance.model_dump()
                       if hasattr(vc.provenance, "model_dump") else str(vc.provenance),
                       "immune": "v5.6 profile" if imm is not None else None,
                       "position_effect": (learned["provenance"] if learned else None)},
        "output_kind": "candidate",
        "no_fabrication": True,
    }
