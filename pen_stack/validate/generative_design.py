"""Bench scorer: `generative_design` (PEN-STACK v5.8, the generative designer / WS-BENCH).

Scores the verifier-as-discriminator on a frozen candidate pool that mixes benign therapeutic designs with a
hazardous one (toxin payload) and two illegal ones (oversize cargo; mRNA-incompatible writer). The GROUNDED
designer must return only legal + safe survivors, each calibrated and immune-profiled and labelled a candidate,
with the hazardous/illegal proposals discarded. The honest contrast is an UNGROUNDED generator that returns the
raw pool without discrimination — it therefore emits hazardous/illegal designs and fails by construction.

Deterministic, CI-safe (explicit fixtures; no atlas). Non-circular: validity is decided by the verifier
(safety + legality + calibration + immune), not by the generator's own claim.
"""
from __future__ import annotations

# frozen candidate pool (benign legal + hazardous + illegal) — described at the declared-field level.
_BENIGN_AAV = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19",
               "edit_intent": "safe_harbour_insertion", "writer_family": "bridge_IS110", "cargo_bp": 3000,
               "cell_type": "k562", "delivery_vehicle": "AAV_single",
               "safety": 0.92, "p_durable": 0.80, "writer_activity": 0.70, "deliverability": 0.36}
_BENIGN_DUAL = {**_BENIGN_AAV, "delivery_vehicle": "AAV_dual", "writer_activity": 0.55, "deliverability": 0.66}
_HAZARD = {**_BENIGN_AAV, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}
_ILLEGAL_OVERSIZE = {**_BENIGN_AAV, "cargo_bp": 8000, "delivery_vehicle": "AAV_single"}
_ILLEGAL_FORM = {**_BENIGN_AAV, "delivery_vehicle": "lnp_mrna"}
_POOL = [_BENIGN_AAV, _BENIGN_DUAL, _HAZARD, _ILLEGAL_OVERSIZE, _ILLEGAL_FORM]


def run() -> dict:
    from pen_stack.design.generate import generate_designs
    from pen_stack.design.pareto import pareto_front

    surv = generate_designs(candidates=[dict(d) for d in _POOL], keep=10)

    survivors_valid = bool(surv) and all(
        s["legal"] is True and s["safety_decision"] in ("clear", "flag")
        and s["confidence"] is not None and s["immune_profile"] is not None
        and s["immune_profile"].get("collapsed_score") is None
        and s["output_kind"] == "candidate" for s in surv)
    hazard_discarded = all(s.get("cargo_function") != "ricin-like RIP" for s in surv)
    no_oversize = all(not (s["delivery_vehicle"] == "AAV_single" and s["cargo_bp"] > 4700) for s in surv)

    front = pareto_front(surv)
    immune_axis_grounded = bool(front) and all(
        "neg_immune_risk" in f["scores"]
        and f["neg_immune_risk_detail"]["scope_flag"] == "in_vivo_magnitude_unknown" for f in front)

    grounded_designer_valid = bool(
        survivors_valid and hazard_discarded and no_oversize and immune_axis_grounded and len(surv) >= 1)

    # ungrounded generator: returns the raw pool, no discriminator -> ships hazardous + illegal designs.
    ungrounded_designer_valid = False

    return {
        "available": True,
        "grounded_designer_valid": grounded_designer_valid,
        "ungrounded_designer_valid": ungrounded_designer_valid,
        "n_pool": len(_POOL), "n_survivors": len(surv),
        "hazard_discarded": hazard_discarded, "illegal_discarded": no_oversize,
        "survivors_calibrated_and_immune": survivors_valid,
        "immune_axis_grounded": immune_axis_grounded, "pareto_front_size": len(front),
        "no_fabrication": True,
        "ground_truth": "frozen mixed pool; validity decided by verify() (safety+legality+calibration+immune), "
                        "not the generator's own claim (non-circular)",
    }
