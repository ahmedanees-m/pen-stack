"""Reject-known-bad genotoxicity blocklist.

A DETERMINISTIC overlay, not a predictor: any 1 kb bin within `cis_window_bp` of a gene at which vector
integration was associated with clonal expansion / oncogenesis in a human gene-therapy trial is flagged
unsafe by RULE (safety := 0.0), overriding the soft atlas safety model. The curated list of documented loci
lives in `configs/safety/genotoxic_loci.yaml` (sourced from the 2025 Leukemia genotoxicity review + the
primary trial reports, not from any benchmark).

This closes the safety filter's false negatives: before this overlay the soft model scored BMI1/SETBP1/MN1 as
safe (BMI1 at the 99.9th writability percentile) because those genes were absent from the narrow six-gene
training label. It is a completeness fix for a blocklist, NOT a claim that the model predicts genotoxicity for
novel loci -- a blocklist cannot be validated on its own contents.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
import yaml

from pen_stack._resources import resource

BIN_BP = 1000
_CONFIG_REL = "configs/safety/genotoxic_loci.yaml"


@lru_cache(maxsize=1)
def blocklist_config() -> dict:
    return yaml.safe_load(resource(_CONFIG_REL).read_text(encoding="utf-8"))


def _gene_coords() -> pd.DataFrame:
    from pen_stack.planner.optimize import gene_coords_path
    return pd.read_parquet(gene_coords_path())


@lru_cache(maxsize=1)
def blocklisted_bins() -> dict[tuple[str, int], dict]:
    """Map every (chrom, bin) within the CIS window of a documented genotoxic gene -> its metadata.

    Resolved once from the curated gene list x gene_coords.parquet, then cached. A gene that does not resolve
    is skipped (never silently dropping the safety signal for one that does)."""
    cfg = blocklist_config()
    window = int(cfg.get("cis_window_bp", 50000))
    gc = _gene_coords().set_index("gene")
    out: dict[tuple[str, int], dict] = {}
    for rec in cfg.get("loci", []):
        gene = rec["gene"]
        if gene not in gc.index:
            continue
        g = gc.loc[gene]
        g = g.iloc[0] if isinstance(g, pd.DataFrame) else g
        lo_bp = max(0, int(g["start"]) - window)
        hi_bp = int(g["end"]) + window
        meta = {"gene": gene, "severity": rec.get("severity"), "citation": rec.get("citation")}
        for b in range(lo_bp // BIN_BP, hi_bp // BIN_BP + 1):
            out[(str(g["chrom"]), b)] = meta
    return out


def is_genotoxic_locus(chrom: str, pos_bp: int) -> dict | None:
    """Point query: the documented-genotoxic-gene metadata if `pos_bp` falls in a blocklisted bin, else None."""
    return blocklisted_bins().get((str(chrom), int(pos_bp) // BIN_BP))


def apply_genotoxic_blocklist(df: pd.DataFrame, *, w_safety: float = 0.5,
                              w_durability: float = 0.5) -> pd.DataFrame:
    """Overlay the reject-known-bad blocklist onto a writability frame (needs `chrom`, `bin`, `safety`).

    For blocklisted bins: safety -> 0.0, add `genotoxic_blocklist` (True) + `genotoxic_blocklist_gene`, and
    recompute `writability` with the zeroed safety so a documented locus can never rank as writable. Idempotent
    and a no-op if the frame lacks the required columns (e.g. a non-atlas frame)."""
    if df.empty or not {"chrom", "bin", "safety"}.issubset(df.columns):
        return df
    bl = blocklisted_bins()
    if not bl:
        return df
    df = df.copy()
    keys = list(zip(df["chrom"].astype(str), df["bin"].astype(int)))
    mask = pd.Series([k in bl for k in keys], index=df.index)
    df["genotoxic_blocklist"] = mask
    if not mask.any():
        return df
    df["genotoxic_blocklist_gene"] = [bl.get(k, {}).get("gene") for k in keys]
    df.loc[mask, "safety"] = 0.0
    if {"p_durable", "writability"}.issubset(df.columns):
        df.loc[mask, "writability"] = (w_safety * 0.0 + w_durability * df.loc[mask, "p_durable"])
    return df
