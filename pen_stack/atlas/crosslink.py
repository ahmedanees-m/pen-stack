"""Cross-link the Writer Atlas <-> the Writable Genome (Phase 2, Step 2.5).

The integration that makes PEN-STACK more than a catalogue: bidirectional queries between writers (the
Phase-2 atlas, 33k systems by family) and loci (the Phase-1 Writable Genome, 3M bins x cell type with a
``reachable_tier1`` annotation + a decomposable ``writability`` score).

- ``loci_for_writer(family, ct)``  -> loci that family can reach, ranked by writability.
- ``writers_for_locus(chrom, bin)`` -> atlas systems whose family reaches that locus, with readiness.
- ``loci_for_gene(gene, ct)``       -> writable bins overlapping a gene (forward query helper).

Honest scope (Phase-1 D1.8-1): reachability is released at the *locus* level - the Tier-1
reprogrammable families (bridge_IS110 / Cas9 / Cas12a) are near-universal at 1 kb, so the cross-link's
discriminating signal is the *writability ranking* and the *family -> atlas-system* join (each carrying
therapeutic readiness). Per-site reachability (does a specific bridge core exist here?) is Planner work.

Inputs : Phase-1 atlas_<ct>.parquet (chrom, bin, safety, p_durable, reachable_tier1, writability),
         the Phase-2 atlas.parquet, gene_coords.parquet.
Outputs: out/crosslink_cache_<ct>.parquet (per-family reachable-loci summary).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
_FINAL = _ROOT.parent                          # Final_Part_v3.0/
_ATLAS = _ROOT / "pen_stack" / "atlas" / "atlas.parquet"
_OUT = _ROOT / "out"
BIN_BP = 1000

# Phase-1 writability atlas can live in a few places (fetched-not-committed). First match wins.
# PEN_ATLAS_DIR (also used by the UI) is honoured first so every cross-link-backed feature - the Write
# Planner, the agent, and the RAG numeric route - finds the same atlas the UI does in any deployment.
def _writability_search() -> list[Path]:
    bases: list[Path] = []
    env = os.environ.get("PEN_ATLAS_DIR")
    if env:
        bases.append(Path(env))
    bases += [_ROOT / "data" / "out", _FINAL / "phase_1" / "out"]
    return bases


def writability_path(ct: str) -> Path:
    bases = _writability_search()
    for base in bases:
        p = base / f"atlas_{ct}.parquet"
        if p.exists():
            return p
    raise FileNotFoundError(f"atlas_{ct}.parquet not found in {[str(b) for b in bases]}")


@lru_cache(maxsize=4)
def load_writability(ct: str) -> pd.DataFrame:
    df = pd.read_parquet(writability_path(ct))
    df["_reach"] = df["reachable_tier1"].fillna("").str.split(";")
    return df


@lru_cache(maxsize=1)
def load_writer_atlas() -> pd.DataFrame:
    return pd.read_parquet(_ATLAS)


def reachable_families(ct: str) -> set[str]:
    """The writer families annotated as Tier-1 reachable in the Phase-1 atlas for this cell type."""
    df = load_writability(ct)
    fams: set[str] = set()
    for r in df["reachable_tier1"].dropna().unique():
        fams.update(x for x in str(r).split(";") if x)
    return fams


def loci_for_writer(family: str, ct: str = "k562", top: int = 20) -> pd.DataFrame:
    """Top-writability loci reachable by a writer family (genomic coords + writability components)."""
    df = load_writability(ct)
    mask = df["_reach"].apply(lambda fams: family in fams)
    hit = df.loc[mask].nlargest(top, "writability").copy()
    hit["chrom_start"] = hit["bin"] * BIN_BP
    return hit[["chrom", "bin", "chrom_start", "safety", "p_durable", "writability", "reachable_tier1"]]


def writers_for_locus(chrom: str, bin_idx: int, ct: str = "k562") -> pd.DataFrame:
    """Atlas systems whose family reaches a locus, with therapeutic readiness (if scored)."""
    df = load_writability(ct)
    row = df[(df["chrom"] == chrom) & (df["bin"] == bin_idx)]
    if row.empty:
        return pd.DataFrame()
    fams = {x for x in str(row.iloc[0]["reachable_tier1"]).split(";") if x}
    atlas = load_writer_atlas()
    cols = [c for c in ["representative_system", "family", "confidence", "deliv_class",
                        "readiness", "cargo_capacity_bp", "reachability_tier"] if c in atlas.columns]
    out = atlas[atlas["family"].isin(fams)][cols].copy()
    out["locus_writability"] = float(row.iloc[0]["writability"])
    return out


def loci_for_gene(gene: str, ct: str = "k562", gene_coords: str | Path | None = None) -> pd.DataFrame:
    """Writable bins overlapping a gene body (forward query helper)."""
    if gene_coords:
        gc_path = Path(gene_coords)
    else:
        from pen_stack.planner.optimize import gene_coords_path
        gc_path = gene_coords_path()
    gc = pd.read_parquet(gc_path)
    g = gc[gc["gene"] == gene]
    if g.empty:
        return pd.DataFrame()
    r = g.iloc[0]
    df = load_writability(ct)
    lo, hi = int(r["start"]) // BIN_BP, int(r["end"]) // BIN_BP
    return df[(df["chrom"] == r["chrom"]) & (df["bin"].between(lo, hi))].sort_values(
        "writability", ascending=False)


def build_crosslink_cache(ct: str = "k562", out: str | Path | None = None) -> pd.DataFrame:
    """Per-family reachable-loci summary (count + median writability + top bin), cached."""
    df = load_writability(ct)
    rows = []
    for fam in sorted(reachable_families(ct)):
        sub = df[df["_reach"].apply(lambda fams, f=fam: f in fams)]
        top = sub.nlargest(1, "writability")
        rows.append({
            "family": fam, "cell_type": ct, "n_reachable_loci": len(sub),
            "median_writability": round(float(sub["writability"].median()), 4),
            "top_chrom": top.iloc[0]["chrom"], "top_bin": int(top.iloc[0]["bin"]),
            "top_writability": round(float(top.iloc[0]["writability"]), 4),
        })
    cache = pd.DataFrame(rows)
    out = Path(out) if out else _OUT / f"crosslink_cache_{ct}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    cache.to_parquet(out, index=False)
    return cache


if __name__ == "__main__":  # pragma: no cover
    for ct in ("k562", "hepg2", "hspc"):
        try:
            c = build_crosslink_cache(ct)
            print(f"[{ct}] crosslink cache:\n{c.to_string(index=False)}\n")
        except Exception as e:  # noqa: BLE001 - a missing/partial cell-type atlas is non-fatal
            print(f"[{ct}] skip: {e}")
