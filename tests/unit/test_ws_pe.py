"""v6.7 PEN-EXPRESS, the learned, trained-conformal position-effect model behind Stage H (WS-D/M/U/I/B/V).

CI-safe: a synthetic position-effect table with a PLANTED signal (expression driven by chromatin marks; silencing
by heterochromatin) exercises the data unification, the learned model, conformal calibration, the controls, and the
Stage-H integration WITHOUT the gitignored TRIP data or model artifact. The REAL-data claim (the factored model
beats the v3.x durability head on TRIP) runs only when the data is present (VM / local checkout), and is skipped,
not faked, in CI.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pen_stack.twin.data import position_effect as ped


def _synth(n=720, seed=7) -> pd.DataFrame:
    """Synthetic position-effect table: expression = active - heterochromatin + cassette offset + noise;
    silenced = low-expression tail. 6 chromosomes, 2 cassettes, enough for blocked CV + the controls."""
    rng = np.random.default_rng(seed)
    chrom = rng.choice([f"chr{i}" for i in range(1, 7)], n)
    cassette = rng.choice(["promA", "promB"], n)
    k27ac, k9me3 = rng.uniform(0, 1, n), rng.uniform(0, 1, n)
    k4me3, k27me3 = rng.uniform(0, 1, n), rng.uniform(0, 1, n)
    offset = np.where(cassette == "promA", 1.0, -1.0)
    expr = 3.0 * k27ac - 3.5 * k9me3 + offset + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"dataset": "SYNTH", "organism": "synthetic", "cell_type": "synthCT",
                       "chrom": chrom, "pos": rng.integers(1, 10_000_000, n), "cassette": cassette,
                       "expression_raw": expr, "H3K27ac": k27ac, "H3K9me3": k9me3,
                       "H3K4me3": k4me3, "H3K27me3": k27me3})
    df["silenced"] = df["expression_raw"] <= df["expression_raw"].quantile(0.25)
    return ped.normalize_within(df)


# ---- WS-D: data unification --------------------------------------------------------------------
def test_registry_has_verified_accessions():
    d = ped.DATASETS
    assert d["TRIP_Akhtar2013"].doi == "10.1016/j.cell.2013.07.018"
    assert "GSE223403" in d["MPIRE_Hong2024"].accession # verified MPIRE accession
    assert d["lentiMPRA_Agarwal2025"].doi == "10.1038/s41586-024-08430-9" # the corrected lentiMPRA citation
    # the lentiMPRA bioRxiv id is attributed to lentiMPRA, NOT to e2MPRA/ccMPRA (the verification fix)
    assert "2023.03.05.531189" in d["lentiMPRA_Agarwal2025"].accession


def test_normalize_is_within_cassette():
    df = _synth()
    g = df.groupby("cassette")["expression_z"].mean().abs()
    assert (g < 1e-6).all() # z-mean ~0 within each cassette


def test_blocked_splits_are_leakage_clean_and_celltype_is_data_gated():
    df = _synth()
    sp = ped.blocked_splits(df)
    assert ped.leakage_report(df, sp)["clean"] is True
    assert ped.heldout_celltype_splits(df) == [] # single cell type -> data-gated, honest


# ---- WS-M: the learned model + WS-U conformal --------------------------------------------------
def test_factored_model_beats_cassette_only_and_calibrates():
    from pen_stack.twin.position_effect import (
        PositionEffectModel, calibrate_conformal, conformal_heldout_coverage, evaluate,
    )
    df = _synth()
    rep = evaluate(df)
    e = rep["expression"]
    assert e["rho_factored"] > e["rho_cassette_only"] # context adds real signal
    assert "interaction_extra_r2" in rep["separability"] # separability reported either way
    conf = calibrate_conformal(rep["_oof"])
    assert np.isfinite(conf.qhat)
    cov = conformal_heldout_coverage(rep["_oof"])
    assert 0.0 <= cov["heldout_coverage"] <= 1.0 and cov["nominal"] == 0.9
    model = PositionEffectModel().fit(df)
    model.conformal = conf
    iv = model.predict_interval(df.head(5))
    assert iv["lo"] is not None and (iv["hi"] >= iv["lo"]).all() # a real interval, hi >= lo


# ---- WS-V: controls + known-biology ------------------------------------------------------------
def test_label_shuffle_collapses_to_chance():
    from pen_stack.validate.expr_controls import label_shuffle_control
    res = label_shuffle_control(_synth(), seed=0)
    assert res["rho_real"] > 0.3 and res["is_chance"] and res["passes"] # shuffling kills the signal


def test_known_biology_recovered():
    from pen_stack.twin.position_effect import PositionEffectModel
    from pen_stack.validate.known_biology_expr import active_chromatin_expression, heterochromatin_silencing
    model = PositionEffectModel().fit(_synth())
    het = heterochromatin_silencing(model)
    assert het["silencing_increases_with_heterochromatin"] # H3K9me3 up -> silencing up
    assert het["expression_decreases_with_heterochromatin"]
    act = active_chromatin_expression(model)
    assert act["expression_increases_with_active_chromatin"] # H3K27ac up -> expression up


# ---- WS-I: Stage-H integration -----------------------------------------------------------------
_DESIGN = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
           "promoter": "ef1a", "copy_number": 1, "accessibility": 0.8, "writer_output_form": "dsDNA"}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


def test_stage_h_heuristic_fallback_when_no_context():
    """No chromatin context (or no artifact) -> heuristic path; learned block is None. Backward-compatible."""
    from pen_stack.twin.outcome import predict_outcome
    o = predict_outcome(_DESIGN, "k562")
    assert o["stage_h_mode"] == "heuristic" and o["position_effect"] is None
    lo, hi = o["interval"] # the v5.9 contract is intact
    assert lo <= o["predicted_outcome"]["relative_expression"] <= hi


def test_stage_h_learned_path_with_injected_model(monkeypatch):
    """With a chromatin context AND a model present, Stage H serves a TRAINED-CONFORMAL interval + p_silenced."""
    from pen_stack.twin import outcome as out
    from pen_stack.twin import position_effect as pemod
    model = pemod.PositionEffectModel().fit(_synth())
    rep = pemod.evaluate(_synth())
    model.conformal = pemod.calibrate_conformal(rep["_oof"])
    monkeypatch.setattr(pemod, "load_cached_model", lambda root=None: model)
    ctx = {"H3K27ac": 0.6, "H3K9me3": 0.2, "H3K4me3": 0.3, "H3K27me3": 0.3}
    o = out.predict_outcome({**_DESIGN, "cassette": "promA", "chromatin_features": ctx}, "k562")
    assert o["stage_h_mode"] == "learned_trained_conformal"
    pe = o["position_effect"]
    assert pe["interval_log2"] is not None and "conformal" in pe["interval_kind"].lower()
    assert 0.0 <= pe["p_silenced"] <= 1.0
    assert "stage_h_learned_trained_conformal" in o["scope_flags"]


# ---- WS-B: TPE-Bench ---------------------------------------------------------------------------
def test_tpe_bench_split_is_sealed_and_sha_locked():
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "benchmarks/position_effect"
    spec = (root / "split.json").read_bytes()
    sha = hashlib.sha256(spec).hexdigest()
    locked = (root / "SHA256SUMS").read_text(encoding="utf-8").split()[0]
    assert sha == locked # split frozen + checksummed
    import json
    j = json.loads(spec)
    assert j["chrom_holdout"]["test_chroms"] == ["chr2", "chr5", "chr14", "chrX"]
    assert j["celltype_holdout"]["status"] == "data_gated" # honest transfer gating


# ---- real-data claim (skipped, not faked, in CI) ----------------------------------------------
def test_real_trip_factored_beats_durability_head_when_available():
    if not ped.available_datasets():
        pytest.skip("TRIP not present (CI / bare wheel), real-data claim runs on VM / local checkout only")
    from pen_stack.twin.position_effect import evaluate
    df = ped.load_position_effect(["TRIP_Akhtar2013"])
    e = evaluate(df)["expression"]
    # the headline: factored model beats the v3.x context-only durability head, CI excludes zero
    assert e["rho_factored"] > e["rho_context_only_durability_head"]
    assert e["delta_factored_vs_context"]["excludes_zero"] is True
