"""Drift detection — the closed loop (v5.12, WS-DRIFT).

Compares what the twin PREDICTED against what the experiments OBSERVED. Growing miscalibration => drift => widen
uncertainty and flag, rather than over-trusting a stale model. Covers calibration/residual shift, not every
failure mode.
"""
from __future__ import annotations


def _predicted(design: dict, cell_state: str) -> float | None:
    from pen_stack.twin.outcome import predict_outcome
    v = predict_outcome(design, design.get("cell_state") or cell_state or "k562")
    return v["predicted_outcome"].get("relative_expression")


def _empirical_calibration_error(designs: list, results: list, cell_state: str = "") -> tuple[float, int]:
    errs = []
    for d, r in zip(designs, results):
        pred = _predicted(d, cell_state)
        obs = (r.get("payload", {}) if hasattr(r, "get") else {}).get("readout") if not isinstance(r, dict) else r.get("readout")
        # results may be raw dicts (sim/ingest) or Candidates; read the readout from either
        if obs is None and hasattr(r, "payload"):
            obs = r.payload.get("readout")
        if pred is not None and obs is not None:
            errs.append(abs(float(pred) - float(obs)))
    if not errs:
        return 0.0, 0
    return sum(errs) / len(errs), len(errs)


def _drift_threshold() -> float:
    return 0.20                                   # mean abs predicted-vs-observed error above which we flag drift


def detect_drift(designs: list, results: list, *, cell_state: str = "") -> dict:
    """Predicted (twin) vs observed (results). Growing miscalibration => drift => widen + flag."""
    ece_now, n = _empirical_calibration_error(designs, results, cell_state)
    sev = "high" if ece_now > _drift_threshold() else "low"
    return {"severity": sev, "ece": round(ece_now, 4), "n": n,
            "action": "inflate_intervals" if sev == "high" else "monitor",
            "note": "calibration/residual drift only, not every failure mode"}
