"""Writability integration (Phase 1, Step 1.9).

Combines the three layers into a transparent, DECOMPOSABLE per-locus writability profile (components
kept visible; never collapsed into one opaque number):

    writability = f(safety, durability, reachability)

- safety:      1 - P(genotoxic) from the safety model (calibrated risk; safe-harbour discriminating).
- durability:  P(durable | epigenome) = 1 - P(silenced), the mouse-trained conditional function APPLIED
               to the human epigenome's histone marks (the cell-type-transfer the design hinges on).
- reachability: WT-KB writer set + tier (Tier-1 reprogrammable writers are broadly available at 1 kb;
               fine-grained site choice is a design-time concern handled by the Planner).
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from pen_stack.wgenome.durability import CHROMATIN as DUR_MARKS
from pen_stack.wgenome.features import feature_columns


def load_pickle(path: str):
    with open(path, "rb") as fh:
        return pickle.load(fh)


def apply_safety(matrix: pd.DataFrame, safety_model) -> np.ndarray:
    feats = feature_columns(matrix)
    p_genotoxic = safety_model.predict_proba(matrix[feats].astype("float32").fillna(0.0))[:, 1]
    return 1.0 - p_genotoxic   # safety = 1 - risk


def apply_durability(matrix: pd.DataFrame, dur_models: dict) -> tuple[np.ndarray, np.ndarray]:
    """Apply the mouse-trained conditional function to the human epigenome's histone marks."""
    feats = [f for f in dur_models["features"] if f in matrix.columns]
    X = matrix[feats].astype("float32").fillna(0.0)
    expr = dur_models["reg"].predict(X)
    p_silenced = dur_models["clf"].predict_proba(X)[:, 1]
    return expr, 1.0 - p_silenced     # predicted expression, P(durable)


def build_writability(matrix: pd.DataFrame, safety_model, dur_models: dict,
                      w_safety: float = 0.5, w_durability: float = 0.5,
                      out_parquet: str | None = None) -> pd.DataFrame:
    out = matrix[["chrom", "bin"]].copy()
    out["safety"] = apply_safety(matrix, safety_model)
    expr, p_durable = apply_durability(matrix, dur_models)
    out["pred_expression"] = expr
    out["p_durable"] = p_durable
    # reachability: Tier-1 reprogrammable writers broadly available at locus level (honest annotation)
    out["reachable_tier1"] = "bridge_IS110;Cas9;Cas12a"
    # decomposable composite (documented weights; components above stay visible)
    out["writability"] = w_safety * out["safety"] + w_durability * out["p_durable"]
    if out_parquet:
        Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(out_parquet, index=False)
    return out


def rank_loci_near(writ_df: pd.DataFrame, chrom: str, start: int, end: int, k: int = 10) -> pd.DataFrame:
    """Inverse query seed (Phase-3 Planner): rank writable bins in a window."""
    w = writ_df.query("chrom == @chrom and bin*1000 >= @start and bin*1000 <= @end")
    return w.sort_values("writability", ascending=False).head(k)
