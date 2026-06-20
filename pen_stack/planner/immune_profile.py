"""Unified per-design immune-risk PROFILE (v5.6, WS-PROFILE).

One object across every immune-risk axis (genotoxicity, CD8 epitope load, innate sensing, pre-existing
anti-vector NAb, anti-PEG), each carrying its OWN value + native uncertainty + scope + WS-CALIB validation
label. The axes are reported as a VECTOR, never fused into a single number, which would fake confidence and
is forbidden (asserted by test). Abstaining axes report ``None``, not a guess. The in-vivo response magnitude
and the patient-specific titer are listed as declared known-unknowns.

This is the "immune-risk screen" the closed-loop arc (v5.7+) consumes, a relative screen across axes,
not a patient-level prediction.
"""
from __future__ import annotations

from pen_stack.planner.antipeg_oracle import antipeg_oracle
from pen_stack.planner.ada_risk import ada_risk
from pen_stack.planner.capsid_epitope_oracle import capsid_epitope_oracle
from pen_stack.planner.genotoxicity_oracle import genotoxicity_oracle
from pen_stack.planner.immune_mhc2 import mhc2_epitope_load, writer_family_to_sequence
from pen_stack.planner.innate_sensing import innate_sensing
from pen_stack.planner.seroprevalence_oracle import seroprevalence_oracle
from pen_stack.validate.immune_calibration import axis_label

# magnitude and patient-level state are NEVER predicted, listed so every consumer sees the boundary.
# v5.6 WS-EXT also registers cd4_mhcii_help / preexisting_capsid_tcell / complement_carpa as known-unknowns
# (configs/known_unknowns.yaml), mechanistically distinct axes PEN-STACK does not model.
KNOWN_UNKNOWNS = ["patient_specific_titer", "in_vivo_response_magnitude", "induced_immunity_post_dose1",
                  "cd4_mhcii_help", "preexisting_capsid_tcell", "complement_carpa"]

# v5.6 WS-EXT, route/dose modifier. Immune-privileged delivery sites (eye, CNS) materially LOWER the realized
# immunogenicity of the SAME vector vs systemic delivery (Streilein 2003, 10.1038/nri1224). This is a
# DOCUMENTED, QUALITATIVE modifier on the realized response, never a fabricated magnitude.
_IMMUNE_PRIVILEGED = {"subretinal", "intravitreal", "intraocular", "cns", "intrathecal", "intracranial",
                      "intraparenchymal", "eye", "retina", "brain"}
ROUTE_MODIFIER_DOI = "10.1038/nri1224" # Streilein 2003, ocular/CNS immune privilege


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
            "note": "DOCUMENTED qualitative modifier on the realized response, NOT a quantified magnitude "
                    "(the magnitude stays a known-unknown)."}

# headline score key inside each oracle's value dict, per axis.
_SCORE_KEY = {"genotoxicity": "genotox_score", "cd8_epitope": "capsid_immune_score",
              "innate": "innate_score", "preexisting_nab": "preexisting_score",
              "anti_peg": "preexisting_antipeg_score"}


def _axis(result, axis: str) -> dict:
    """One axis record: value (headline score or None when abstaining) + native uncertainty + scope + the
    WS-CALIB validation label. Never fabricates, an abstaining oracle yields value None."""
    val = None
    if result.available and result.value:
        val = result.value.get(_SCORE_KEY[axis])
    return {"value": val,
            "uncertainty": result.native_uncertainty,
            "in_scope": result.in_scope,
            "available": result.available,
            "validation": axis_label(axis), # 'mechanistic/population proxy' until WS-CALIB validates
            "scope_card": result.scope_card,
            "note": result.note}


def _proxy_axis(value, note: str, axis: str = "mhc2_writer") -> dict:
    """An axis record for the v6.9 sequence-intrinsic proxies (MHC-II / ADA). Value None = abstained (no writer
    sequence). Population-level proxy until WS-CALIB validates, never a patient magnitude."""
    return {"value": value, "uncertainty": None, "in_scope": value is not None, "available": value is not None,
            "validation": axis_label(axis), "scope_card": axis, "note": note}


def _writer_antigen_card(design: dict) -> dict | None:
    """The WRITER enzyme as a distinct antigen (v6.9 G-WS3): MHC-II epitope load + ADA-risk over the writer's real
    sequence. Returns None when no representative writer sequence is bundled (axis then abstains)."""
    wf = design.get("writer_family") or design.get("writer")
    rec = writer_family_to_sequence(wf) if wf else None
    if not rec or not rec.get("seq"):
        return None
    nm = rec.get("name")
    el = mhc2_epitope_load(rec["seq"], nm) # real NetMHCIIpan-4.0 when cached, else proxy
    ad = ada_risk(rec["seq"], rec.get("origin"), name=nm)
    return {"writer_family": wf, "representative": rec.get("name"), "accession": rec.get("accession"),
            "origin": rec.get("origin"), "is_foreign": rec.get("origin") == "foreign",
            "mhc2_immune_score": el["mhc2_immune_score"], "epitope_density": el["epitope_density"],
            "ada_risk_score": ad["ada_risk_score"], "ada_immune_score": ad["ada_immune_score"],
            "foreignness": ad.get("foreignness"),
            "self_match_human_proteome": ad.get("self_match_human_proteome"),
            "ada_backend": ad.get("backend"), "mhc2_backend": el.get("backend"),
            "note": "the WRITER enzyme scored as a distinct antigen (real NetMHCIIpan-4.0 MHC-II/CD4 + ADA, "
                    "origin-authoritative foreignness with a real human-proteome 9-mer self-match cross-check); "
                    "bacterial/phage writers are foreign -> ADA-driving (Cas9 MHC-II: Simhadri 2021). "
                    "Population-level proxy; realized CD4 response / ADA titer is a known-unknown."}


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

    capsid_cd8 = capsid_epitope_oracle(veh)
    writer_card = _writer_antigen_card(design) # v6.9, the writer enzyme as a distinct antigen

    axes = {
        "genotoxicity": _axis(genotoxicity_oracle(veh), "genotoxicity"),
        "cd8_epitope": _axis(capsid_cd8, "cd8_epitope"), # capsid CD8/MHC-I (v5.3)
        "innate": _axis(innate_sensing(cargo_seq, form), "innate"),
        "preexisting_nab": _axis(seroprevalence_oracle(veh, sero), "preexisting_nab"),
        "anti_peg": _axis(antipeg_oracle(veh, peg), "anti_peg"),
        # v6.9, CD4/MHC-II + ADA over the WRITER enzyme (the dominant immunogenicity driver, previously omitted)
        "mhc2_writer": _proxy_axis(writer_card["mhc2_immune_score"] if writer_card else None,
                                   (writer_card or {}).get("note", "no bundled writer sequence -> abstains"),
                                   "mhc2_writer"),
        "ada_writer": _proxy_axis(writer_card["ada_immune_score"] if writer_card else None,
                                  "ADA-risk (higher ada_immune_score = safer) over the writer enzyme, self-"
                                  "tolerance filtered; population proxy" if writer_card else
                                  "no bundled writer sequence -> abstains", "ada_writer"),
    }

    # writer-as-antigen comparison: for non-viral delivery (no foreign capsid) or a foreign writer outscoring the
    # capsid, the WRITER is the dominant antigen, the v6.9 insight, never collapsed into the other axes.
    dominant = None
    writer_dominant_risk = False
    if writer_card:
        capsid_present = bool(capsid_cd8.available and capsid_cd8.value
                              and (capsid_cd8.value.get("capsid_immune_score") or 1.0) < 1.0)
        writer_risk = writer_card["ada_risk_score"]
        capsid_risk = (1.0 - (capsid_cd8.value or {}).get("capsid_immune_score", 1.0)) if capsid_present else 0.0
        writer_dominant_risk = bool(writer_card["is_foreign"] and (not capsid_present or writer_risk >= capsid_risk))
        dominant = "writer" if writer_dominant_risk else ("capsid" if capsid_present else "writer")

    return {
        "axes": axes,
        "collapsed_score": None, # deliberately None, a profile, never a fused number
        "writer_as_antigen": ({**writer_card, "dominant_antigen": dominant,
                               "writer_dominant_risk": writer_dominant_risk} if writer_card else None),
        "route_modifier": _route_modifier(design.get("route")), # v5.6 WS-EXT documented route modifier (or None)
        "known_unknowns": KNOWN_UNKNOWNS,
        "no_fabrication": True,
        "note": ("relative immune-risk SCREEN across axes (now incl. CD4/MHC-II + ADA over the writer enzyme); each "
                 "axis keeps its own value + uncertainty + scope + validation label; NEVER fused. NOT a patient-"
                 "level prediction. The realized CD4 response / ADA titer / in-vivo magnitude are known-unknowns."),
    }
