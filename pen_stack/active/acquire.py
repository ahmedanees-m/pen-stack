"""Acquisition functions for the experiment designer (v5.10, WS-ACQ).

Score each candidate experiment by the information it is expected to yield, computed from the calibrated v5.9
twin's predictive uncertainty (never fabricated). Three signals:
  * expected_information_gain, reducible predictive uncertainty (entropy now - expected posterior entropy),
  * predictive_entropy, the twin's current uncertainty (from its interval width),
  * immune_voi, value of information for VALIDATING an immune PROXY axis (turns proxy -> validated).
The acquisition is only as good as the v5.9 twin and the v5.6 labels it queries; it chooses informative
experiments, it does not run them.
"""
from __future__ import annotations

import math

# a measurement does not resolve uncertainty perfectly: a noise floor on the post-experiment entropy.
_MEASUREMENT_NOISE_SD = 0.05
_TWO_PI_E = 2.0 * math.pi * math.e


def _interval_sd(outcome: dict) -> float:
    """Std-dev implied by the twin's (approx 95%) interval: sd ~ width / (2 * 1.96)."""
    lo, hi = outcome.get("interval", [0.0, 0.0])
    return max(1e-6, (float(hi) - float(lo)) / (2.0 * 1.96))


def _gaussian_entropy(sd: float) -> float:
    return 0.5 * math.log(_TWO_PI_E * sd * sd)


def predictive_entropy(outcome: dict) -> float:
    """Differential entropy of the twin's predictive distribution, from its interval width."""
    return _gaussian_entropy(_interval_sd(outcome))


def _expected_posterior_entropy(outcome: dict) -> float:
    """Entropy expected AFTER running the experiment: the measurement collapses predictive sd toward the
    measurement noise floor (cannot go below it)."""
    post_sd = max(_MEASUREMENT_NOISE_SD, min(_interval_sd(outcome), _MEASUREMENT_NOISE_SD * 2))
    return _gaussian_entropy(post_sd)


def expected_information_gain(candidate: dict, cell_state: str, model_ctx: dict | None = None) -> float:
    """EIG ~ reducible uncertainty = predictive entropy now - expected posterior entropy. Computed from the
    calibrated twin's predictive distribution; >= 0 (a measurement never increases expected uncertainty)."""
    from pen_stack.twin.outcome import predict_outcome
    o = predict_outcome(candidate, cell_state or candidate.get("cell_state", ""))
    return max(0.0, predictive_entropy(o) - _expected_posterior_entropy(o))


def immune_voi(candidate: dict, cell_state: str = "") -> float:
    """Value of information for validating an immune PROXY axis (v5.6): an axis still labelled a proxy that this
    experiment would MEASURE is high-VOI (turns proxy -> outcome-validated). Reads the v5.6 validation labels."""
    from pen_stack.twin.outcome import predict_outcome
    prof = predict_outcome(candidate, cell_state or candidate.get("cell_state", "")).get("immune_outcome") or {}
    measures = {str(a).strip().lower() for a in (candidate.get("measures_immune_axes") or [])}
    voi = 0.0
    for axis, rec in prof.get("axes", {}).items():
        label = (rec.get("validation") or "").lower()
        is_proxy = "proxy" in label and "not outcome-validated" in label
        if is_proxy and (not measures or axis.lower() in measures):
            voi += 1.0
    return voi


def acquisition_score(candidate: dict, cell_state: str, model_ctx: dict | None = None,
                      *, w_eig: float = 1.0, w_unc: float = 0.3, w_imm: float = 0.4) -> float:
    """Weighted acquisition: information gain + raw uncertainty + immune value-of-information. Fully traceable
    to twin quantities + v5.6 labels (no fabricated values); deterministic given the inputs."""
    from pen_stack.twin.outcome import predict_outcome
    o = predict_outcome(candidate, cell_state or candidate.get("cell_state", ""))
    eig = expected_information_gain(candidate, cell_state, model_ctx)
    unc = predictive_entropy(o)
    return w_eig * eig + w_unc * unc + w_imm * immune_voi(candidate, cell_state)
