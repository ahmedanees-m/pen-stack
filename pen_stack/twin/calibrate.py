"""Twin calibration, two-sided (v5.9, WS-CAL).

Reports the twin's calibration on held-out (predicted, observed) outcomes WHATEVER the shape: interval coverage
vs nominal, and a skill comparison against a NAIVE baseline (predict the mean) with a bootstrap CI on the MAE
gap. A twin "beats" the baseline only when the CI excludes zero in its favour, otherwise the negative is
reported verbatim. This mirrors the field's own result (Arc VCC): perturbation prediction does not yet
consistently beat naive baselines, and the twin says so rather than hiding it.
"""
from __future__ import annotations

import numpy as np


def _mae(pred, obs) -> float:
    return float(np.mean(np.abs(np.asarray(pred, float) - np.asarray(obs, float))))


def _bootstrap_gap(twin_pred, naive_pred, obs, *, reps: int = 300, seed: int = 0) -> tuple[float, list[float]]:
    """Bootstrap the MAE gap (naive - twin); positive => twin better. Returns mean gap + 95% CI."""
    rng = np.random.default_rng(seed)
    twin_pred, naive_pred, obs = map(lambda a: np.asarray(a, float), (twin_pred, naive_pred, obs))
    n = len(obs)
    gaps = []
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        gaps.append(_mae(naive_pred[idx], obs[idx]) - _mae(twin_pred[idx], obs[idx]))
    lo, hi = np.percentile(gaps, [2.5, 97.5])
    return float(np.mean(gaps)), [round(float(lo), 4), round(float(hi), 4)]


def interval_coverage(intervals, obs) -> dict:
    """Empirical coverage of the prediction intervals vs the observed outcomes."""
    obs = np.asarray(obs, float)
    covered = np.array([lo <= y <= hi for (lo, hi), y in zip(intervals, obs)])
    return {"empirical_coverage": round(float(np.mean(covered)), 4), "n": int(len(obs))}


def calibrate_outcome(predictions, observations, *, intervals=None, reps: int = 300, seed: int = 0) -> dict:
    """Two-sided calibration of the twin against a naive mean baseline. Reports the MAE gap with a
    bootstrap CI (beats-or-not), and interval coverage when intervals are supplied."""
    pred = np.asarray(predictions, float)
    obs = np.asarray(observations, float)
    n = len(obs)
    if n < 3:
        return {"available": False, "n": n, "reason": "too few held-out outcomes to calibrate"}
    naive = np.full(n, float(np.mean(obs)))
    mae_twin, mae_naive = _mae(pred, obs), _mae(naive, obs)
    gap, ci = _bootstrap_gap(pred, naive, obs, reps=reps, seed=seed)
    beats = bool(ci[0] > 0) # CI excludes 0 in the twin's favour
    out = {
        "available": True, "n": n,
        "mae_twin": round(mae_twin, 4), "mae_naive": round(mae_naive, 4),
        "mae_gap_naive_minus_twin": round(gap, 4), "gap_ci": ci,
        "beats_naive_baseline": beats,
        "honest_note": ("twin beats naive (CI excludes 0)" if beats
                        else "twin does NOT beat naive on this data (CI spans 0) - reported, not hidden"),
        "no_fabrication": True,
    }
    if intervals is not None:
        out["interval_coverage"] = interval_coverage(intervals, obs)
    return out
