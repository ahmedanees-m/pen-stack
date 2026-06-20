"""Chromatin feature store (Phase 1, Step 1.1).

Resolves the ENCODE bigWig panel for a cell type, downloads tracks IN PARALLEL, bins each to the
canonical 1 kb grid (mean signal per bin) IN PARALLEL across cores, merges into one feature-store
parquet, and deletes the raw bigWigs (500 GB discipline). Run in Docker on the VM.
"""
from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyBigWig
import requests

from pen_stack.data.encode import resolve_panel
from pen_stack.data.genome import MAIN_CHROMS, load_chrom_sizes

BIN_BP = 1000


def download(href: str, dest: str) -> str:
    dest = str(dest)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    with requests.get(href, stream=True, timeout=900) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    return dest


def bin_one(args) -> tuple[str, pd.DataFrame]:
    """Bin one bigWig to 1 kb mean per bin (module-level for ProcessPool picklability)."""
    name, path, sizes = args
    bw = pyBigWig.open(path)
    bw_chroms = set(bw.chroms().keys())
    frames = []
    for c in MAIN_CHROMS:
        if c not in sizes:
            continue
        n = sizes[c] // BIN_BP
        key = c if c in bw_chroms else c.replace("chr", "")
        if key not in bw_chroms:
            frames.append(pd.DataFrame({"chrom": c, "bin": range(n), name: np.zeros(n, "float32")}))
            continue
        vals = bw.stats(key, 0, n * BIN_BP, nBins=n, type="mean")
        v = np.array([0.0 if x is None else float(x) for x in vals], dtype="float32")
        frames.append(pd.DataFrame({"chrom": c, "bin": range(n), name: v}))
    bw.close()
    return name, pd.concat(frames, ignore_index=True)


def build_feature_store(biosample: str, chrom_sizes_tsv: str, raw_dir: str, out_parquet: str,
                        max_dl: int = 7, max_bin: int = 7) -> pd.DataFrame:
    sizes = load_chrom_sizes(chrom_sizes_tsv)
    panel = resolve_panel(biosample)
    print(f"[{biosample}] resolved tracks: {list(panel.keys())}", flush=True)
    if not panel:
        raise SystemExit(f"no ENCODE bigWig tracks resolved for {biosample}")

    # 1) parallel download
    paths = {}
    with ThreadPoolExecutor(max_workers=max_dl) as ex:
        futs = {ex.submit(download, rec["href"],
                          os.path.join(raw_dir, f"{biosample}_{name}_{rec['accession']}.bigWig")): name
                for name, rec in panel.items()}
        for fut in futs:
            name = futs[fut]
            paths[name] = fut.result()
            print(f" downloaded {name}", flush=True)

    # 2) parallel bin
    binned = {}
    with ProcessPoolExecutor(max_workers=max_bin) as ex:
        for name, df in ex.map(bin_one, [(n, paths[n], sizes) for n in panel]):
            binned[name] = df
            print(f" binned {name}", flush=True)

    base = None
    for name in panel:
        base = binned[name] if base is None else base.merge(binned[name], on=["chrom", "bin"])
    base["biosample"] = biosample

    # 3) clean raws
    for p in paths.values():
        try:
            os.remove(p)
        except OSError:
            pass

    Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
    base.to_parquet(out_parquet, index=False)
    pd.DataFrame([{"track": n, "accession": panel[n]["accession"],
                   "output_type": panel[n]["output_type"]} for n in panel]
                 ).to_csv(out_parquet.replace(".parquet", "_manifest.csv"), index=False)
    return base


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--biosample", required=True)
    ap.add_argument("--sizes", default="/data/raw/hg38.chrom.sizes")
    ap.add_argument("--raw-dir", default="/data/raw/encode")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or f"/data/features/chromatin_{a.biosample.lower()}.parquet"
    df = build_feature_store(a.biosample, a.sizes, a.raw_dir, out)
    cols = [c for c in df.columns if c not in ("chrom", "bin", "biosample")]
    print(f"feature store {out}: bins={len(df)} tracks={cols}", flush=True)


if __name__ == "__main__":
    main()
