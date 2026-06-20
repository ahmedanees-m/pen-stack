"""Build the Writable Genome atlas for a cell type (Phase 1, Step 1.9 + 1.11).

Loads the cell-type feature matrix, applies the safety + (mouse-trained) durability models, integrates
into the decomposable writability profile, writes the atlas parquet, and runs a safe-harbour sanity
check (validated safe harbours should be highly writable; genotoxic CIS should not).

    python scripts/p1_build_atlas.py --ct k562
"""
import argparse
import gzip
import json
from pathlib import Path


from pen_stack.wgenome.features import assemble_matrix, resolve_integration
from pen_stack.wgenome.writability import build_writability, load_pickle

SAFE_GENES = {"PPP1R12C": "AAVS1", "CCR5": "CCR5", "CLYBL": "CLYBL"}
GTOX_GENES = {"LMO2": "LMO2", "MECOM": "MECOM", "CCND2": "CCND2"}


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
    ap.add_argument("--out-dir", default="/data/out")
    ap.add_argument("--gtf", default="/data/raw/gencode.v46.basic.gtf.gz")
    a = ap.parse_args()

    m = assemble_matrix(f"{a.feat_dir}/chromatin_{a.ct}.parquet",
                        f"{a.feat_dir}/safety_annot.parquet",
                        resolve_integration(a.feat_dir, a.ct))
    safety = load_pickle(f"{a.out_dir}/safety_{a.ct}.pkl")
    dur = load_pickle(f"{a.out_dir}/durability.pkl")

    atlas = build_writability(m, safety, dur, out_parquet=f"{a.out_dir}/atlas_{a.ct}.parquet")
    print(f"[atlas {a.ct}] bins={len(atlas)} "
          f"writability mean={atlas.writability.mean():.3f} "
          f"safety mean={atlas.safety.mean():.3f} p_durable mean={atlas.p_durable.mean():.3f}")

    # safe-harbour sanity: writability percentile of safe harbours vs genotoxic CIS
    genes = gene_coords(a.gtf)
    am = atlas.copy()

    def wr_pct(g):
        if g not in genes:
            return None
        c, s, e = genes[g]
        sub = am[(am.chrom == c) & (am.bin >= s // 1000) & (am.bin <= e // 1000)]
        if not len(sub):
            return None
        v = sub.writability.mean()
        return float((am.writability < v).mean())

    print("\n locus writability percentile (higher = more writable):")
    rows = {}
    for g, name in {**SAFE_GENES, **GTOX_GENES}.items():
        p = wr_pct(g)
        if p is not None:
            cls = "SAFE" if g in SAFE_GENES else "GTOX"
            rows[name] = (cls, p)
            print(f" {name:8s} {cls} {p:.3f}")
    safe_mean = sum(v for c, v in rows.values() if c == "SAFE") / max(1, sum(c == "SAFE" for c, v in rows.values()))
    gtox_mean = sum(v for c, v in rows.values() if c == "GTOX") / max(1, sum(c == "GTOX" for c, v in rows.values()))
    print(f"\n mean writability percentile: safe-harbours={safe_mean:.3f} genotoxic-CIS={gtox_mean:.3f}")
    print(f" safe harbours more writable than genotoxic CIS: {safe_mean > gtox_mean}")
    Path(f"{a.out_dir}/atlas_{a.ct}_sanity.json").write_text(
        json.dumps({"safe_mean": safe_mean, "gtox_mean": gtox_mean, "loci": rows}, indent=2))


if __name__ == "__main__":
    main()
