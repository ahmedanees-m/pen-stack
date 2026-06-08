"""WS-UQ unit tests (Phase 3.2) - pure-logic, synthetic data, run everywhere (no real atlas/VM needed).

Asserts the *properties* the pre-registration locks: conformal coverage hits the nominal target on a
held-out synthetic set; the OOD detector separates a deliberately-shifted set and widens monotonically;
the risk-coverage curve is monotone-improving when confidence is genuinely informative.
"""
from __future__ import annotations

import numpy as np

from pen_stack.validate.selective_prediction import (
    propagate_plan_confidence,
    risk_coverage_curve,
)
from pen_stack.wgenome.ood import OODDetector
from pen_stack.wgenome.uncertainty import (
    ConformalClassifier,
    ConformalRegressor,
    ConformalWrapper,
    conformal_quantile,
)


def test_conformal_quantile_finite_sample():
    s = np.linspace(0, 1, 100)
    q = conformal_quantile(s, alpha=0.1)
    assert 0.85 <= q <= 0.95
    # too few points to certify -> +inf (honest, not a falsely tight bound)
    assert conformal_quantile(np.array([0.3]), alpha=0.1) == float("inf")


def test_regression_conformal_coverage_hits_nominal():
    rng = np.random.default_rng(0)
    n = 4000
    y = rng.normal(0, 1, n)
    yhat = y + rng.normal(0, 0.5, n)               # noisy predictor
    cal = slice(0, n // 2)
    te = slice(n // 2, n)
    reg = ConformalRegressor(alpha=0.10).calibrate(y[cal], yhat[cal])
    cov = reg.coverage(y[te], yhat[te])
    assert abs(cov["empirical_coverage"] - 0.90) <= 0.03      # within tolerance of nominal
    assert cov["within_tol"]


def test_classification_aps_coverage_and_mondrian():
    rng = np.random.default_rng(1)
    n = 6000
    p1_true = rng.uniform(0, 1, n)
    y = (rng.uniform(0, 1, n) < p1_true).astype(int)           # well-specified probabilities
    cal = slice(0, n // 2)
    te = slice(n // 2, n)
    clf = ConformalClassifier(alpha=0.10, mondrian=True).calibrate(y[cal], p1_true[cal])
    cov = clf.coverage(y[te], p1_true[te])
    assert cov["empirical_coverage"] >= 0.87                   # marginal coverage guarantee
    # class-conditional coverage exists for both classes
    assert set(cov["per_class_coverage"]) == {0, 1}


def test_ood_separates_and_widens_monotonically():
    rng = np.random.default_rng(2)
    train = rng.normal(0, 1, (2000, 5))
    id_test = rng.normal(0, 1, (1000, 5))
    ood_test = rng.normal(4, 1, (1000, 5))                     # clearly shifted
    det = OODDetector(method="mahalanobis").fit(train)
    res = det.calibrate_threshold(id_test, ood_test)
    assert res["auroc"] >= 0.75 and res["separates"]
    # widen factor is monotone non-decreasing in the OOD score
    pooled = np.vstack([id_test, ood_test])
    s = det.score(pooled)
    wf = det.widen_factor(pooled)
    order = np.argsort(s)
    assert np.all(np.diff(wf[order]) >= -1e-9)
    assert wf.min() >= 1.0


def test_ood_knn_method_runs():
    rng = np.random.default_rng(3)
    det = OODDetector(method="knn", k=5).fit(rng.normal(0, 1, (500, 4)))
    assert det.score(rng.normal(3, 1, (10, 4))).mean() > det.score(rng.normal(0, 1, (10, 4))).mean()


def test_risk_coverage_monotone_when_confidence_informative():
    rng = np.random.default_rng(4)
    n = 3000
    confidence = rng.uniform(0, 1, n)
    # higher confidence -> more likely correct (informative uncertainty)
    correct = (rng.uniform(0, 1, n) < (0.5 + 0.45 * confidence)).astype(int)
    rc = risk_coverage_curve(confidence, correct)
    assert rc["useful"] and rc["monotone_improving"] and rc["strictly_improves"]
    assert rc["accuracy_min_coverage"] > rc["accuracy_full_coverage"]


def test_risk_coverage_flat_when_confidence_uninformative():
    rng = np.random.default_rng(5)
    n = 3000
    confidence = rng.uniform(0, 1, n)
    correct = (rng.uniform(0, 1, n) < 0.7).astype(int)         # independent of confidence
    rc = risk_coverage_curve(confidence, correct)
    # an honest NEGATIVE: uninformative confidence does not strictly improve accuracy
    assert not rc["strictly_improves"] or abs(
        rc["accuracy_min_coverage"] - rc["accuracy_full_coverage"]) < 0.05


def test_plan_confidence_propagation():
    axes = {"safety": {"point": 0.8, "lo": 0.6, "hi": 0.95},
            "durability": {"point": 0.7, "lo": 0.4, "hi": 0.9},
            "activity": {"point": 0.6, "lo": 0.5, "hi": 0.7}}
    weights = {"safety": 0.4, "durability": 0.4, "activity": 0.2}
    res = propagate_plan_confidence(axes, weights, threshold=0.5)
    assert res["lo"] <= res["point"] <= res["hi"]
    assert 0.0 <= res["confidence"] <= 1.0
    # a plan well above threshold should be high-confidence
    assert res["confidence"] > 0.9


def test_planner_attach_uncertainty():
    import pandas as pd
    from pen_stack.planner.optimize import attach_uncertainty
    scored = pd.DataFrame({
        "chrom": ["chr1", "chr2"], "bin": [10, 20],
        "safety": [0.9, 0.55], "p_durable": [0.85, 0.5], "writer_activity": [0.8, 0.45],
        "score": [0.86, 0.50]})
    # in-distribution (ood_factor 1.0) -> the strong plan is grounded-confident
    out = attach_uncertainty(scored, "safe_harbour_insertion", ood_factor=1.0)
    assert {"confidence", "score_lo", "score_hi", "abstain", "epistemic_status"} <= set(out.columns)
    assert out.loc[0, "score_lo"] <= out.loc[0, "score_hi"]
    assert out.loc[0, "confidence"] >= out.loc[1, "confidence"]      # stronger plan more confident
    # a large OOD factor flips status to grounded-extrapolating
    out_ood = attach_uncertainty(scored, "safe_harbour_insertion", ood_factor=2.0)
    assert (out_ood["epistemic_status"] == "grounded-extrapolating").all()


def test_uq4_offtarget_confidence():
    from pen_stack.bridge.offtarget import offtarget_confidence
    assert offtarget_confidence(False, False, False)["abstain"]
    assert offtarget_confidence(True, False, False)["abstain"]          # engine ready, no scan -> abstain
    scanned = offtarget_confidence(True, True, True, n_candidates=42)
    assert not scanned["abstain"] and scanned["calibrated"]
    assert scanned["epistemic_status"] == "grounded-confident"


def test_uq4_structure3d_confidence():
    from pen_stack.wgenome.structure3d import uq4_confidence
    assert uq4_confidence(0.0)["abstain"] and uq4_confidence(0.0)["epistemic_status"] == "not-computable"
    flag = uq4_confidence(0.2)
    assert not flag["abstain"] and not flag["calibrated"] and flag["level"] == "qualitative_flag"


def test_conformal_wrapper_roundtrip(tmp_path):
    rng = np.random.default_rng(6)
    y = rng.normal(0, 1, 500)
    yhat = y + rng.normal(0, 0.3, 500)
    w = ConformalWrapper(alpha=0.1)
    w.add_regressor("dur", ConformalRegressor(alpha=0.1).calibrate(y, yhat))
    w.add_classifier("sil", ConformalClassifier(alpha=0.1).calibrate(
        (rng.uniform(0, 1, 500) < 0.3).astype(int), rng.uniform(0, 1, 500)))
    p = w.save(tmp_path / "cal.json")
    w2 = ConformalWrapper.load(p)
    assert np.isclose(w2.reg["dur"].qhat, w.reg["dur"].qhat)
    assert w2.clf["sil"].mondrian == w.clf["sil"].mondrian
