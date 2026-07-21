"""Human K562 position-effect head (Leemans 2019) + cell-type-routed serving.

Hermetic: builds a small model on synthetic human data and monkeypatches the loaders (no dependency on the
VM data/artifact). Validates the loader schema, dataset availability, and that a human K562 design is served
by the human head (flipped scope/provenance) while non-human designs fall back to the mESC model.
"""
import numpy as np
import pandas as pd


def _synth_human(n: int = 240, seed: int = 0) -> pd.DataFrame:
    from pen_stack.twin.data.position_effect import normalize_within
    rng = np.random.default_rng(seed)
    chroms = [f"chr{i}" for i in range(1, 7)]
    cass = ["promA", "promB"]
    rows = []
    for i in range(n):
        a, b, c, d = rng.random(), rng.random(), rng.random(), rng.random()
        expr = 2.0 * a - 1.5 * b + rng.normal(0, 0.3)
        rows.append({"dataset": "Leemans2019", "organism": "human", "cell_type": "K562",
                     "chrom": chroms[i % 6], "pos": 1000 * i, "cassette": cass[i % 2],
                     "expression_raw": expr, "silenced": bool(expr < 0),
                     "H3K27ac": a, "H3K9me3": b, "H3K27me3": c, "H3K4me1": d, "H3K36me3": rng.random()})
    return normalize_within(pd.DataFrame(rows))


def _fit_model():
    from pen_stack.twin import position_effect as pe
    df = _synth_human()
    m = pe.PositionEffectModel().fit(df)
    m.conformal = pe.calibrate_conformal(pe.evaluate(df)["_oof"])
    return m


def test_leemans_loader_and_availability(tmp_path):
    from pen_stack.twin.data import position_effect as ped
    d = tmp_path / "data/external/leemans"
    d.mkdir(parents=True)
    pd.DataFrame({"chrom": ["chr1", "chr2"], "pos": [100, 200], "promoter": ["p", "p"],
                  "expression": [1.0, -1.0], "silenced": [False, True],
                  "H3K27ac": [0.5, 0.1], "H3K9me3": [0.1, 0.8], "H3K27me3": [0.2, 0.7],
                  "H3K4me1": [0.3, 0.2], "H3K36me3": [0.4, 0.1]}
                 ).to_parquet(d / "leemans_k562_position_effect.parquet")
    out = ped._load_leemans(tmp_path)
    assert {"dataset", "organism", "cell_type", "chrom", "pos", "cassette",
            "expression_raw", "silenced"}.issubset(out.columns)
    assert (out["organism"] == "human").all() and (out["cell_type"] == "K562").all()
    assert "Leemans2019" in ped.available_datasets(tmp_path)


def test_human_k562_head_serves_with_flipped_scope(monkeypatch):
    from pen_stack.twin import position_effect as pe
    model = _fit_model()
    monkeypatch.setattr(pe, "load_human_k562_model", lambda root=None: model)
    monkeypatch.setattr(pe, "load_cached_model", lambda root=None: None)  # no mESC fallback
    ctx = {"H3K27ac": 0.6, "H3K9me3": 0.2, "H3K27me3": 0.3, "H3K36me3": 0.4}
    # EXACT-SITE resolution declared -> the head earns the outcome_validated scope.
    r = pe.predict_stage_h({"cassette": "promA", "chromatin_features": ctx,
                            "feature_resolution": "exact_site"}, cell_type="K562")
    assert r is not None
    assert r["outcome_validated"] is True
    assert any("human_K562_outcome_validated" in f for f in r["scope_flags"])
    assert "human K562 head" in r["provenance"] and "validated regime" in r["provenance"]
    assert r["interval_log2"] is not None and 0.0 <= r["p_silenced"] <= 1.0
    # the human K562 silencing classifier is a validated null (AUROC 0.50); p_silenced must be flagged
    assert any("silencing_classifier_not_validated" in f for f in r["scope_flags"])
    # a non-K562 design must NOT use the human head (falls back; mESC=None here -> None)
    assert pe.predict_stage_h({"cassette": "promA", "chromatin_features": ctx}, cell_type="HepG2") is None


def test_human_head_does_not_overclaim_at_coarse_resolution(monkeypatch):
    """Serve-time honesty: the human head validated at exact-site resolution must NOT stamp
    `outcome_validated` when the caller supplies coarse/undeclared-resolution features (realized rho~0.16)."""
    from pen_stack.twin import position_effect as pe
    model = _fit_model()
    monkeypatch.setattr(pe, "load_human_k562_model", lambda root=None: model)
    monkeypatch.setattr(pe, "load_cached_model", lambda root=None: None)
    ctx = {"H3K27ac": 0.6, "H3K9me3": 0.2, "H3K27me3": 0.3, "H3K36me3": 0.4}
    # (a) undeclared resolution -> conservative: not validated, downgraded flag.
    r = pe.predict_stage_h({"cassette": "promA", "chromatin_features": ctx}, cell_type="K562")
    assert r is not None and r["served_feature_resolution"] == "undeclared"
    assert r["outcome_validated"] is False
    assert not any("human_K562_outcome_validated" in f for f in r["scope_flags"])
    assert any("UNVALIDATED_RESOLUTION" in f and "rho~0.16" in f for f in r["scope_flags"])
    assert "BELOW the exact-site regime" in r["provenance"]
    # (b) an explicit coarse resolution is likewise not validated.
    r2 = pe.predict_stage_h({"cassette": "promA", "chromatin_ctx": {"features": ctx, "resolution": "bin_1kb"}},
                            cell_type="K562")
    assert r2 is not None and r2["served_feature_resolution"] == "bin_1kb" and r2["outcome_validated"] is False


def test_non_human_design_retains_mesc_provenance(monkeypatch):
    from pen_stack.twin import position_effect as pe
    model = _fit_model()
    monkeypatch.setattr(pe, "load_cached_model", lambda root=None: model)
    monkeypatch.setattr(pe, "load_human_k562_model", lambda root=None: None)
    ctx = {"H3K27ac": 0.6, "H3K9me3": 0.2, "H3K27me3": 0.3, "H3K36me3": 0.4}
    r = pe.predict_stage_h({"cassette": "promA", "chromatin_features": ctx}, cell_type="mESC")
    assert r is not None
    assert any("mESC" in f for f in r["scope_flags"])
    assert "mESC" in r["provenance"]
