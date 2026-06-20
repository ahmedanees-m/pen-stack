"""v3.1 WS-F - local recalibration / private-data adaptation. CI-safe (synthetic; no atlas/network)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def test_ingest_normalize_derives_bin_and_validates():
    from pen_stack.adapt.ingest import normalize, schema_summary
    df = normalize(pd.DataFrame({"chrom": ["chr1", "chr2"], "pos": [1500, 9000], "label": [1, 0]}))
    assert list(df.columns)[:4] == ["chrom", "bin", "ct", "label"]
    assert df["bin"].tolist() == [1, 9] and (df["ct"] == "user").all()
    assert schema_summary(df)["label_kind"] == "binary"
    with pytest.raises(ValueError):
        normalize(pd.DataFrame({"chrom": ["chr1"], "label": [1]})) # no bin/pos
    with pytest.raises(ValueError):
        normalize(pd.DataFrame({"chrom": ["chr1"], "bin": [1], "label": [5]})) # label out of range


def test_isotonic_calibrator_roundtrip(tmp_path):
    from pen_stack.adapt.recalibrate import IsotonicCalibrator, recalibrate
    rng = np.random.default_rng(0)
    s = rng.random(300)
    y = (rng.random(300) < s).astype(float)
    cal = recalibrate(s, y)
    p = tmp_path / "cal.json"
    cal.save(p)
    reloaded = IsotonicCalibrator.load(p)
    assert np.allclose(cal.transform(s), reloaded.transform(s), atol=1e-9) # serialization is faithful
    assert (cal.transform(s) >= 0).all() and (cal.transform(s) <= 1).all()


def test_gate_no_skill_guard():
    from pen_stack.adapt.report import gate
    base = {"brier": 0.30}
    no_skill = {"brier": 0.25}
    # adapted beats released but NOT the no-skill constant -> rejected (the trivial-calibration guard)
    g1 = gate(base, {"brier": 0.26}, primary="brier", no_skill=no_skill)
    assert g1["activate"] is False and g1["beats_released"] is True and g1["beats_no_skill"] is False
    # adapted beats both -> activated
    g2 = gate(base, {"brier": 0.20}, primary="brier", no_skill=no_skill)
    assert g2["activate"] is True


def test_evaluate_metrics_extremes():
    from pen_stack.adapt.report import evaluate
    y = [0, 0, 1, 1]
    assert evaluate([0.0, 0.0, 1.0, 1.0], y)["brier"] == 0.0
    assert evaluate([0.0, 0.0, 1.0, 1.0], y)["auroc"] == 1.0


def test_adapt_demo_acceptance_both_ways():
    from pen_stack.validate.adapt_demo import run
    r = run()
    a = r["acceptance"]
    assert a["adaptation_improves_or_is_rejected"] is True # activate activated, reject rejected
    assert a["released_model_provably_unchanged"] is True # released model fingerprint identical
    assert a["before_after_report_produced"] is True
    assert r["activate_case"]["activated"] is True and r["reject_case"]["activated"] is False
    assert r["activate_case"]["auroc_preserved"] is True # isotonic preserves ranking


def test_adapt_pipeline_versions_without_touching_released():
    from pen_stack.adapt.pipeline import adapt
    rng = np.random.default_rng(3)
    n = 200
    latent = rng.random(n)
    df = pd.DataFrame({"chrom": rng.choice(["chr1", "chr2", "chr3"], n), "bin": rng.integers(0, 1000, n),
                       "score": np.clip(latent ** 2, 0, 1), "label": (rng.random(n) < latent).astype(float)})
    rep = adapt(df, target="safety", method="isotonic", local_id="pytest")
    assert rep["released_model_unchanged"] is True
    assert set(rep["held_out_before"]) >= {"brier", "ece", "auroc"}
    assert "no_skill_constant" in rep["gate"]


def test_adapt_finetune_method_runs_and_is_gated():
    from pen_stack.adapt.pipeline import adapt
    rng = np.random.default_rng(7)
    n = 240
    latent = rng.random(n)
    df = pd.DataFrame({"chrom": rng.choice(["chr1", "chr2", "chr3", "chr4"], n),
                       "bin": rng.integers(0, 1000, n),
                       "score": np.clip(latent ** 2, 0, 1), "feat2": latent + rng.normal(0, 0.1, n),
                       "label": (rng.random(n) < latent).astype(float)})
    rep = adapt(df, target="safety", method="finetune", local_id="pytest_ft",
                feature_cols=["score", "feat2"])
    assert rep["method"] == "finetune" and rep["released_model_unchanged"] is True
    assert rep["gate"]["activate"] in (True, False) # gated either way, never crashes
