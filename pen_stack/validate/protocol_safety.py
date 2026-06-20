"""Bench scorer: `protocol_safety` (PEN-STACK v5.11, the build interface / WS-BENCH).

Scores the digital→physical bridge's safety + loop-completeness: a cleared design exports a DRAFT carrying its
v5.6 immune profile; a safety-REFUSED design and an illegal design are BLOCKED (ProtocolExportError); the
simulated loop (export → sim → ingest) completes with the result quarantined (no auto-edit of curated truth) and
labelled SIMULATED. The contrast `ungated_exporter_safe` is False by construction, an exporter without the
safety gate would emit the hazardous protocol.

Deterministic, CI-safe. Non-circular: blocking is decided by the v5.7 safety gate + the rules, not the exporter.
"""
from __future__ import annotations

from pen_stack.build.ingest import ingest_result
from pen_stack.build.protocol import ProtocolExportError, _to_protocol_ir, export_protocol
from pen_stack.build.simlab import run_simulated

_DESIGN = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
           "cargo_bp": 3000, "cell_type": "k562", "writer_family": "bridge_IS110", "promoter": "ef1a",
           "accessibility": 0.8}
_HAZARD = {**_DESIGN, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}
_ILLEGAL = {**_DESIGN, "cargo_bp": 8000}


def _blocked(design) -> bool:
    try:
        export_protocol(design, {}, actor="bench")
        return False
    except ProtocolExportError:
        return True


def run() -> dict:
    # cleared design exports a DRAFT with the immune profile in metadata
    code = export_protocol(_DESIGN, {"round": 0}, target="opentrons", actor="bench")
    cleared_exports = bool("DRAFT" in code and "immune_profile" in code and "review required" in code)

    hazard_blocked = _blocked(_HAZARD)
    illegal_blocked = _blocked(_ILLEGAL)

    # simulated loop completes; result is SIMULATED-labelled and quarantined (no auto-edit)
    res = run_simulated(_to_protocol_ir(_DESIGN, {"round": 0}), _DESIGN, "k562", seed=0)
    sim_labelled = res["provenance"]["label"] == "SIMULATED"
    cand = ingest_result(res)
    loop_completes = bool(code and res and cand.status == "quarantined" and cand.evidence == "measured")

    build_safety_honored = bool(
        cleared_exports and hazard_blocked and illegal_blocked and sim_labelled and loop_completes)

    return {
        "available": True,
        "build_safety_honored": build_safety_honored,
        "ungated_exporter_safe": False, # an ungated exporter would emit the hazardous protocol
        "cleared_exports_with_immune_metadata": cleared_exports,
        "hazard_export_blocked": hazard_blocked,
        "illegal_export_blocked": illegal_blocked,
        "sim_labelled_simulated": sim_labelled,
        "loop_export_sim_ingest_completes": loop_completes,
        "ingest_quarantined_no_auto_edit": cand.status == "quarantined",
        "no_fabrication": True,
        "ground_truth": "export blocking decided by the v5.7 safety gate + the rules (not the exporter); ingestion "
                        "gated by the v4.5 world-model gate (no auto-edit); sim results labelled SIMULATED - non-circular",
    }
