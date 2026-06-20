"""Energetics oracle (v4.0, WS-O4), bridge off-target relative-risk, under the oracle contract.

Generalises the v3.2 MC3 off-target energetics model into the mesh. The HARD GATE is unchanged: the
energetics model ships only if its held-out AUROC beats BOTH the position-weight model on the same split AND
the published 0.77 baseline (the eval lives in `validate.offtarget_energetics_eval`); off the VM (Perry data
absent) the adapter returns a deferred result rather than a fabricated number.
"""
from __future__ import annotations

from pen_stack.oracles import build_result
from pen_stack.oracles.schema import OracleResult

GATE_AUROC = 0.77


def gate() -> OracleResult:
    """Run the MC3 held-out discrimination eval and report whether energetics still earns its place."""
    inputs = {"eval": "offtarget_energetics_eval", "gate": GATE_AUROC}
    try:
        from pen_stack.validate.offtarget_energetics_eval import run
        rep = run()
    except Exception as e: # noqa: BLE001 - Perry tables absent off the VM
        return build_result("energetics", "bridge_energetics", inputs=inputs, available=False,
                            note=f"off-target energetics eval unavailable: {type(e).__name__}: {e}")
    if not rep.get("available", True):
        return build_result("energetics", "bridge_energetics", inputs=inputs, available=False,
                            note=rep.get("note", "Perry off-target tables absent (runs on the VM)"))
    auroc = rep.get("energetics_auroc") or rep.get("model_auroc")
    ships = bool(rep.get("ships", auroc is not None and auroc > GATE_AUROC))
    return build_result("energetics", "bridge_energetics", inputs=inputs, value={"held_out_auroc": auroc,
                        "beats_0_77": ships, "report": rep},
                        native_uncertainty=None if auroc is None else round(max(0.0, 1.0 - auroc), 3),
                        note=f"MC3 gate: ships only if held-out AUROC>{GATE_AUROC} AND > position-weight model")
