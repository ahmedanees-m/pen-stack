"""Sequence-derived chromatin tracks (WS-C2): map AlphaGenome predictions onto the measured-atlas schema
and recompute writability/safety/durability from predicted tracks.

Two details:
  * Unit handling. AlphaGenome track outputs are in the model's own units, not the measured ENCODE scale the
    safety/durability models were trained on. Per-track agreement is therefore reported with Spearman (rank,
    unit-free) alongside Pearson. For the *score-level* recompute we quantile-map each predicted track onto
    the measured track's marginal (a standard rank-preserving calibration), so the recomputed scores test
    whether AlphaGenome's RANKING of the epigenome recovers the measured-track scores - not a unit accident.
  * Coverage. AlphaGenome predicts H3K9me3 for HepG2 but NOT K562; missing marks come back NaN and are
    excluded from per-track correlation and passed as NaN to the (NaN-native) durability model.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pen_stack.wgenome.providers import AlphaGenomeProvider, _HISTONES, TRACK_NAMES

_ROOT = Path(__file__).resolve().parents[2]
_P1_FEAT = _ROOT.parent / "phase_1" / "features"
_P1_OUT = _ROOT.parent / "phase_1" / "out"


def predicted_tracks_frame(ct: str, bins: pd.DataFrame, provider: AlphaGenomeProvider | None = None,
                           offline: bool = False) -> pd.DataFrame:
    """Predicted 7-track values for the given (chrom, bin) rows. Cached per bin in the provider."""
    provider = provider or AlphaGenomeProvider(assembly="hg38")
    rows = []
    for r in bins.itertuples():
        rec = provider.tracks(r.chrom, int(r.bin), ct, offline=offline)
        if rec.get("available"):
            rows.append({"chrom": r.chrom, "bin": int(r.bin),
                         **{t: rec.get(t, np.nan) for t in TRACK_NAMES}})
    return pd.DataFrame(rows)


def quantile_map(pred: pd.Series, measured: pd.Series) -> pd.Series:
    """Map `pred` onto `measured`'s marginal by matching ranks (rank-preserving calibration)."""
    pred = pred.astype(float)
    if pred.notna().sum() < 2 or measured.notna().sum() < 2:
        return pred
    ranks = pred.rank(pct=True, na_option="keep")
    q = np.nanpercentile(measured.to_numpy(dtype=float), np.clip(ranks.to_numpy() * 100, 0, 100))
    return pd.Series(q, index=pred.index)


def _load_models(ct: str):
    from pen_stack.wgenome.writability import load_pickle
    safety = load_pickle(str(_P1_OUT / f"safety_{ct}.pkl"))
    dur = load_pickle(str(_P1_OUT / "durability.pkl"))
    return safety, dur


def recompute_scores(matrix: pd.DataFrame, ct: str) -> pd.DataFrame:
    """Apply the trained safety + durability models to a feature matrix; return writability components."""
    from pen_stack.wgenome.writability import build_writability
    safety, dur = _load_models(ct)
    return build_writability(matrix, safety, dur)


def build_predicted_matrix(measured_matrix: pd.DataFrame, predicted: pd.DataFrame, ct: str) -> pd.DataFrame:
    """Substitute quantile-mapped predicted tracks into a copy of the measured feature matrix.

    Distance/integration features are genomic (not predicted) and are kept as-is; only the chromatin tracks
    (atac/dnase/5 histones -> accessibility + marks) are replaced, then `accessibility` is rederived.
    """
    from pen_stack.wgenome.features import add_accessibility
    m = measured_matrix.merge(predicted, on=["chrom", "bin"], how="inner", suffixes=("", "_pred"))
    for t in TRACK_NAMES:
        pc = f"{t}_pred"
        if pc in m.columns and t in m.columns:
            m[t] = quantile_map(m[pc], m[t]) # map predicted onto this sample's measured marginal
    m = m.drop(columns=[c for c in m.columns if c.endswith("_pred")])
    m = m.drop(columns=["accessibility"], errors="ignore")
    return add_accessibility(m)


def histone_marks_for(ct: str) -> list[str]:
    """Marks AlphaGenome actually predicts for this cell type (K562 lacks H3K9me3)."""
    return [m for m in _HISTONES if not (ct.lower() == "k562" and m == "H3K9me3")]
