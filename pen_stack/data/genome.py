"""hg38 genome scaffolding (Phase 1, Step 1.1 foundation).

Fetches hg38 chromosome sizes and builds the canonical 1 kb bin grid (autosomes + X) that every
feature store is keyed on. Pure-CPU, small; runs in any container.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

UCSC_CHROM_SIZES = "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.chrom.sizes"
MAIN_CHROMS = [f"chr{i}" for i in range(1, 23)] + ["chrX"]
BIN_BP = 1000


def fetch_chrom_sizes(out_tsv: str | Path, url: str = UCSC_CHROM_SIZES,
                      chroms: list[str] = MAIN_CHROMS) -> dict[str, int]:
    txt = requests.get(url, timeout=60).text
    sizes = {}
    for line in txt.splitlines():
        if not line.strip():
            continue
        c, n = line.split("\t")[:2]
        if c in chroms:
            sizes[c] = int(n)
    sizes = {c: sizes[c] for c in chroms if c in sizes}   # canonical order
    Path(out_tsv).parent.mkdir(parents=True, exist_ok=True)
    Path(out_tsv).write_text("".join(f"{c}\t{n}\n" for c, n in sizes.items()))
    return sizes


def build_bin_grid(chrom_sizes: dict[str, int], out_parquet: str | Path | None = None,
                   bin_bp: int = BIN_BP) -> pd.DataFrame:
    rows = []
    for c, n in chrom_sizes.items():
        nbins = n // bin_bp
        starts = range(0, nbins * bin_bp, bin_bp)
        rows.append(pd.DataFrame({"chrom": c, "start": starts}))
    grid = pd.concat(rows, ignore_index=True)
    grid["end"] = grid["start"] + bin_bp
    grid["bin"] = grid["start"] // bin_bp
    if out_parquet:
        Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
        grid.to_parquet(out_parquet, index=False)
    return grid


def load_chrom_sizes(tsv: str | Path) -> dict[str, int]:
    out = {}
    for line in Path(tsv).read_text().splitlines():
        if line.strip():
            c, n = line.split("\t")[:2]
            out[c] = int(n)
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes-out", default="/data/raw/hg38.chrom.sizes")
    ap.add_argument("--grid-out", default="/data/features/bin_grid_1kb.parquet")
    a = ap.parse_args()
    sizes = fetch_chrom_sizes(a.sizes_out)
    grid = build_bin_grid(sizes, a.grid_out)
    print(f"chroms={len(sizes)} total_bins={len(grid)} -> {a.grid_out}")


if __name__ == "__main__":
    main()
