"""Acquire / load the bridge-recombinase training data (Phase 1.5, Step 1.5.1).

Three tables supervise the engine: the measured **off-target profile** (per-position mismatch tolerance),
the **DMS** (variant->activity), and the **72-system human-cell activity screen**. The Perry 2025
supplementary (Science adz0276) is paywalled and not bulk-downloadable from the build environment; the
loaders below read the real tables when supplied, and otherwise fall back to the literature-grounded
position-weight profile (`configs/bridge_offtarget_profile.yaml`) so the engine runs end-to-end.

Outputs (when real tables are present): features/bridge_offtarget_profile.parquet, bridge_dms.parquet,
bridge_screen.parquet.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_CFG = _ROOT / "configs" / "bridge_offtarget_profile.yaml"

# Perry 2025 supplementary (Science adz0276) - copyrighted; kept LOCAL, never committed/redistributed.
# Default location: Final_Part_v3.0/Perry_et_al/ (override with PEN_PERRY_DIR).
_PERRY_FILES = {
    "orthologs": "science.adz0276_table_s1.xlsx", # S1: 72 bridge recombinase orthologs
    "offtargets": "science.adz0276_table_s2.xlsx", # S2: genome-wide insertion sites (off-targets)
    "dms": "science.adz0276_table_s3.xlsx", # S3: deep mutational scan
}


def perry_dir() -> Path | None:
    env = os.environ.get("PEN_PERRY_DIR")
    for cand in ([Path(env)] if env else []) + [_ROOT.parent / "Perry_et_al"]:
        if cand.exists():
            return cand
    return None


def _perry(name: str) -> Path | None:
    d = perry_dir()
    if d is None:
        return None
    p = d / _PERRY_FILES[name]
    return p if p.exists() else None


@lru_cache(maxsize=1)
def load_profile_config(path: str | Path = _CFG) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def protective_weights() -> dict[int, float]:
    """Per-position protective weight (1 = mismatch abolishes recombination; 0 = fully tolerated)."""
    cfg = load_profile_config()
    return {int(k): float(v) for k, v in cfg["protective_weight"].items()}


def load_insertion_sites() -> pd.DataFrame:
    """Perry 2025 Table S2 - measured genome-wide insertion sites (on- + off-target). Empty if absent.

    Columns include Intended_Site_Name, Plasmid_Encoded_Sequence (the intended 14-nt target),
    Insertion_Site, Insertion_Site_Sequence (measured 14-nt), UMI_Count, %_of_Insertions, On-Target.
    """
    p = _perry("offtargets")
    if p is None:
        return pd.DataFrame()
    df = pd.read_excel(p, sheet_name="Genome Wide Insertion Sites")
    return df.dropna(subset=["Insertion_Site_Sequence", "Plasmid_Encoded_Sequence"])


_MEASURED_PARQUET = _ROOT / "data" / "curated" / "bridge_offtarget_profile_measured.parquet"


def load_measured_profile() -> pd.DataFrame:
    """The MEASURED per-position profile. Prefers the committed derived parquet (available everywhere via
    git); otherwise re-derives from the raw Perry tables (local only). Empty if neither is present."""
    if _MEASURED_PARQUET.exists():
        return pd.read_parquet(_MEASURED_PARQUET)
    return derive_measured_profile()


def derive_measured_profile() -> pd.DataFrame:
    """Per-position protective weight derived from the MEASURED off-targets (UMI-weighted conservation).

    Among real off-targets (which recombined despite mismatches), positions that stay matched are the
    specificity determinants (high protective weight); frequently-mismatched positions are tolerant.
    Returns cols: position(1-based), conservation, protective_weight, source. Empty if Perry data absent.
    """
    s2 = load_insertion_sites()
    if s2.empty:
        return pd.DataFrame()
    off = s2[(s2["On-Target"] == False) & # noqa: E712
             (s2["Insertion_Site_Sequence"].str.len() == 14) &
             (s2["Plasmid_Encoded_Sequence"].str.len() == 14)]
    L = 14
    match = [0.0] * L
    tot = 0.0
    for seq, intended, umi in zip(off["Insertion_Site_Sequence"], off["Plasmid_Encoded_Sequence"],
                                  off["UMI_Count"]):
        w = float(umi)
        for j in range(L):
            if seq[j] == intended[j]:
                match[j] += w
        tot += w
    cons = [m / tot for m in match]
    return pd.DataFrame({"position": list(range(1, L + 1)), "conservation": cons,
                         "protective_weight": cons, "source": "perry2025_table_s2_measured",
                         "n_offtargets": len(off)})


def load_offtarget_profile(use_measured: bool = True) -> pd.DataFrame:
    """Measured profile (Perry S2) if available and requested, else the literature position weights."""
    if use_measured:
        m = derive_measured_profile()
        if not m.empty:
            return m.rename(columns={"protective_weight": "_pw"}).assign(
                rel_recombination=lambda d: 1 - d["_pw"]).drop(columns="_pw")
    w = protective_weights()
    return pd.DataFrame({"position": list(w), "rel_recombination": [1 - v for v in w.values()],
                         "source": "literature_position_weights"})


def load_dms() -> pd.DataFrame:
    """Perry 2025 Table S3 - deep mutational scan (Position, Mutation, Z_Score_wrt_WT). Empty if absent."""
    p = _perry("dms")
    if p is None:
        return pd.DataFrame(columns=["Position", "Mutation", "Z_Score_wrt_WT"])
    df = pd.read_excel(p, sheet_name="L2FC_Relative_Z-Scores")
    return df[df["Position"] != "All"].copy()


def load_screen() -> pd.DataFrame:
    """Perry 2025 Table S1 - 72 bridge recombinase orthologs (Name, sequences, Target, Donor). Empty if absent."""
    p = _perry("orthologs")
    if p is None:
        return pd.DataFrame(columns=["Name", "Recombinase_Sequence", "bRNA_Sequence", "Donor", "Target"])
    return pd.read_excel(p, sheet_name="Sheet1")
