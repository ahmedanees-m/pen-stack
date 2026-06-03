"""Assemble the per-cell-type training/scoring matrix (Phase 1, bridge between 1A and 1B).

Joins the cell-type chromatin feature store + the (cell-type-agnostic) safety-annotation store
(+ integration-outcome store when available) on (chrom, bin) into one matrix the safety and
durability layers consume. Keeps feature provenance explicit.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Unified chromatin feature set: ONE accessibility feature (ATAC where present, else DNase) +
# the 5 core histone marks. This makes every cell type share an IDENTICAL schema, so a cell type
# that lacks a specific accessibility assay (e.g. CD34+ HSPC has DNase but no ATAC) is fully
# specified rather than "partial" - ATAC and DNase are interchangeable open-chromatin assays.
CHROMATIN_TRACKS = ["accessibility", "H3K27ac", "H3K4me1", "H3K4me3", "H3K9me3", "H3K27me3"]
ACCESS_SOURCES = ["atac", "dnase"]
SAFETY_DIST = ["dist_oncogene", "dist_tsg", "dist_essential", "dist_tss"]


def add_accessibility(m: pd.DataFrame) -> pd.DataFrame:
    """Derive the unified `accessibility` column: prefer ATAC, fall back to DNase."""
    if "accessibility" not in m.columns:
        if "atac" in m.columns:
            m["accessibility"] = m["atac"]
            if "dnase" in m.columns:                      # fill any ATAC gaps with DNase
                m["accessibility"] = m["accessibility"].fillna(m["dnase"])
        elif "dnase" in m.columns:
            m["accessibility"] = m["dnase"]
    return m


def _log_dist(s: pd.Series) -> pd.Series:
    # large/Inf for "no feature on chromosome" -> log1p of a capped distance; NaN -> max
    v = s.fillna(s.max() if s.notna().any() else 1e8).clip(lower=0)
    return np.log1p(v)


def assemble_matrix(chromatin_parquet: str, safety_parquet: str,
                    integration_parquet: str | None = None,
                    out_parquet: str | None = None) -> pd.DataFrame:
    chrom = pd.read_parquet(chromatin_parquet)
    safe = pd.read_parquet(safety_parquet)
    m = chrom.merge(safe, on=["chrom", "bin"], how="inner")
    m = add_accessibility(m)                               # unify ATAC/DNase -> accessibility

    # log-scaled distance features (raw kept too, for transparency)
    for d in SAFETY_DIST:
        if d in m.columns:
            m[f"log_{d}"] = _log_dist(m[d])

    if integration_parquet and Path(integration_parquet).exists():
        integ = pd.read_parquet(integration_parquet)
        m = m.merge(integ, on=["chrom", "bin"], how="left")
        for c in [c for c in integ.columns if c not in ("chrom", "bin")]:
            m[c] = m[c].fillna(0)

    if out_parquet:
        Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
        m.to_parquet(out_parquet, index=False)
    return m


def resolve_integration(feat_dir: str, ct: str) -> str | None:
    """Integration-feature parquet for a cell type: prefer the cell-type-specific MLV set
    (LaFave K562/HepG2); fall back to the cell-type-agnostic VISDB retroviral-propensity track so a
    cell type without its own integration assay (e.g. CD34+ HSPC) still gets an integration feature."""
    ct_specific = Path(feat_dir) / f"integration_{ct}.parquet"
    if ct_specific.exists():
        return str(ct_specific)
    fallback = Path(feat_dir) / "integration_density.parquet"
    return str(fallback) if fallback.exists() else None


def feature_columns(df: pd.DataFrame) -> list[str]:
    """The model feature set: chromatin marks + log-distances + any integration features."""
    feats = [c for c in CHROMATIN_TRACKS if c in df.columns]
    feats += [c for c in df.columns if c.startswith("log_dist_")]
    feats += [c for c in df.columns if c.startswith("integ_")]
    return feats
