"""Chromatin feature store (Phase 1, Step 1.1).

Resolves the ENCODE bigWig panel for a cell type, downloads each track, bins it to the canonical
1 kb grid (mean signal per bin, per chromosome to bound memory), and writes one feature-store parquet.
Run in Docker on the VM; pull the parquet to Drive and clean the raw bigWigs.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyBigWig
import requests

from pen_stack.data.encode import resolve_panel
from pen_stack.data.genome import MAIN_CHROMS, load_chrom_sizes

BIN_BP = 1000


def download(href: str, dest: str | Path) -> Path:
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(href, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    return dest


def bin_bigwig(bw_path: str | Path, chrom_sizes: dict[str, int],
               chroms=MAIN_CHROMS, bin_bp=BIN_BP) -> pd.DataFrame:
    bw = pyBigWig.open(str(bw_path))
    frames = []
    bw_chroms = set(bw.chroms().keys())
    for c in chroms:
        if c not in chrom_sizes:
            continue
        n = chrom_sizes[c] // bin_bp
        name = c if c in bw_chroms else c.replace("chr", "")  # handle 'chr1' vs '1'
        if name not in bw_chroms:
            frames.append(pd.DataFrame({"chrom": c, "bin": range(n), "value": np.zeros(n)}))
            continue
        vals = bw.stats(name, 0, n * bin_bp, nBins=n, type="mean")
        v = np.array([0.0 if x is None else float(x) for x in vals], dtype="float32")
        frames.append(pd.DataFrame({"chrom": c, "bin": range(n), "value": v}))
    bw.close()
    return pd.concat(frames, ignore_index=True)


def build_feature_store(biosample: str, chrom_sizes_tsv: str, raw_dir: str,
                        out_parquet: str) -> pd.DataFrame:
    sizes = load_chrom_sizes(chrom_sizes_tsv)
    panel = resolve_panel(biosample)
    print(f"[{biosample}] resolved tracks: {list(panel.keys())}")
    base = None
    manifest = []
    for name, rec in panel.items():
        local = download(rec["href"], os.path.join(raw_dir, f"{biosample}_{name}_{rec['accession']}.bigWig"))
        df = bin_bigwig(local, sizes).rename(columns={"value": name})
        base = df if base is None else base.merge(df, on=["chrom", "bin"])
        manifest.append({"track": name, **{k: rec[k] for k in ("accession", "output_type")}})
        os.remove(local)   # 500 GB discipline: drop the raw bigWig after binning
        print(f"  binned {name} ({rec['accession']}), removed raw")
    base["biosample"] = biosample
    Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
    base.to_parquet(out_parquet, index=False)
    pd.DataFrame(manifest).to_csv(out_parquet.replace(".parquet", "_manifest.csv"), index=False)
    return base


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--biosample", required=True)            # K562 | HepG2 | ...
    ap.add_argument("--sizes", default="/data/raw/hg38.chrom.sizes")
    ap.add_argument("--raw-dir", default="/data/raw/encode")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or f"/data/features/chromatin_{a.biosample.lower()}.parquet"
    df = build_feature_store(a.biosample, a.sizes, a.raw_dir, out)
    cols = [c for c in df.columns if c not in ("chrom", "bin", "biosample")]
    print(f"feature store {out}: bins={len(df)} tracks={cols}")


if __name__ == "__main__":
    main()
