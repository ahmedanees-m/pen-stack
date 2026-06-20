"""Export the Writable Genome atlas as genome-browser tracks (Phase 1, Step 1.11).

Writes per-cell-type BigWig tracks (writability, safety, p_durable) loadable in IGV/UCSC, plus a BED
of the top-writable loci. The atlas parquet stays the queryable source; these are the shareable tracks.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyBigWig

from pen_stack.data.genome import MAIN_CHROMS, load_chrom_sizes

BIN_BP = 1000
TRACKS = ["writability", "safety", "p_durable"]


def write_bigwig(df: pd.DataFrame, col: str, chrom_sizes: dict[str, int], out_bw: str) -> None:
    bw = pyBigWig.open(out_bw, "w")
    # header must be sorted; keep canonical chrom order with sizes
    chroms = [(c, chrom_sizes[c]) for c in MAIN_CHROMS if c in chrom_sizes]
    bw.addHeader(chroms)
    for chrom, _ in chroms:
        g = df[df["chrom"] == chrom].sort_values("bin")
        if g.empty:
            continue
        starts = (g["bin"].to_numpy() * BIN_BP).astype("int64")
        vals = g[col].astype("float64").fillna(0.0).to_numpy()
        bw.addEntries(chrom, list(starts), values=list(vals), span=BIN_BP, step=BIN_BP)
    bw.close()


def export_atlas(atlas_parquet: str, chrom_sizes_tsv: str, out_dir: str, ct: str,
                 top_n: int = 5000) -> dict:
    df = pd.read_parquet(atlas_parquet)
    sizes = load_chrom_sizes(chrom_sizes_tsv)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    written = {}
    for col in TRACKS:
        if col in df.columns:
            out_bw = f"{out_dir}/atlas_{ct}_{col}.bw"
            write_bigwig(df, col, sizes, out_bw)
            written[col] = out_bw
    # top-writable loci BED
    top = df.nlargest(top_n, "writability")[["chrom", "bin", "writability"]].copy()
    top["start"] = top["bin"] * BIN_BP
    top["end"] = top["start"] + BIN_BP
    bed = f"{out_dir}/atlas_{ct}_top{top_n}.bed"
    top[["chrom", "start", "end", "writability"]].to_csv(bed, sep="\t", header=False, index=False)
    written["top_bed"] = bed
    return written
