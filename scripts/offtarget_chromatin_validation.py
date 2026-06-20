"""Reproducible analysis (v6.10.2): does chromatin accessibility predict off-target activity? (Lazzarotto 2020).

Run on the VM (needs hg38 GRCh38.fa, the Stage B chromatin_{ct}.parquet, and the harmonized assay CSVs). Maps each
off-target protospacer to hg38 coordinates by exact match on both strands (grep -F, one genome pass), intersects with
the Stage B K562 ATAC/DNase accessibility at 1 kb bins, and computes the AUROC of accessibility for active-vs-inactive
off-targets PER ASSAY. Cell-based assays (GUIDE-seq, TTISS) are the test; in-vitro assays (CHANGE/CIRCLE/SITE-seq) are
the NEGATIVE control (cell-free -> no chromatin -> accessibility should not discriminate). Writes the result JSON.

RESULT (committed in benchmarks/offtarget/chromatin_validation.json): WEAK / INCONSISTENT, the in-vitro controls are
~0.5 (method sound), GUIDE-seq is a textbook modest positive (0.58) but TTISS reverses (0.346); the cross-cell-type
K562 accessibility proxy is the likely cause. Chromatin is therefore a documented annotation, NOT a validated axis.

Usage (on the VM, inside a container with pandas+numpy):
    FA=.../GRCh38.fa CHROM=.../chromatin_k562.parquet DS=.../datasets python offtarget_chromatin_validation.py
"""
from __future__ import annotations

import collections
import json
import os
import subprocess

import numpy as np
import pandas as pd

FA = os.environ.get("FA", "/data/genomes/GRCh38.fa")
CHROM = os.environ.get("CHROM", "/data/chromatin_k562.parquet")
DS = os.environ.get("DS", "/data/datasets")
COMP = str.maketrans("ACGT", "TGCA")
ASSAYS = {"guideseq": "cell-based", "ttiss": "cell-based", "changeseq": "in_vitro_control",
          "circleseq_all": "in_vitro_control", "siteseq": "in_vitro_control"}
VALID = {f"chr{i}" for i in list(range(1, 23)) + ["X", "Y"]}


def rc(s: str) -> str:
    return s.translate(COMP)[::-1]


def auroc(y, s):
    y = np.asarray(y)
    s = np.asarray(s, float)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return None, n1, n0
    order = np.argsort(s)
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    d = collections.defaultdict(list)
    for i, v in enumerate(s):
        d[v].append(i)
    for _v, idxs in d.items():
        rr = np.mean([ranks[i] for i in idxs])
        for i in idxs:
            ranks[i] = rr
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)), n1, n0


def main() -> dict:
    rng = np.random.RandomState(7)
    frames = []
    for tag in ASSAYS:
        df = pd.read_csv(f"{DS}/{tag}.csv")
        df["assay"] = tag.replace("_all", "")
        inact = df[df["Active"] == 0]
        frames.append(pd.concat([df[df["Active"] == 1], inact.sample(n=min(1500, len(inact)), random_state=rng)]))
    sub = pd.concat(frames).reset_index(drop=True)
    sub["off23"] = sub["Off"].str[:23]
    pat_map = {}
    for off in sub["off23"].unique():
        if len(off) == 23 and set(off) <= set("ACGT"):
            pat_map[off] = off
            pat_map[rc(off)] = off
    open("/tmp/pats.txt", "w").write("\n".join(pat_map) + "\n")
    hits: dict = {}
    cur, buf = None, []

    def flush(chrom, seq):
        c = chrom if chrom and chrom.startswith("chr") else f"chr{chrom}"
        if not seq or c not in VALID:
            return
        open("/tmp/chr.txt", "w").write(seq)
        p = subprocess.run(["grep", "-boFf", "/tmp/pats.txt", "/tmp/chr.txt"], capture_output=True, text=True)
        for ln in p.stdout.splitlines():
            off_b, _, matched = ln.partition(":")
            fwd = pat_map.get(matched)
            if fwd:
                hits.setdefault(fwd, []).append((c, int(off_b)))
    with open(FA) as fh:
        for line in fh:
            if line.startswith(">"):
                if cur:
                    flush(cur, "".join(buf))
                cur, buf = line[1:].split()[0], []
            else:
                buf.append(line.strip().upper())
        if cur:
            flush(cur, "".join(buf))
    cdf = pd.read_parquet(CHROM)
    cdf["acc"] = cdf[["atac", "dnase"]].max(axis=1)
    acc_idx = {(c, int(b)): float(a) for c, b, a in zip(cdf["chrom"], cdf["bin"], cdf["acc"])}
    sub["acc"] = sub["off23"].map(lambda o: max(
        [acc_idx.get((c, p // 1000)) for c, p in hits.get(o, []) if acc_idx.get((c, p // 1000)) is not None] or [np.nan]))
    mp = sub.dropna(subset=["acc"])
    out = {}
    for tag in {t.replace("_all", "") for t in ASSAYS}:
        a = mp[mp["assay"] == tag]
        au, n1, n0 = auroc(a["Active"].values, a["acc"].values)
        out[tag] = {"modality": ASSAYS.get(tag, ASSAYS.get(tag + "_all")), "auroc": au if au is None else round(au, 3),
                    "actives": n1, "inactives": n0}
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
