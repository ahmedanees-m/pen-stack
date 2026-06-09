"""WS-CAL unit tests (Phase 3.4) - plan-confidence calibrated against documented outcomes.

Verifier-backed + the DOI writer panel (data/writer_panel.csv); skips cleanly if the panel is absent.
Asserts the pre-registered acceptance: a reliability diagram + ECE + a selective-prediction gap with a
bootstrap CI are produced, the result is reported whatever its shape, and no-fabrication holds.
"""
from __future__ import annotations

import pytest

from pen_stack.validate import outcome_calibration as OC


def _report():
    r = OC.run()
    if not r.get("available"):
        pytest.skip(f"writer panel unavailable: {r.get('note')}")
    return r


def test_outcome_calibration_runs_and_reports():
    r = _report()
    assert r["n_plans"] == r["n_writes"] * r["n_families"]
    assert r["n_families"] == 4 and r["n_writes"] >= 10
    assert isinstance(r["ece"], float)
    assert len(r["reliability_bins"]) == 5
    assert r["no_fabrication"] is True


def test_selective_prediction_has_ci_and_is_reported():
    sp = _report()["selective_prediction"]
    # the gap (high-conf - low-conf accuracy) is reported with a bootstrap 95% CI, whatever its sign
    assert sp["high_minus_low_gap"] is not None
    assert sp["gap_ci95"][0] is not None and sp["gap_ci95"][1] is not None
    assert sp["gap_ci95"][0] <= sp["gap_ci95"][1]
    assert isinstance(sp["useful_monotone"], bool)


def test_low_confidence_plans_are_infeasible_choices():
    # capacity-infeasible plans (beyond a family's documented envelope) are never the documented choice
    sp = _report()["selective_prediction"]
    assert sp["accuracy_low_confidence_half"] == 0.0
    # and high-confidence plans recover the documented choice strictly more often (the usefulness signal)
    assert sp["accuracy_high_confidence_half"] > sp["accuracy_low_confidence_half"]
    assert sp["useful_monotone"] is True


def test_interpretation_states_calibration_caveat_honestly():
    r = _report()
    # high ECE + significant gap must be reported as useful-for-ranking, not as absolute calibration
    assert r["ece"] > r["prevalence"]                     # confidence over-states absolute recovery (honest)
    assert "scope" in r and "survivorship" in r["scope"]
