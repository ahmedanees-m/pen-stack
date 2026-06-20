"""Simulated-lab harness, run the closed loop without hardware (v5.11, WS-SIMLAB).

Executes a protocol in silico: samples an "observed" result from the v5.9 twin + measurement noise, clearly
labelled SIMULATED. This lets the closed loop (v5.12) run end-to-end before any hardware exists. Sim outcomes
inherit the twin's limits and NEVER enter the curated world-model as measured truth, they are for development /
loop-validation only.
"""
from __future__ import annotations

import random


def run_simulated(protocol_ir: dict, design: dict, cell_state: str, *, seed: int = 0) -> dict:
    """Execute a protocol in silico: sample an 'observed' readout from the twin + measurement noise. Labelled
    SIMULATED; the loop (export -> sim-run -> ingest) completes without a wet lab."""
    from pen_stack.twin.outcome import predict_outcome
    out = predict_outcome(design, cell_state)
    truth = out["predicted_outcome"]
    rng = random.Random(seed)
    base = truth.get("relative_expression")
    readout = None if base is None else round(base + rng.gauss(0.0, 0.05), 4)
    return {
        "assay": protocol_ir.get("assay", "cassette_expression_readout"),
        "readout": readout,
        "units": truth.get("units"),
        "design_id": design.get("design_id", "design:sim"),
        "confidence": out.get("interval"),
        "provenance": {"source": "simlab", "seed": seed, "label": "SIMULATED",
                       "note": "sampled from the v5.9 twin + measurement noise; NOT measured truth"},
    }
