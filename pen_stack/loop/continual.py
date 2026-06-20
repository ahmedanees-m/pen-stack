"""Gated, versioned, reversible continual learning, the closed loop (v5.12, WS-CONTINUAL).

Recalibrates the trust layer + the v5.9 twin + the v5.6 immune proxies on ADMITTED outcomes only, never on
un-gated evidence. Every update is versioned and reversible (carries a `rollback_to` pointer), attributable to
the admitted evidence and the approver. High drift widens intervals rather than over-trusting a shifting model.
This is recalibration, NOT full retraining of the foundation models.
"""
from __future__ import annotations

import hashlib
import json
from statistics import mean


def _evidence_digest(admitted_results: list) -> str:
    payloads = [getattr(r, "payload", r) for r in admitted_results]
    return hashlib.sha256(json.dumps(payloads, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _readouts(admitted_results: list) -> list[float]:
    out = []
    for r in admitted_results:
        payload = getattr(r, "payload", r)
        ro = payload.get("readout") if isinstance(payload, dict) else None
        if ro is not None:
            out.append(float(ro))
    return out


def _update_immune_labels(admitted_results: list) -> dict:
    """Immune-measurement results can move a v5.6 axis proxy -> outcome-validated (recorded). Requires an
    admitted measurement that names an immune axis + a CI (v5.6 WS-CALIB rule); else no graduation."""
    graduated = []
    for r in admitted_results:
        payload = getattr(r, "payload", r)
        if isinstance(payload, dict) and payload.get("immune_axis_measured") and payload.get("ci"):
            graduated.append(payload["immune_axis_measured"])
    return {"graduated_to_validated": graduated,
            "note": "graduation requires an admitted immune measurement with a CI (v5.6 WS-CALIB gate)"}


def continual_update(admitted_results: list, *, drift: dict | None = None, approver: str,
                     prev_version: str | None = None) -> dict:
    """Recalibrate trust + twin + immune proxies on ADMITTED outcomes only. Versioned + reversible. High drift
    widens intervals rather than over-trusting a shifting model."""
    if not admitted_results:
        return {"updated": False, "reason": "no admitted evidence", "rollback_to": prev_version}
    readouts = _readouts(admitted_results)
    calibration = {"mean_readout": round(mean(readouts), 4) if readouts else None, "n": len(readouts)}
    interval_inflation = 1.0
    if drift and drift.get("severity") == "high":
        interval_inflation = 1.0 + min(1.0, drift.get("ece", 0.0)) # widen, don't over-trust
    imm_lbls = _update_immune_labels(admitted_results)
    version = f"v{_evidence_digest(admitted_results)}"
    return {
        "updated": True, "version": version, "by": approver,
        "n_evidence": len(admitted_results), "calibration": calibration,
        "interval_inflation": round(interval_inflation, 4), "immune_labels": imm_lbls,
        "rollback_to": prev_version, # reversible: revert to the prior belief version
        "note": "recalibration only (not foundation-model retraining); admitted-evidence-only; versioned+reversible",
    }
