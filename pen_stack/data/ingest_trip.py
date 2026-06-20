"""TRIP durability supervision (Phase 1, Step 1.3).

Ingests the Akhtar et al. 2013 TRIP data (GEO GSE49806 tet-O + GSE49807 mPGK; mouse mESC): each row is
one integrated reporter at a genomic position with expression. Produces (position, expression level,
silenced/expressed label) - the supervision for the conditional chromatin-context durability model.

The model learns `local chromatin features -> expression`; it never sees the coordinate. So TRIP being
mouse is fine: attach mouse (mES) chromatin features at these positions, train the function, then apply
it to a human epigenome (the headline function-transfer test).
"""
from __future__ import annotations

import argparse
import gzip
from pathlib import Path

import numpy as np
import pandas as pd


def load_trip(txt_gz: str, promoter: str) -> pd.DataFrame:
    """Robust to both TRIP schemas: GSE49807 (plain) and GSE49806 (leading '#' comment + multi-Dox
    columns; we use the 100 ng full-induction normalization/expression pair)."""
    with gzip.open(txt_gz, "rt") as fh:
        raw = pd.read_csv(fh, sep="\t", comment="#", dtype=str)
    cols = {c.lower().strip(): c for c in raw.columns}
    chrom_c = cols.get("chromosome")
    pos_c = cols.get("position")
    norm_c = cols.get("normalization_counts_100ng_1") or cols.get("normalization_counts")
    expr_c = cols.get("expression_counts_100ng_1") or cols.get("expression_counts")
    if not all([chrom_c, pos_c, norm_c, expr_c]):
        raise ValueError(f"{txt_gz}: missing expected columns; have {list(raw.columns)[:8]}")
    df = pd.DataFrame({
        "chrom": raw[chrom_c].astype(str),
        "pos": pd.to_numeric(raw[pos_c], errors="coerce"),
        "norm_counts": pd.to_numeric(raw[norm_c], errors="coerce"),
        "expr_counts": pd.to_numeric(raw[expr_c], errors="coerce"),
    }).dropna()
    df["pos"] = df["pos"].astype(int)
    df["promoter"] = promoter
    return df


def assemble(files: dict[str, str], out_parquet: str, silenced_quantile: float = 0.25) -> pd.DataFrame:
    parts = [load_trip(path, prom) for prom, path in files.items()]
    df = pd.concat(parts, ignore_index=True)
    # normalized expression (expression per normalization read), log scale
    df["expression"] = np.log2((df["expr_counts"] + 1) / (df["norm_counts"] + 1))
    # silenced/expressed: low tail of expression flagged silenced (per promoter, to control for promoter strength)
    df["silenced"] = False
    for prom, g in df.groupby("promoter"):
        thr = g["expression"].quantile(silenced_quantile)
        df.loc[g.index, "silenced"] = g["expression"] <= thr
    df["stable"] = ~df["silenced"]
    Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_parquet, index=False)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teto", default="/data/external/trip/GSE49806_S2.txt.gz")
    ap.add_argument("--mpgk", default="/data/external/trip/GSE49807_S3.txt.gz")
    ap.add_argument("--out", default="/data/features/trip_mesc.parquet")
    a = ap.parse_args()
    files = {k: v for k, v in {"tetO": a.teto, "mPGK": a.mpgk}.items() if Path(v).exists()}
    df = assemble(files, a.out)
    print(f"TRIP integrations: {len(df)} promoters={df['promoter'].value_counts().to_dict()}")
    print(f"expression range (log2): [{df['expression'].min():.2f}, {df['expression'].max():.2f}] "
          f"~{2**(df['expression'].max()-df['expression'].min()):.0f}-fold")
    print(f"silenced={int(df['silenced'].sum())} stable={int(df['stable'].sum())}")
    print(f"chroms: {sorted(df['chrom'].unique())[:6]}... (mouse build)")


if __name__ == "__main__":
    main()
