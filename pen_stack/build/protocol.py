"""Safety-gated protocol export, the digital→physical bridge (v5.11, WS-PROTO).

A cleared, legal design becomes a runnable protocol, emitted as a reviewed DRAFT carrying its v5.6 immune-risk
profile in the metadata, never auto-run, and refused outright if the v5.7 safety gate flags it. Protocols are
drafts for human/lab review, never auto-executed.
"""
from __future__ import annotations

import json

from pen_stack.verify import verify

_TARGETS = ("opentrons", "pylabrobot", "cloudlab")


class ProtocolExportError(RuntimeError):
    """Raised when a design cannot be exported (safety-refused or illegal)."""


def _to_protocol_ir(design: dict, experiment: dict) -> dict:
    """Minimal, platform-agnostic protocol intermediate representation (a DRAFT plan, not lab-tuned steps)."""
    return {
        "assay": experiment.get("assay", "cassette_expression_readout"),
        "cell_type": design.get("cell_type", "k562"),
        "delivery_vehicle": design.get("delivery_vehicle"),
        "writer_family": design.get("writer_family"),
        "cargo_bp": design.get("cargo_bp"),
        "round": experiment.get("round"),
        "steps": ["seed cells", "prepare delivery vehicle + cargo", "deliver", "incubate", "assay readout"],
    }


def _emit_opentrons(ir: dict) -> str:
    return (f"# Opentrons Python Protocol API v2 (DRAFT)\nmetadata = {{'apiLevel': '2.15'}}\n"
            f"def run(protocol):\n"
            f" # assay: {ir['assay']} | cell_type: {ir['cell_type']} | vehicle: {ir['delivery_vehicle']}\n"
            f" # steps: {ir['steps']}\n"
            f" pass # DRAFT - human/lab review required; fill in labware + liquid handling\n")


def _emit_pylabrobot(ir: dict) -> str:
    return (f"# PyLabRobot protocol (DRAFT)\nfrom pylabrobot.liquid_handling import LiquidHandler\n"
            f"async def run(lh: LiquidHandler):\n"
            f" # assay: {ir['assay']} | vehicle: {ir['delivery_vehicle']} | steps: {ir['steps']}\n"
            f" ... # DRAFT - human/lab review required\n")


def _emit_cloudlab(ir: dict) -> str:
    return ("# Cloud-lab protocol request (DRAFT)\n"
            + json.dumps({"assay": ir["assay"], "cell_type": ir["cell_type"], "steps": ir["steps"],
                          "status": "DRAFT - human/lab review required"}, indent=2) + "\n")


_EMITTERS = {"opentrons": _emit_opentrons, "pylabrobot": _emit_pylabrobot, "cloudlab": _emit_cloudlab}


def _stamp_draft(code: str, *, provenance: dict) -> str:
    header = ("# ============================================================\n"
              "# DRAFT, human/lab review required. NOT auto-executed.\n"
              f"# provenance: {json.dumps(provenance, default=str)}\n"
              "# ============================================================\n")
    return header + code


def export_protocol(design: dict, experiment: dict, *, target: str = "opentrons",
                    actor: str = "anonymous") -> str:
    """Cleared design + experiment -> a runnable protocol DRAFT, with the v5.6 immune-risk profile in the
    metadata. HARD GATE: refuses anything the safety gate flags, or any illegal design."""
    if target not in _TARGETS:
        raise ProtocolExportError(f"unknown target {target!r}; choose from {_TARGETS}")
    v = verify(dict(design), actor=actor)
    if v.safety is not None and v.safety.decision == "refuse":
        raise ProtocolExportError(f"export blocked by safety gate: {v.safety.reason}")
    if v.legal is not True:
        raise ProtocolExportError(f"export blocked: design not legal ({v.summary()})")
    ir = _to_protocol_ir(design, experiment)
    code = _EMITTERS[target](ir)
    return _stamp_draft(code, provenance={
        "verify": v.summary(), "safety": (v.safety.decision if v.safety else None),
        "immune_profile": v.immune_profile, # v5.6 metadata travels with the protocol
        "target": target, "actor": actor,
        "note": "immune profile is a screen carrying its known-unknowns, not a patient prediction"})
