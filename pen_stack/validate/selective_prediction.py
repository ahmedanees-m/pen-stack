"""Selective prediction / risk-coverage (Phase 3.2, WS-UQ / UQ3).

Uncertainty is only worth reporting if it is *useful*: predictions the model is confident about should be
more accurate than the ones it is unsure about. The risk-coverage curve is the proof. Sort predictions by
confidence (descending), then sweep the retained fraction (``coverage``) from 1.0 down to a minimum,
abstaining on the least-confident; at each coverage record the accuracy (or risk = 1-accuracy) of what is
kept. If the uncertainty is useful, accuracy **rises** as coverage shrinks (we abstain on the hard cases).

The monotonic-improvement check is the UQ3 acceptance test (G-UQ). A FLAT or non-improving curve is a valid,
reported NEGATIVE result ("uncertainty present but not yet useful"), not a hidden failure.

Also provides plan-level confidence propagation: combine per-axis intervals (safety / durability / activity)
into one plan confidence by Monte-Carlo over the axis intervals (axes assumed independent - stated), so the
Planner can rank and abstain on whole plans.
"""
from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------------------------------------
# risk-coverage curve
# --------------------------------------------------------------------------------------------------
def risk_coverage_curve(confidence, correct, n_points: int = 20, min_coverage: float = 0.1) -> dict:
    """Risk-coverage curve from per-prediction ``confidence`` and boolean ``correct``.

    Returns the curve (coverage, accuracy, risk, n_retained), the area under the risk-coverage curve
    (AURC; lower is better), and ``monotone_improving`` - whether accuracy is non-decreasing as coverage
    decreases (the usefulness test, with a tiny tolerance for ties/noise).
    """
    conf = np.asarray(confidence, float)
    corr = np.asarray(correct, float)
    n = len(conf)
    order = np.argsort(-conf) # most-confident first
    corr_sorted = corr[order]
    cum_acc = np.cumsum(corr_sorted) / np.arange(1, n + 1)

    coverages = np.linspace(1.0, min_coverage, n_points)
    curve = []
    for cov in coverages:
        kk = max(1, int(round(cov * n)))
        acc = float(cum_acc[kk - 1])
        curve.append({"coverage": float(kk / n), "accuracy": acc, "risk": 1.0 - acc, "n_retained": kk})

    # AURC over the realized coverages (trapezoid on risk vs coverage)
    covs = np.array([c["coverage"] for c in curve])
    risks = np.array([c["risk"] for c in curve])
    o = np.argsort(covs)
    _trapz = getattr(np, "trapezoid", getattr(np, "trapz", None)) # numpy>=2.0 renamed trapz->trapezoid
    aurc = float(_trapz(risks[o], covs[o]))

    # monotone-improving: accuracy at low coverage >= accuracy at full coverage, and the trend is
    # non-decreasing as we tighten coverage (allow 1pt tolerance for sampling noise)
    accs_by_tightening = [c["accuracy"] for c in sorted(curve, key=lambda r: -r["coverage"])]
    diffs = np.diff(accs_by_tightening)
    monotone = bool(np.all(diffs >= -0.01))
    improves = bool(accs_by_tightening[-1] - accs_by_tightening[0] > 0.0)
    return {"curve": curve, "aurc": aurc, "n": int(n),
            "accuracy_full_coverage": float(cum_acc[-1]),
            "accuracy_min_coverage": accs_by_tightening[-1],
            "monotone_improving": monotone, "strictly_improves": improves,
            "useful": bool(monotone and improves)}


def selective_accuracy(confidence, correct, coverage: float) -> dict:
    """Accuracy when retaining the top-``coverage`` fraction by confidence (abstaining on the rest)."""
    conf = np.asarray(confidence, float)
    corr = np.asarray(correct, float)
    n = len(conf)
    kk = max(1, int(round(coverage * n)))
    keep = np.argsort(-conf)[:kk]
    return {"coverage": float(kk / n), "n_retained": int(kk),
            "accuracy": float(corr[keep].mean()), "abstained": int(n - kk)}


# --------------------------------------------------------------------------------------------------
# plan-level confidence propagation (per-axis intervals -> plan confidence)
# --------------------------------------------------------------------------------------------------
def propagate_plan_confidence(axes: dict, weights: dict, n_mc: int = 4000, seed: int = 42,
                              threshold: float = 0.0) -> dict:
    """Monte-Carlo propagate per-axis intervals into a plan-level score distribution + confidence.

    ``axes``: ``{axis: {"point": p, "lo": lo, "hi": hi}}`` (e.g. safety, durability, activity); ``weights``:
    ``{axis: w}`` for the linear plan combination the Planner already uses. Each axis is sampled uniformly
    in its (conformal) interval; the weighted plan score is recomputed per draw. Returns the plan-score
    point estimate + interval, and ``confidence`` = P(plan score > ``threshold``) - how reliably the plan
    clears the bar given the per-axis uncertainty. Axes are assumed independent (stated limitation).
    """
    rng = np.random.default_rng(seed)
    names = list(axes)
    w = np.array([weights.get(a, 0.0) for a in names], float)
    wsum = w.sum() if w.sum() != 0 else 1.0
    point = float(sum(weights.get(a, 0.0) * axes[a]["point"] for a in names) / wsum)

    draws = np.zeros(n_mc)
    for i, a in enumerate(names):
        lo, hi = axes[a]["lo"], axes[a]["hi"]
        draws += w[i] * rng.uniform(lo, hi, size=n_mc)
    draws /= wsum
    return {"point": point,
            "lo": float(np.percentile(draws, 5)), "hi": float(np.percentile(draws, 95)),
            "interval_width": float(np.percentile(draws, 95) - np.percentile(draws, 5)),
            "confidence": float(np.mean(draws > threshold)),
            "axes": names, "n_mc": int(n_mc)}
