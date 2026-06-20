"""Therapeutic-readiness scoring across families (Phase 2, Step 2.3).

The motto's "therapeutic-ready" axis, realised and *measured*: score every Writer-Atlas system for
deliverability, cargo capacity, immunogenicity proxy, and human-cell compatibility - using the Phase-0
re-grounded axes (configs/score_axes.yaml is the single source of thresholds; no per-enzyme overrides).
All components are retained on the row (a transparent profile, never collapsed to one opaque number).

Inputs : pen_stack/atlas/atlas.parquet, configs/score_axes.yaml.
Outputs: atlas.parquet updated with deliv_class / S_Deliv / S_Cargo / S_HumanCell / readiness.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pen_stack.score.recalibrate import load_axes_config

_ROOT = Path(__file__).resolve().parents[2]
_ATLAS = _ROOT / "pen_stack" / "atlas" / "atlas.parquet"


def deliverability_class(length_aa: float | None, cfg: dict) -> str:
    """AAV single (<=~730 aa effector) / split-AAV (<=1500) / mRNA-RNP, from effector size."""
    d = cfg["deliverability"]
    if length_aa is None or (isinstance(length_aa, float) and np.isnan(length_aa)):
        return "unknown"
    L = float(length_aa)
    if L <= d["aav_single_max_aa"]:
        return "AAV"
    if L <= d["split_aav_max_aa"]:
        return "split-AAV"
    return "mRNA-RNP"


def _s_cargo(bp, cfg) -> float:
    cap = float(cfg["cargo"]["cap_bp"])
    if bp is None or (isinstance(bp, float) and np.isnan(bp)) or bp <= 0:
        return np.nan
    return float(np.log1p(min(float(bp), cap)) / np.log1p(cap))


def _s_humancell(hca: str | None) -> float:
    """Coarse human-cell compatibility from the curated activity string (measured > demonstrated > none)."""
    t = (hca or "").lower()
    if "not measured" in t or "bacterial" in t:
        return 0.0
    if "low in human" in t or "modest" in t:
        return 0.4
    if "human cell" in t or "human cells" in t or "primary t cell" in t or "hepatocyte" in t or "clinical" in t:
        return 1.0
    return np.nan


def therapeutic_profile(atlas_df: pd.DataFrame, cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_axes_config()
    df = atlas_df.copy()
    classes = cfg["deliverability"]["classes"]

    df["deliv_class"] = df["length_aa"].apply(lambda L: deliverability_class(L, cfg))
    df["S_Deliv"] = df["deliv_class"].map(classes) # unknown -> NaN
    df["S_Cargo"] = df["cargo_capacity_bp"].apply(lambda bp: _s_cargo(bp, cfg))
    df["S_HumanCell"] = df["human_cell_activity"].apply(_s_humancell)
    df["S_DSBfree"] = df["dsb_free"].apply(lambda b: 1.0 if b is True else (0.0 if b is False else np.nan))

    # transparent composite (mean of available components); components remain on the row
    comp = df[["S_Deliv", "S_Cargo", "S_HumanCell", "S_DSBfree"]]
    df["readiness"] = comp.mean(axis=1, skipna=True)
    return df


def apply_to_atlas(atlas_parquet: str | Path = _ATLAS, out: str | Path = _ATLAS) -> pd.DataFrame:
    atlas = pd.read_parquet(atlas_parquet)
    out_df = therapeutic_profile(atlas)
    out_df.to_parquet(out, index=False)
    return out_df


if __name__ == "__main__": # pragma: no cover
    a = apply_to_atlas()
    cores = a[a.entry_kind == "curated_core"]
    print(cores[["representative_system", "length_aa", "deliv_class", "S_Deliv",
                 "S_Cargo", "S_HumanCell", "readiness"]].to_string(index=False))
    print("\ndeliv_class distribution:\n", a["deliv_class"].value_counts(dropna=False))
