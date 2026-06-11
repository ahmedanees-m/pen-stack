"""WS-CALIB unit tests (Phase 5.6) - calibrate immune-risk PROXIES against observed outcomes (honestly).

CI-safe. Asserts the calibration machinery: a real Spearman rho + bootstrap CI when given >=6 paired points;
'outcome_validated' ONLY when the CI excludes zero; 'weak_proxy' when it includes zero; 'mechanistic_proxy'
when there are too few points. And the central honesty gate: every CURRENT real axis is labelled a proxy (no
axis is silently upgraded to 'validated')."""
from __future__ import annotations

from pen_stack.validate.immune_calibration import (
    AXIS_STATUS,
    axis_label,
    calibrate_axis,
    run,
)


def test_strong_correlation_is_outcome_validated():
    x = [0.10, 0.20, 0.35, 0.50, 0.62, 0.75, 0.88, 0.95]
    y = [0.15, 0.18, 0.40, 0.48, 0.66, 0.70, 0.90, 0.99]
    r = calibrate_axis(x, y, axis="demo")
    assert r["status"] == "outcome_validated"
    assert r["ci"][0] > 0 and r["spearman"] > 0.8 and r["n"] == 8


def test_no_correlation_is_weak_proxy_not_validated():
    x = [i / 10 for i in range(8)]
    y = [0.5, 0.4, 0.6, 0.45, 0.55, 0.5, 0.48, 0.52]
    r = calibrate_axis(x, y, axis="demo")
    assert r["status"] == "weak_proxy"          # CI includes zero -> NOT upgraded to validated
    assert r["ci"][0] <= 0 <= r["ci"][1]


def test_insufficient_data_is_mechanistic_proxy():
    r = calibrate_axis([0.1, 0.2, 0.3], [0.2, 0.1, 0.4], axis="demo")
    assert r["status"] == "mechanistic_proxy" and r["n"] == 3
    assert "not outcome-validated" in r["label"].lower()


def test_every_current_axis_is_labelled_a_proxy():
    # the central WS-CALIB honesty gate: with no sufficient public outcome dataset, NO real axis is
    # 'outcome_validated' — each is a mechanistic/population proxy, labelled as such.
    assert set(AXIS_STATUS) == {"genotoxicity", "cd8_epitope", "innate", "preexisting_nab", "anti_peg"}
    for axis, rec in AXIS_STATUS.items():
        assert rec["status"] in {"mechanistic_proxy", "population_proxy"}
        assert rec["status"] != "outcome_validated"
        assert "proxy" in axis_label(axis).lower()


def test_run_report_is_two_sided_honest():
    rep = run("phase_5.6/out/immune_calibration.json")
    assert rep["no_fabrication"] is True
    assert set(rep["axes"]) == set(AXIS_STATUS)
    assert "not outcome-validated" in rep["summary"].lower() or "proxies" in rep["summary"].lower()
