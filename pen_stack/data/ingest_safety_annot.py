"""Safety annotations per 1 kb bin (Phase 1, Step 1.4).

Builds per-bin safety features from COSMIC Cancer Gene Census (oncogene/TSG loci),
DepMap CRISPRGeneEffect (essential genes), and GENCODE (gene/TSS distances):
  - dist_oncogene, dist_tsg, dist_essential, dist_tss  (bp to nearest, via bedtools closest)
  - genotoxic_cis flag (bins within a window of LMO2/MECOM/CCND2/PRDM16/HMGA2)

Inputs are staged on the VM under /data/external (COSMIC tsv, DepMap csv); GENCODE is downloaded.
Runs CPU-only in the penstack:phase1 image (bedtools in-image). Output keyed on (chrom, bin).
"""
from __future__ import annotations

import argparse
import gzip
import os
from pathlib import Path

import pandas as pd
import pybedtools
import requests

from pen_stack.data.genome import MAIN_CHROMS, load_chrom_sizes

GENCODE_GTF = ("https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/"
               "release_46/gencode.v46.basic.annotation.gtf.gz")
GENOTOXIC = ["LMO2", "MECOM", "EVI1", "CCND2", "PRDM16", "HMGA2"]
BIN_BP = 1000
CIS_WINDOW = 50000  # bp window around a genotoxic gene to flag


def _chr(c: str) -> str:
    c = str(c)
    return c if c.startswith("chr") else f"chr{c}"


def load_cosmic(tsv: str) -> pd.DataFrame:
    df = pd.read_csv(tsv, sep="\t", dtype=str)
    df = df.dropna(subset=["CHROMOSOME", "GENOME_START", "GENOME_STOP"])
    df["chrom"] = df["CHROMOSOME"].map(_chr)
    df["start"] = pd.to_numeric(df["GENOME_START"], errors="coerce")
    df["end"] = pd.to_numeric(df["GENOME_STOP"], errors="coerce")
    df = df.dropna(subset=["start", "end"])
    df["role"] = df.get("ROLE_IN_CANCER", "").fillna("")
    df = df[df["chrom"].isin(MAIN_CHROMS)]
    df["start"] = df["start"].astype(int)
    df["end"] = df["end"].astype(int)
    return df[["chrom", "start", "end", "GENE_SYMBOL", "role"]]


def load_depmap_essential(csv: str, thresh: float = -0.5) -> set[str]:
    """Common-essential genes: mean Chronos effect across cell lines < thresh."""
    df = pd.read_csv(csv, index_col=0)
    means = df.mean(axis=0)
    genes = {c.split(" (")[0] for c, m in means.items() if m < thresh}
    return genes


def download_gencode(dest: str, url: str = GENCODE_GTF) -> str:
    if not (os.path.exists(dest) and os.path.getsize(dest) > 0):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for ch in r.iter_content(1 << 20):
                    fh.write(ch)
    return dest


def parse_gencode_genes(gtf_gz: str) -> pd.DataFrame:
    rows = []
    with gzip.open(gtf_gz, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if f[2] != "gene":
                continue
            chrom = f[0]
            if chrom not in MAIN_CHROMS:
                continue
            start, end, strand = int(f[3]), int(f[4]), f[6]
            attrs = f[8]
            name = ""
            for kv in attrs.split(";"):
                kv = kv.strip()
                if kv.startswith("gene_name"):
                    name = kv.split('"')[1]
                    break
            tss = start if strand == "+" else end
            rows.append((chrom, start, end, strand, name, tss))
    return pd.DataFrame(rows, columns=["chrom", "start", "end", "strand", "gene_name", "tss"])


def _bed(df: pd.DataFrame, cols=("chrom", "start", "end")) -> pybedtools.BedTool:
    b = df[list(cols)].copy()
    b.columns = ["chrom", "start", "end"]
    b = b.sort_values(["chrom", "start"])
    return pybedtools.BedTool.from_dataframe(b)


def nearest_dist(bins_bed: pybedtools.BedTool, feat_df: pd.DataFrame, name: str) -> pd.DataFrame:
    if feat_df.empty:
        return pd.DataFrame(columns=["chrom", "start", name])
    fb = _bed(feat_df).sort()
    closest = bins_bed.closest(fb, d=True)
    out = closest.to_dataframe(header=None, usecols=[0, 1, closest.field_count() - 1],
                               names=["chrom", "start", name])
    out[name] = out[name].clip(lower=0)
    return out.groupby(["chrom", "start"], as_index=False)[name].min()


def build(bin_grid: str, cosmic_tsv: str, depmap_csv: str, gencode_dest: str,
          sizes_tsv: str, out_parquet: str) -> pd.DataFrame:
    grid = pd.read_parquet(bin_grid)[["chrom", "start", "bin"]]
    bins_bed = _bed(grid.assign(end=grid["start"] + BIN_BP)).sort()

    cosmic = load_cosmic(cosmic_tsv)
    onco = cosmic[cosmic["role"].str.contains("oncogene", case=False, na=False)]
    tsg = cosmic[cosmic["role"].str.contains("TSG", case=False, na=False)]

    gtf = download_gencode(gencode_dest)
    genes = parse_gencode_genes(gtf)
    ess_syms = load_depmap_essential(depmap_csv)
    ess = genes[genes["gene_name"].isin(ess_syms)]

    out = grid.copy()
    for nm, fdf in [("dist_oncogene", onco), ("dist_tsg", tsg),
                    ("dist_essential", ess), ("dist_tss", genes.assign(end=genes["tss"] + 1, start=genes["tss"]))]:
        d = nearest_dist(bins_bed, fdf, nm)
        out = out.merge(d, on=["chrom", "start"], how="left")

    # genotoxic CIS flag
    gtox = genes[genes["gene_name"].isin(GENOTOXIC)].copy()
    gtox["start"] = (gtox["start"] - CIS_WINDOW).clip(lower=0)
    gtox["end"] = gtox["end"] + CIS_WINDOW
    gflag = nearest_dist(bins_bed, gtox, "dist_gtox")
    out = out.merge(gflag, on=["chrom", "start"], how="left")
    out["genotoxic_cis"] = (out["dist_gtox"].fillna(1e9) == 0)

    Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_parquet, index=False)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin-grid", default="/data/features/bin_grid_1kb.parquet")
    ap.add_argument("--cosmic", default="/data/external/Cosmic_CancerGeneCensus_v104_GRCh38.tsv")
    ap.add_argument("--depmap", default="/data/external/CRISPRGeneEffect.csv")
    ap.add_argument("--gencode", default="/data/raw/gencode.v46.basic.gtf.gz")
    ap.add_argument("--sizes", default="/data/raw/hg38.chrom.sizes")
    ap.add_argument("--out", default="/data/features/safety_annot.parquet")
    a = ap.parse_args()
    df = build(a.bin_grid, a.cosmic, a.depmap, a.gencode, a.sizes, a.out)
    n_onco = (df["dist_oncogene"] == 0).sum()
    print(f"safety_annot bins={len(df)} cols={[c for c in df.columns if c.startswith('dist') or c=='genotoxic_cis']}")
    print(f"bins in an oncogene={n_onco} genotoxic_cis bins={int(df['genotoxic_cis'].sum())}")


if __name__ == "__main__":
    main()
