"""WS-F1 - ingest a user's private assay into per-site labels matching the model's feature schema.

The runnable in-code path is TABULAR: a CSV/TSV/Parquet of sites + an outcome label (and, optionally, the
released-model score column or the per-bin features to attach). The upstream FASTQ/BAM -> per-site label
derivation (integration-site sequencing, GUIDE-seq, expression-stability profiling) is documented in
docs/private_data_formats.md and runs in the Docker image with the usual aligners; it produces exactly the
tabular schema this module validates, so the two halves compose.

Schema (standardized output): chrom, bin, ct, label, [score], [features...]
  * label: 0/1 (discrimination) or a real value in [0,1] (calibration target).
  * score: the released model's output for that site (safety / p_durable / writability) - the thing we
    recalibrate. If absent, attach_features() joins it from the writability atlas.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BIN_BP = 1000
REQUIRED = ("chrom", "label")            # plus one of {bin, pos}


def load_user_labels(path: str | Path) -> pd.DataFrame:
    """Load + validate a user label table (.csv/.tsv/.parquet). Returns a frame with chrom, bin, ct, label."""
    p = Path(path)
    if p.suffix in (".parquet", ".pq"):
        df = pd.read_parquet(p)
    else:
        df = pd.read_csv(p, sep="\t" if p.suffix in (".tsv", ".txt") else ",")
    return normalize(df)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Validate columns and standardize: derive `bin` from `pos` if needed; coerce label; default ct."""
    df = df.copy()
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"user table missing required columns: {missing} (have {list(df.columns)})")
    if "bin" not in df.columns:
        if "pos" not in df.columns:
            raise ValueError("user table needs a 'bin' or a 'pos' column to locate each site")
        df["bin"] = (df["pos"].astype(int) // BIN_BP).astype(int)
    if "ct" not in df.columns:
        df["ct"] = "user"
    lab = pd.to_numeric(df["label"], errors="coerce")
    if lab.isna().any():
        raise ValueError("label column has non-numeric / missing values")
    if not (((lab == 0) | (lab == 1)).all() or ((lab >= 0) & (lab <= 1)).all()):
        raise ValueError("label must be binary {0,1} or a probability in [0,1]")
    df["label"] = lab.astype(float)
    keep = ["chrom", "bin", "ct", "label"] + [c for c in df.columns
                                              if c not in ("chrom", "bin", "ct", "label", "pos")]
    return df[keep].reset_index(drop=True)


def attach_features(df: pd.DataFrame, target: str = "safety", ct: str = "k562") -> pd.DataFrame:
    """Join the released model's score for `target` (safety|p_durable|writability) from the Phase-1 atlas.

    No-op if the score column is already present (user supplied it). Raises if the atlas is unavailable and
    no score column exists - the caller then supplies scores directly.
    """
    col = {"safety": "safety", "durability": "p_durable", "p_durable": "p_durable",
           "writability": "writability"}.get(target, target)
    if col in df.columns and df[col].notna().any():
        return df.rename(columns={col: "score"}) if col != "score" else df
    if "score" in df.columns:
        return df
    atlas = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / f"atlas_{ct}.parquet"
    if not atlas.exists():
        raise FileNotFoundError(
            f"no '{col}'/'score' column and Phase-1 atlas absent ({atlas}); supply the released-model score "
            "column in the user table, or run inside the image where the atlas is mounted.")
    a = pd.read_parquet(atlas, columns=["chrom", "bin", col])
    out = df.merge(a, on=["chrom", "bin"], how="left").rename(columns={col: "score"})
    if out["score"].isna().any():
        out = out.dropna(subset=["score"]).reset_index(drop=True)
    return out


def schema_summary(df: pd.DataFrame) -> dict:
    return {"n_sites": int(len(df)), "n_chroms": int(df["chrom"].nunique()),
            "label_kind": "binary" if set(np.unique(df["label"])) <= {0.0, 1.0} else "continuous",
            "positive_rate": round(float(df["label"].mean()), 4),
            "has_score": "score" in df.columns}
