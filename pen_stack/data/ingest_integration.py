"""Integration-propensity features (Phase 1, Step 1.2).

Builds per-1 kb-bin retroviral integration density from VISDB integration tables (HIV, HTLV, MLV;
coordinates already lifted to hg38 in VISDB). Integration propensity reflects accessible/active
chromatin and is a feature for both the safety layer and "where insertions land".

NOTE (scope): VISDB's MLV set is tiny (~32 sites); the large >3.7M MLV-in-K562/HepG2 sets
referenced in the plan live in specific papers'/GEO supplements and are sourced separately. The
GENOTOXIC labels (clonal-outcome CIS) come from the clinical gene list (Step 1.4) - this module
supplies the integration-DENSITY feature, not the danger label.
"""
from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

from pen_stack.data.genome import MAIN_CHROMS

BIN_BP = 1000


def load_visdb(csv_dir: str) -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(os.path.join(csv_dir, "*.csv"))):
        virus = Path(f).stem
        df = pd.read_csv(f, dtype=str)
        cols = {c.lower().strip(): c for c in df.columns}
        chrom_c = cols.get("human chromosome")
        start_c = cols.get("hg38_start")
        if not chrom_c or not start_c:
            continue
        sub = pd.DataFrame({
            "chrom": df[chrom_c].astype(str).map(lambda c: c if c.startswith("chr") else f"chr{c}"),
            "pos": pd.to_numeric(df[start_c], errors="coerce"),
            "virus": virus,
        }).dropna(subset=["pos"])
        frames.append(sub)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["chrom", "pos", "virus"])
    out = out[out["chrom"].isin(MAIN_CHROMS)].copy()
    out["pos"] = out["pos"].astype(int)
    return out


def density_per_bin(integ: pd.DataFrame, bin_grid: str, out_parquet: str) -> pd.DataFrame:
    grid = pd.read_parquet(bin_grid)[["chrom", "bin"]]
    integ["bin"] = integ["pos"] // BIN_BP
    dens = integ.groupby(["chrom", "bin"]).size().rename("integ_density").reset_index()
    out = grid.merge(dens, on=["chrom", "bin"], how="left")
    out["integ_density"] = out["integ_density"].fillna(0).astype("int32")
    out["integ_log_density"] = np.log1p(out["integ_density"]).astype("float32")
    Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_parquet, index=False)
    return out


def lafave_density(bed_gz: str, chain_file: str, bin_grid: str, out_parquet: str) -> pd.DataFrame:
    """Cell-type-specific MLV integration density from a LaFave et al. 2014 BED (hg19 -> hg38 lift).

    The LaFave K562/HepG2 MLV integration BEDs are on hg19; lift each site to hg38 with the UCSC
    chain, then bin to 1 kb. This is the plan's >3.7M MLV-in-K562/HepG2 supervision (Bushman/NHGRI).
    """
    from pyliftover import LiftOver
    lo = LiftOver(chain_file)
    sites = []
    with __import__("gzip").open(bed_gz, "rt") as fh:
        for line in fh:
            if line.startswith("track") or not line.strip():
                continue
            f = line.split("\t")
            chrom, start = f[0], int(f[1])
            conv = lo.convert_coordinate(chrom, start)
            if conv:
                nc, npos = conv[0][0], conv[0][1]
                if nc in MAIN_CHROMS:
                    sites.append((nc, npos))
    integ = pd.DataFrame(sites, columns=["chrom", "pos"])
    print(f"lifted {len(integ)} / sites to hg38")
    out = density_per_bin(integ, bin_grid, out_parquet)
    out = out.rename(columns={"integ_density": "integ_mlv_density",
                              "integ_log_density": "integ_mlv_log_density"})
    out.to_parquet(out_parquet, index=False)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["visdb", "lafave"], default="visdb")
    ap.add_argument("--visdb-dir", default="/data/external/visdb")
    ap.add_argument("--lafave-bed", default=None)
    ap.add_argument("--chain", default="/data/external/hg19ToHg38.over.chain.gz")
    ap.add_argument("--bin-grid", default="/data/features/bin_grid_1kb.parquet")
    ap.add_argument("--out", default="/data/features/integration_density.parquet")
    a = ap.parse_args()
    if a.mode == "lafave":
        out = lafave_density(a.lafave_bed, a.chain, a.bin_grid, a.out)
        nz = int((out["integ_mlv_density"] > 0).sum())
        print(f"MLV density: bins={len(out)} nonzero={nz} max={int(out['integ_mlv_density'].max())} -> {a.out}")
        return
    integ = load_visdb(a.visdb_dir)
    print(f"loaded {len(integ)} integration sites; by virus: {integ['virus'].value_counts().to_dict()}")
    out = density_per_bin(integ, a.bin_grid, a.out)
    nz = int((out["integ_density"] > 0).sum())
    print(f"integration density: bins={len(out)} nonzero={nz} max={int(out['integ_density'].max())}")


if __name__ == "__main__":
    main()
