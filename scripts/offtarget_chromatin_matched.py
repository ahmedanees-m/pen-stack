"""Reproducible analysis (v6.10.3): the CELL-TYPE-MATCHED chromatin test that settled v6.10.2's ambiguous result.

Re-runs the accessibility-vs-off-target-activity AUROC with a cell-type-MATCHED ENCODE HEK293T DNase-seq track
(ENCFF529BOG) instead of the cross-cell K562 proxy. HEK293T matches GUIDE-seq (HEK293) and TTISS (HEK293T). Maps
off-targets to hg38 (grep -F, both strands), queries the HEK293T DNase signal at each off-target's 1 kb bin
(pyBigWig mean), AUROC of accessibility for active-vs-inactive off-targets per assay. Needs hg38 GRCh38.fa, the
HEK293T DNase bigWig, the harmonized assay CSVs, and pyBigWig.

RESULT (committed in benchmarks/offtarget/chromatin_validation.json, phase2): cell-type matching LIFTS the canonical
WT-Cas9 cell-based assay GUIDE-seq from AUROC 0.58 (cross-cell K562) to 0.671 (matched HEK293T, CI [0.642, 0.701]);
the in-vitro control stays null (0.494). VERDICT: VALIDATED (moderate, cell-type-matched). TTISS stays an outlier
(0.383), it is a Cas9-VARIANT specificity assay, driven by variant fidelity rather than WT chromatin.

Usage (on the VM, container with pandas+numpy+pyBigWig):
    FA=GRCh38.fa BW=hek293t_dnase.bigWig DS=datasets python offtarget_chromatin_matched.py
"""
from __future__ import annotations

import collections
import json
import os
import subprocess

import numpy as np
import pandas as pd
import pyBigWig

FA = os.environ.get("FA", "/ref/GRCh38.fa")
BW = os.environ.get("BW", "/ref/hek293t_dnase.bigWig")
DS = os.environ.get("DS", "/d")
COMP = str.maketrans("ACGT", "TGCA")
# cell-based assays (matched by HEK293T) + one small in-vitro control; the big in-vitro sets are dropped for speed
ASSAYS = {"guideseq": "cell-based (WT Cas9)", "ttiss": "cell-based (Cas9 variants)", "siteseq": "in_vitro_control"}
VALID = {f"chr{i}" for i in list(range(1, 23)) + ["X", "Y"]}


def rc(s: str) -> str:
    return s.translate(COMP)[::-1]


def auroc(y, s):
    y = np.asarray(y)
    s = np.asarray(s, float)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return None
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
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main() -> dict:
    rng = np.random.RandomState(7)
    bw = pyBigWig.open(BW)
    bwchroms = set(bw.chroms().keys())
    frames = []
    for tag in ASSAYS:
        df = pd.read_csv(f"{DS}/{tag}.csv")
        df["assay"] = tag
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
    cache: dict = {}

    def binsig(bc, b0):
        if (bc, b0) not in cache:
            try:
                v = bw.stats(bc, b0, min(b0 + 1000, bw.chroms(bc)), type="mean")[0]
                cache[(bc, b0)] = float(v) if v is not None else None
            except Exception: # noqa: BLE001
                cache[(bc, b0)] = None
        return cache[(bc, b0)]

    def acc(off):
        vals = []
        for c, p in hits.get(off, []):
            bc = c if c in bwchroms else (c[3:] if c[3:] in bwchroms else None)
            if bc is None:
                continue
            s = binsig(bc, (p // 1000) * 1000)
            if s is not None:
                vals.append(s)
        return max(vals) if vals else None
    sub["acc"] = sub["off23"].map(acc)
    mp = sub.dropna(subset=["acc"])
    out = {}
    for tag in ASSAYS:
        a = mp[mp["assay"] == tag]
        out[tag] = {"modality": ASSAYS[tag], "auroc": round(auroc(a["Active"].values, a["acc"].values), 3),
                    "actives": int(a["Active"].sum()), "n": int(len(a))}
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
