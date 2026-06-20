"""Safety concordance evaluation (Phase 1, Step 1.10 - the CORRECT safety validation).

AUROC on the `genotoxic_cis` label is circular (the label = proximity to 5 oncogenes = the distance
baseline's own definition). The scientifically meaningful test is CONCORDANCE: does the learned risk
score rank validated genotoxic CIS (LMO2/MECOM/CCND2/PRDM16/HMGA2) ABOVE validated safe harbours
(AAVS1/PPP1R12C, CCR5, CLYBL), and does it separate them better than the naive distance baseline?
"""
import argparse
import gzip

import pandas as pd

from pen_stack.wgenome.features import assemble_matrix
from pen_stack.wgenome.safety import train_safety

GTOX = ["LMO2", "MECOM", "CCND2", "PRDM16", "HMGA2"]
SAFE = ["PPP1R12C", "CCR5", "CLYBL"] # AAVS1 = PPP1R12C intron


def gene_coords(gtf_gz):
    g = {}
    with gzip.open(gtf_gz, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.split("\t")
            if f[2] != "gene":
                continue
            nm = [x for x in f[8].split(";") if "gene_name" in x]
            if nm:
                g[nm[0].split('"')[1]] = (f[0], int(f[3]), int(f[4]))
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ct", default="k562")
    ap.add_argument("--feat-dir", default="/data/features")
    ap.add_argument("--gtf", default="/data/raw/gencode.v46.basic.gtf.gz")
    a = ap.parse_args()

    m = assemble_matrix(f"{a.feat_dir}/chromatin_{a.ct}.parquet",
                        f"{a.feat_dir}/safety_annot.parquet",
                        f"{a.feat_dir}/integration_{a.ct}.parquet")
    res = train_safety(m, label="genotoxic_cis")
    m = m.copy()
    m["risk"] = res["oof"]
    m["base"] = -m["dist_oncogene"].fillna(m["dist_oncogene"].max())
    genes = gene_coords(a.gtf)

    def pct(col, val):
        return float((m[col] < val).mean())

    def locus(g):
        if g not in genes:
            return None
        c, s, e = genes[g]
        sub = m[(m.chrom == c) & (m.bin >= s // 1000) & (m.bin <= e // 1000)]
        if not len(sub):
            return None
        return pct("risk", sub.risk.max()), pct("base", sub.base.max())

    rows = []
    print(f"{'LOCUS':14s} {'class':5s} {'model_pct':>9s} {'base_pct':>9s}")
    for g in GTOX + SAFE:
        r = locus(g)
        if r:
            cls = "GTOX" if g in GTOX else "SAFE"
            rows.append((g, cls, r[0], r[1]))
            print(f"{g:14s} {cls:5s} {r[0]:9.3f} {r[1]:9.3f}")

    df = pd.DataFrame(rows, columns=["locus", "cls", "model", "base"])
    gt, sf = df[df.cls == "GTOX"], df[df.cls == "SAFE"]
    # separation = mean(genotoxic percentile) - mean(safe-harbour percentile); higher = better
    sep_model = gt.model.mean() - sf.model.mean()
    sep_base = gt.base.mean() - sf.base.mean()
    print(f"\nseparation (GTOX - SAFE, higher=better): model={sep_model:+.3f} baseline={sep_base:+.3f}")
    print(f"model separates genotoxic from safe-harbour better than baseline: {sep_model > sep_base}")


if __name__ == "__main__":
    main()
