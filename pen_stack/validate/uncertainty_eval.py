"""WS-UQ real-data evaluation driver (Phase 3.2, UQ1-UQ3).

Runs the conformal wrappers + OOD detector + risk-coverage curve against the ACTUAL Phase-1 heads and
feature stores, and writes ``out/ws_uq_*.json`` for the G-UQ gate. No model is retrained: the durability
head's chromosome-grouped out-of-fold predictions (reused from ``durability_baselines._cv_oof``) are the
calibration/test predictions; coverage is evaluated on **held-out chromosomes** so the reported number
respects the existing spatial grouping (no leakage between adjacent bins).

Heads evaluated:
  * durability EXPRESSION (regression)   -> normalized-residual conformal intervals (UQ1);
  * durability SILENCED (classification) -> APS / Mondrian conformal prediction sets (UQ1);
  * the silenced head also drives the risk-coverage curve (UQ3) - is the confidence USEFUL?
OOD (UQ2): fit on one cell type's chromatin features, separate held-out in-distribution bins from a
different cell type (a real distribution shift), report the separation AUROC + monotone widening.

Run on the VM in Docker (lightgbm + sklearn present). Data paths follow the repo convention
(``_ROOT.parent/phase_1/features``); when a store is absent the corresponding block reports
``available: false`` so the driver never crashes.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pen_stack.validate.durability_baselines import _cv_oof
from pen_stack.validate.selective_prediction import risk_coverage_curve
from pen_stack.wgenome.uncertainty import (
    ConformalClassifier,
    ConformalRegressor,
    ConformalWrapper,
    reliability_curve,
)
from pen_stack.wgenome.ood import OODDetector

_ROOT = Path(__file__).resolve().parents[2]
_FEAT = _ROOT.parent / "phase_1" / "features"
_TRIP = _FEAT / "trip_with_chromatin.parquet"
_OUT = _ROOT / "out"
_MARKS = ["H3K27ac", "H3K4me1", "H3K4me3", "H3K9me3", "H3K27me3"]
_OOD_SCHEMA = ["accessibility", "H3K27ac", "H3K4me1", "H3K4me3", "H3K9me3", "H3K27me3"]
ALPHA = 0.10                                   # 90% nominal coverage (pre-registered)


def _chrom_split(chrom: pd.Series, frac_cal: float = 0.5, seed: int = 42):
    """Split CHROMOSOMES (not rows) into calibration vs test so conformal coverage respects the grouped
    structure - adjacent bins never straddle the split."""
    rng = np.random.default_rng(seed)
    chroms = np.array(sorted(chrom.unique()))
    rng.shuffle(chroms)
    n_cal = max(1, int(round(frac_cal * len(chroms))))
    cal = set(chroms[:n_cal].tolist())
    is_cal = chrom.isin(cal).to_numpy()
    return is_cal, ~is_cal, sorted(cal), sorted(set(chroms.tolist()) - cal)


def durability_conformal(alpha: float = ALPHA, seed: int = 42) -> dict:
    """UQ1 - conformal intervals (expression) + APS sets (silenced) on grouped-held-out TRIP chromosomes."""
    if not _TRIP.exists():
        return {"available": False, "note": "TRIP-with-chromatin not present"}
    df = pd.read_parquet(_TRIP)
    d, sil_oof, exp_oof = _cv_oof(df, _MARKS, seed=seed)
    is_cal, is_te, cal_chroms, te_chroms = _chrom_split(d["chrom"], seed=seed)

    # --- regression: expression intervals ---
    reg = ConformalRegressor(alpha=alpha)
    reg.calibrate(d["expression"].to_numpy()[is_cal], exp_oof[is_cal])
    cov_reg = reg.coverage(d["expression"].to_numpy()[is_te], exp_oof[is_te])

    # group / Mondrian fallback (per-chromosome quantile) - reported alongside marginal
    reg_g = ConformalRegressor(alpha=alpha)
    reg_g.calibrate(d["expression"].to_numpy()[is_cal], exp_oof[is_cal],
                    groups=d["chrom"].to_numpy()[is_cal])

    # --- classification: silenced prediction sets ---
    clf = ConformalClassifier(alpha=alpha, mondrian=True)
    clf.calibrate(d["silenced"].to_numpy()[is_cal].astype(int), sil_oof[is_cal])
    cov_clf = clf.coverage(d["silenced"].to_numpy()[is_te].astype(int), sil_oof[is_te])
    rel = reliability_curve(sil_oof[is_te], d["silenced"].to_numpy()[is_te])

    wrapper = ConformalWrapper(alpha=alpha)
    wrapper.add_regressor("durability_expression", reg)
    wrapper.add_classifier("durability_silenced", clf)
    wrapper.meta.update({"cal_chroms": cal_chroms, "test_chroms": te_chroms,
                         "n_cal": int(is_cal.sum()), "n_test": int(is_te.sum())})
    return {"available": True, "alpha": alpha, "nominal_coverage": 1 - alpha,
            "n_total": int(len(d)), "cal_chroms": cal_chroms, "test_chroms": te_chroms,
            "expression_interval": cov_reg,
            "silenced_set": cov_clf, "silenced_reliability": rel,
            "calibration_artifact": wrapper.to_dict()}


def risk_coverage(seed: int = 42) -> dict:
    """UQ3 - is the silenced-head confidence USEFUL? Risk-coverage on grouped-held-out TRIP."""
    if not _TRIP.exists():
        return {"available": False, "note": "TRIP-with-chromatin not present"}
    df = pd.read_parquet(_TRIP)
    d, sil_oof, _ = _cv_oof(df, _MARKS, seed=seed)
    y = d["silenced"].to_numpy().astype(int)
    pred = (sil_oof >= 0.5).astype(int)
    correct = (pred == y).astype(float)
    confidence = np.abs(sil_oof - 0.5) * 2.0          # 0 at the decision boundary, 1 at the extremes
    rc = risk_coverage_curve(confidence, correct)
    return {"available": True, "n": int(len(d)), **rc}


def ood_eval(in_ct: str = "k562", ood_ct: str = "hspc", seed: int = 42) -> dict:
    """UQ2 - separate held-out in-distribution bins from a different cell type's bins (a real shift)."""
    f_in = _FEAT / f"chromatin_{in_ct}.parquet"
    f_ood = _FEAT / f"chromatin_{ood_ct}.parquet"
    if not f_in.exists() or not f_ood.exists():
        return {"available": False, "note": f"chromatin store for {in_ct}/{ood_ct} absent"}
    from pen_stack.wgenome.features import add_accessibility
    a = add_accessibility(pd.read_parquet(f_in))
    b = add_accessibility(pd.read_parquet(f_ood))
    feats = [c for c in _OOD_SCHEMA if c in a.columns and c in b.columns]
    a = a.dropna(subset=feats)
    b = b.dropna(subset=feats)
    rng = np.random.default_rng(seed)
    # subsample for a tractable, balanced construction
    n = min(8000, len(a) // 2, len(b))
    ai = rng.permutation(len(a))
    train = a.iloc[ai[:n]][feats].to_numpy()
    id_test = a.iloc[ai[n:2 * n]][feats].to_numpy()
    ood_test = b.iloc[rng.permutation(len(b))[:n]][feats].to_numpy()

    det = OODDetector(method="mahalanobis").fit(train)
    cal = det.calibrate_threshold(id_test, ood_test)
    # monotone widening: bin the pooled scores, check widen_factor is non-decreasing in OOD score
    pooled = np.vstack([id_test, ood_test])
    s = det.score(pooled)
    wf = det.widen_factor(pooled)
    order = np.argsort(s)
    monotone = bool(np.all(np.diff(wf[order]) >= -1e-9))
    return {"available": True, "method": "mahalanobis", "in_ct": in_ct, "ood_ct": ood_ct,
            "features": feats, "n_per_group": int(n), **cal,
            "widen_monotone_in_score": monotone,
            "widen_range": [float(wf.min()), float(wf.max())]}


def ood_eval_multi(in_cts=("k562", "hepg2"), ood_cts=("hspc",), methods=("mahalanobis",),
                   seed: int = 42, n_cap: int = 4000) -> dict:
    """UQ2 EXPLORATORY utility (NOT pre-registered, NOT in the gated run) - the OOD detector across cell-type
    pairs / methods, to contextualise the locked primary's near-miss (k562/hspc are both hematopoietic, so
    only weakly OOD in chromatin space). Reads the large per-cell-type chromatin stores, so it is run on
    demand, not in :func:`run`. Pairs chosen after seeing the primary -> exploratory only, never the headline.
    """
    out = {}
    for in_ct in in_cts:
        for ood_ct in ood_cts:
            for method in methods:
                try:
                    r = _ood_with_method(in_ct, ood_ct, method, seed, n_cap)
                    out[f"{in_ct}_vs_{ood_ct}__{method}"] = r
                except Exception as ex:  # noqa: BLE001 - exploratory; never crash
                    out[f"{in_ct}_vs_{ood_ct}__{method}"] = {"available": False, "error": str(ex)[:160]}
    return out


def _ood_with_method(in_ct: str, ood_ct: str, method: str, seed: int = 42, n_cap: int = 4000) -> dict:
    from pen_stack.wgenome.features import add_accessibility
    a = add_accessibility(pd.read_parquet(_FEAT / f"chromatin_{in_ct}.parquet"))
    b = add_accessibility(pd.read_parquet(_FEAT / f"chromatin_{ood_ct}.parquet"))
    feats = [c for c in _OOD_SCHEMA if c in a.columns and c in b.columns]
    a, b = a.dropna(subset=feats), b.dropna(subset=feats)
    rng = np.random.default_rng(seed)
    n = min(n_cap, len(a) // 2, len(b))
    ai = rng.permutation(len(a))
    det = OODDetector(method=method).fit(a.iloc[ai[:n]][feats].to_numpy())
    cal = det.calibrate_threshold(a.iloc[ai[n:2 * n]][feats].to_numpy(),
                                  b.iloc[rng.permutation(len(b))[:n]][feats].to_numpy())
    return {**cal, "n_per_group": int(n), "method": method, "in_ct": in_ct, "ood_ct": ood_ct}


def ood_cross_species(seed: int = 42) -> dict:
    """UQ2 REAL-SHIFT positive case (reviewer-driven) - a genuinely different context, not a lineage-adjacent
    cell type. In-distribution = mouse mESC TRIP loci (the 5 shared histone marks); OOD = human K562 bins on
    the SAME 5 marks. Cross-species is a real distribution shift, so this is the positive case the weak
    cross-cell-type tests (K562->HSPC 0.72, K562->HepG2 0.65) lack - it shows the detector DOES fire when the
    features genuinely move, complementing the honest finding that human cell types barely move."""
    f_human = _FEAT / "chromatin_k562.parquet"
    if not _TRIP.exists() or not f_human.exists():
        return {"available": False, "note": "TRIP (mESC) or human K562 chromatin store absent"}
    mouse = pd.read_parquet(_TRIP).dropna(subset=_MARKS)
    human = pd.read_parquet(f_human).dropna(subset=_MARKS)
    rng = np.random.default_rng(seed)
    n = min(4000, len(mouse) // 2, len(human))
    mi = rng.permutation(len(mouse))
    det = OODDetector(method="mahalanobis").fit(mouse.iloc[mi[:n]][_MARKS].to_numpy())
    cal = det.calibrate_threshold(mouse.iloc[mi[n:2 * n]][_MARKS].to_numpy(),
                                  human.iloc[rng.permutation(len(human))[:n]][_MARKS].to_numpy())
    return {"available": True, "construction": "mouse mESC (in-dist) vs human K562 (OOD), 5 shared histone marks",
            "method": "mahalanobis", "n_per_group": int(n), **cal,
            "note": "cross-SPECIES real shift - the positive case; contrast the weak cross-CELL-TYPE tests "
                    "(human cell types barely move in chromatin-mark space)"}


def ood_feature_regime(seed: int = 42) -> dict:
    """UQ2 REAL-SHIFT positive case #2 (reviewer-driven) - a genuinely different *chromatin-state* context
    WITHIN one cell type, where the features actually move. In-distribution = euchromatic K562 bins (low
    H3K9me3 + accessible); OOD = strongly heterochromatic K562 bins (top-decile H3K9me3 + low accessibility) -
    a real, biologically-distinct regime (heterochromatin vs euchromatin). This complements the finding that
    biological *context* shifts (cell type, species) do NOT move chromatin-mark distributions: a chromatin
    *state* shift does, and the detector should fire on it."""
    f = _FEAT / "chromatin_k562.parquet"
    if not f.exists():
        return {"available": False, "note": "K562 chromatin store absent"}
    from pen_stack.wgenome.features import add_accessibility
    d = add_accessibility(pd.read_parquet(f)).dropna(subset=_OOD_SCHEMA)
    h9 = d["H3K9me3"]
    acc = d["accessibility"]
    eu = d[(h9 <= h9.quantile(0.5)) & (acc >= acc.quantile(0.5))]            # euchromatin (in-dist)
    het = d[(h9 >= h9.quantile(0.9)) & (acc <= acc.quantile(0.3))]          # strong heterochromatin (OOD)
    if len(eu) < 200 or len(het) < 200:
        return {"available": False, "note": "too few euchromatin/heterochromatin bins"}
    rng = np.random.default_rng(seed)
    n = min(4000, len(eu) // 2, len(het))
    ei = rng.permutation(len(eu))
    det = OODDetector(method="mahalanobis").fit(eu.iloc[ei[:n]][_OOD_SCHEMA].to_numpy())
    cal = det.calibrate_threshold(eu.iloc[ei[n:2 * n]][_OOD_SCHEMA].to_numpy(),
                                  het.iloc[rng.permutation(len(het))[:n]][_OOD_SCHEMA].to_numpy())
    return {"available": True, "construction": "K562 euchromatin (in-dist) vs K562 strong heterochromatin (OOD)",
            "method": "mahalanobis", "n_per_group": int(n), **cal,
            "note": "real WITHIN-cell-type chromatin-STATE shift (features move), unlike cross-context shifts"}


def run(out_dir: str | Path = _OUT, alpha: float = ALPHA) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"alpha": alpha, "nominal_coverage": 1 - alpha,
              "UQ1_durability_conformal": durability_conformal(alpha=alpha),
              "UQ2_ood": ood_eval(),
              "UQ2_ood_real_shift_cross_species": ood_cross_species(),
              "UQ2_ood_feature_regime": ood_feature_regime(),
              "UQ3_risk_coverage": risk_coverage()}
    (out_dir / "ws_uq_coverage.json").write_text(json.dumps(report, indent=2, default=str),
                                                 encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
