"""Unified per-design immune-risk PROFILE (v5.6, WS-PROFILE).

One object across every immune-risk axis (genotoxicity, CD8 epitope load, innate sensing, pre-existing
anti-vector NAb, anti-PEG), each carrying its OWN value + native uncertainty + scope + WS-CALIB validation
label. The axes are reported as a VECTOR — never fused into a single number, which would fake confidence and
is forbidden (asserted by test). Abstaining axes report ``None``, not a guess. The in-vivo response magnitude
and the patient-specific titer are listed as declared known-unknowns.

This is the honest "immune-risk screen" the closed-loop arc (v5.7+) consumes — a relative screen across axes,
not a patient-level prediction.
"""
from __future__ import annotations

from pen_stack.planner.antipeg_oracle import antipeg_oracle
from pen_stack.planner.capsid_epitope_oracle import capsid_epitope_oracle
from pen_stack.planner.genotoxicity_oracle import genotoxicity_oracle
from pen_stack.planner.innate_sensing import innate_sensing
from pen_stack.planner.seroprevalence_oracle import seroprevalence_oracle
from pen_stack.validate.immune_calibration import axis_label

# magnitude and patient-level state are NEVER predicted — listed so every consumer sees the boundary.
# v5.6 WS-EXT also registers cd4_mhcii_help / preexisting_capsid_tcell / complement_carpa as known-unknowns
# (configs/known_unknowns.yaml) — mechanistically distinct axes PEN-STACK does not model.
KNOWN_UNKNOWNS = ["patient_specific_titer", "in_vivo_response_magnitude", "induced_immunity_post_dose1",
                  "cd4_mhcii_help", "preexisting_capsid_tcell", "complement_carpa"]

# v5.6 WS-EXT — route/dose modifier. Immune-privileged delivery sites (eye, CNS) materially LOWER the realized
# immunogenicity of the SAME vector vs systemic delivery (Streilein 2003, 10.1038/nri1224). This is a
# DOCUMENTED, QUALITATIVE modifier on the realized response — never a fabricated magnitude.
_IMMUNE_PRIVILEGED = {"subretinal", "intravitreal", "intraocular", "cns", "intrathecal", "intracranial",
                      "intraparenchymal", "eye", "retina", "brain"}
ROUTE_MODIFIER_DOI = "10.1038/nri1224"          # Streilein 2003, ocular/CNS immune privilege


def _route_modifier(route: str | None) -> dict | None:
    if not route:
        return None
    r = str(route).strip().lower()
    privileged = any(k in r for k in _IMMUNE_PRIVILEGED)
    return {"route": route,
            "immune_privileged": privileged,
            "effect": ("immune-privileged site: realized immunogenicity is materially LOWER than systemic "
                       "delivery of the same vector (qualitative)" if privileged
                       else "systemic / non-privileged route: no immune-privilege reduction applied"),
            "doi": "10.1038/nri1224",
            "note": "DOCUMENTED qualitative modifier on the realized response — NOT a quantified magnitude "
                    "(the magnitude stays a known-unknown)."}

# headline score key inside each oracle's value dict, per axis.
_SCORE_KEY = {"genotoxicity": "genotox_score", "cd8_epitope": "capsid_immune_score",
              "innate": "innate_score", "preexisting_nab": "preexisting_score",
              "anti_peg": "preexisting_antipeg_score"}


def _axis(result, axis: str) -> dict:
    """One axis record: value (headline score or None when abstaining) + native uncertainty + scope + the
    WS-CALIB validation label. Never fabricates — an abstaining oracle yields value None."""
    val = None
    if result.available and result.value:
        val = result.value.get(_SCORE_KEY[axis])
    return {"value": val,
            "uncertainty": result.native_uncertainty,
            "in_scope": result.in_scope,
            "available": result.available,
            "validation": axis_label(axis),          # 'mechanistic/population proxy' until WS-CALIB validates
            "scope_card": result.scope_card,
            "note": result.note}


def immune_profile(design: dict) -> dict:
    """Per-design immune-risk profile across all axes. ``design`` keys: ``delivery_vehicle`` (or ``vehicle``),
    ``serotype``, ``cargo_seq``, ``writer_output_form`` (or ``cargo_form``), ``pegylated``.

    Returns the axes vector with per-axis uncertainty + validation label, an explicit ``collapsed_score: None``
    (no fused number), the known-unknowns, and ``no_fabrication: True``."""
    veh = design.get("delivery_vehicle") or design.get("vehicle")
    sero = design.get("serotype")
    cargo_seq = design.get("cargo_seq") or ""
    form = design.get("writer_output_form") or design.get("cargo_form") or ""
    peg = design.get("pegylated")

    axes = {
        "genotoxicity": _axis(genotoxicity_oracle(veh), "genotoxicity"),
        "cd8_epitope": _axis(capsid_epitope_oracle(veh), "cd8_epitope"),
        "innate": _axis(innate_sensing(cargo_seq, form), "innate"),
        "preexisting_nab": _axis(seroprevalence_oracle(veh, sero), "preexisting_nab"),
        "anti_peg": _axis(antipeg_oracle(veh, peg), "anti_peg"),
    }
    return {
        "axes": axes,
        "collapsed_score": None,            # deliberately None — a profile, never a fused number
        "route_modifier": _route_modifier(design.get("route")),   # v5.6 WS-EXT documented route modifier (or None)
        "known_unknowns": KNOWN_UNKNOWNS,
        "no_fabrication": True,
        "note": ("relative immune-risk SCREEN across axes; each axis keeps its own value + uncertainty + scope "
                 "+ validation label; NOT a patient-level prediction. The in-vivo response magnitude and the "
                 "patient-specific titer are declared known-unknowns."),
    }
