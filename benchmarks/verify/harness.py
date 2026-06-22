"""Verify-Bench (v6.12 PEN-VERIFY, F-WS5): the verification-service gates as a reportable bench.

Reports the three Stage F gates from committed, deterministic code (no external data, CI-safe):
  1. rule spec parity: the exported machine-readable rule spec reproduces the live ruleset at 0 mismatches,
     every rule names a registered evaluator and carries a DOI or a note (F-G1).
  2. proof-object repair: a design that fails on legality is repaired using ONLY the proof object and
     re-verifies to a pass, and the three axes are reported separately (never collapsed).
  3. biosecurity standards concordance: the Guardian decisions, expressed as Common Mechanism ScreenStatus,
     are concordant with the expected status on the labelled probe set (reported verbatim).
"""
from __future__ import annotations

from typing import Any


def _rule_spec_parity() -> dict[str, Any]:
    from pen_stack.rules.spec import spec_parity
    p = spec_parity()
    p["gate_pass"] = bool(p["parity_0_mismatch"] and p["all_evaluators_registered"] and p["all_rules_cited"])
    return p


def _proof_repair() -> dict[str, Any]:
    from pen_stack.rules import Design
    from pen_stack.verify.proof import repair_from_proof, verify_proof
    # legal except the cargo (8000 bp) exceeds the AAV_single packaging capacity (4700 bp).
    failed = Design(write_type="insertion", installed_att=True, cargo_bp=8000,
                    delivery_vehicle="AAV_single", writer_output_form="DNA")
    p0 = verify_proof(failed)
    repaired = repair_from_proof(failed, p0)
    p1 = verify_proof(repaired)
    return {
        "before_passable": p0.passable,
        "before_legality": p0.axis("legality").status,
        "repair_applied": {"delivery_vehicle": repaired.delivery_vehicle},
        "after_passable": p1.passable,
        "after_legality": p1.axis("legality").status,
        "axes_reported_separately": [a.axis for a in p0.axes],
        "collapsed_is_none": p0.collapsed is None,
        "gate_pass": bool(p0.passable is False and p1.passable is True and p0.collapsed is None
                          and len(p0.axes) == 3),
    }


def _standards_concordance() -> dict[str, Any]:
    from pen_stack.safety.standards import concordance_report
    r = concordance_report()
    r["gate_pass"] = bool(r["n"] > 0 and not r["discordances"])
    return r


def run() -> dict[str, Any]:
    """Run the three Verify-Bench gates and report them with an overall verdict."""
    parity = _rule_spec_parity()
    repair = _proof_repair()
    concord = _standards_concordance()
    return {
        "bench": "Verify-Bench (PEN-VERIFY)",
        "rule_spec_parity": parity,
        "proof_object_repair": repair,
        "standards_concordance": concord,
        "all_gates_pass": bool(parity["gate_pass"] and repair["gate_pass"] and concord["gate_pass"]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
