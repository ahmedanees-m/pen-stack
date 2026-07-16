"""Reproducible analysis (v6.10.4): does chromatin accessibility add INCREMENTAL value over the CRISOT sequence
score for nominating off-targets? On GUIDE-seq (cell-based) with cell-type-matched HEK293T DNase accessibility:

  (A) conditional logistic regression active ~ z(CRISOT) + z(accessibility) -> bootstrap-over-guides 95% CI on
      the accessibility coefficient (does accessibility carry signal CONDITIONAL on CRISOT?).
  (B) leave-one-guide-out held-out AUPRC of CRISOT-only vs a CRISOT+accessibility logistic combiner, bootstrap
      95% CI on the per-guide gap (does the combiner IMPROVE held-out nomination ranking?).

RESULT (committed in benchmarks/offtarget/chromatin_incremental.json): accessibility carries a SMALL, REAL
conditional signal (coef ~0.35, CI excludes 0 at both 1:16 and 1:123 imbalance) but adds NO held-out ranking
improvement over CRISOT (AUPRC gap CI includes 0 at both). DECISION: chromatin is a validated ANNOTATION, NOT a
re-ranker, the CRISOT sequence score already captures the practically-relevant ranking signal.

Needs: the CRISOT repo (CRISOT-Score), hg38 GRCh38.fa, the HEK293T DNase bigWig, the GUIDE-seq CSV, plus
xgboost / pyBigWig / scikit-learn. Run on the VM. (Inactive cap controls the candidate imbalance.)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pyBigWig
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

sys.path.insert(0, os.environ.get("CRISOT", "/crisot"))
from crisot_modules import CRISOT # noqa: E402
from utils import load_pkl # noqa: E402

FA = os.environ.get("FA", "/ref/GRCh38.fa")
BW = os.environ.get("BW", "/ref/hek293t_dnase.bigWig")
DS = os.environ.get("DS", "/d")
INACT_CAP = int(os.environ.get("INACT_CAP", "4000")) # 4000/guide ~ realistic imbalance
COMP = str.maketrans("ACGT", "TGCA")
VALID = {f"chr{i}" for i in list(range(1, 23)) + ["X", "Y"]}


def rc(s: str) -> str:
    return s.translate(COMP)[::-1]


def main() -> dict:
    rng = np.random.RandomState(7)
    pr, _ab, _bins, _w = load_pkl(os.environ.get("CRISOT", "/crisot") + "/models/crisot_score_param.pkl")
    model = CRISOT(param=pr, ref_genome=os.environ.get("CRISOT", "/crisot") + "/script/hg38.na")
    df = pd.read_csv(f"{DS}/guideseq.csv")
    df["On20"] = df["On"].str[:20]
    g = df.groupby("On20")["Active"].sum()
    df = df[df["On20"].isin(list(g[g >= 5].index))].copy()
    parts = []
    for _gd, sub in df.groupby("On20"):
        inact = sub[sub.Active == 0]
        parts.append(pd.concat([sub[sub.Active == 1], inact.sample(n=min(INACT_CAP, len(inact)), random_state=rng)]))
    d = pd.concat(parts).reset_index(drop=True)
    d["crisot"] = model.score(data_df=d, On="On", Off="Off")
    d["off23"] = d["Off"].str[:23]
    pat = {}
    for off in d["off23"].unique():
        if len(off) == 23 and set(off) <= set("ACGT"):
            pat[off] = off
            pat[rc(off)] = off
    open("/tmp/pats.txt", "w").write("\n".join(pat) + "\n")
    hits: dict = {}
    cur, buf = None, []

    def flush(chrom, seq):
        c = chrom if chrom and chrom.startswith("chr") else f"chr{chrom}"
        if not seq or c not in VALID:
            return
        open("/tmp/chr.txt", "w").write(seq)
        p = subprocess.run(["grep", "-boFf", "/tmp/pats.txt", "/tmp/chr.txt"], capture_output=True, text=True)
        for ln in p.stdout.splitlines():
            ob, _, m = ln.partition(":")
            if pat.get(m):
                hits.setdefault(pat[m], []).append((c, int(ob)))
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
    bw = pyBigWig.open(BW)
    bwc = set(bw.chroms().keys())
    cache: dict = {}

    def acc(off):
        vals = []
        for c, p in hits.get(off, []):
            bc = c if c in bwc else (c[3:] if c[3:] in bwc else None)
            if bc is None:
                continue
            b0 = (p // 1000) * 1000
            if (bc, b0) not in cache:
                try:
                    v = bw.stats(bc, b0, min(b0 + 1000, bw.chroms(bc)), type="mean")[0]
                    cache[(bc, b0)] = float(v) if v is not None else None
                except Exception: # noqa: BLE001
                    cache[(bc, b0)] = None
            if cache[(bc, b0)] is not None:
                vals.append(cache[(bc, b0)])
        return max(vals) if vals else None
    d["acc"] = d["off23"].map(acc)
    d = d.dropna(subset=["acc"]).reset_index(drop=True)
    d["zc"] = (d.crisot - d.crisot.mean()) / d.crisot.std()
    d["za"] = (d.acc - d.acc.mean()) / d.acc.std()
    guides = sorted(d.On20.unique())

    def fit(dd):
        lr = LogisticRegression(max_iter=2000, class_weight="balanced").fit(dd[["zc", "za"]], dd.Active)
        return lr.coef_[0], lr.intercept_[0]
    (cc, ca), _b = fit(d)
    accb = []
    for _ in range(1000):
        gs = rng.choice(guides, len(guides), replace=True)
        try:
            accb.append(fit(pd.concat([d[d.On20 == x] for x in gs]))[0][1])
        except Exception: # noqa: BLE001
            pass
    acc_ci = [round(float(np.percentile(accb, 2.5)), 4), round(float(np.percentile(accb, 97.5)), 4)]
    cris_ap, comb_ap = [], []
    for held in guides:
        tr, te = d[d.On20 != held], d[d.On20 == held]
        if te.Active.sum() == 0 or len(te) < 5:
            continue
        lr = LogisticRegression(max_iter=2000, class_weight="balanced").fit(tr[["zc", "za"]], tr.Active)
        comb_ap.append(average_precision_score(te.Active, lr.predict_proba(te[["zc", "za"]])[:, 1]))
        cris_ap.append(average_precision_score(te.Active, te.zc.values))
    gap = np.array(comb_ap) - np.array(cris_ap)
    gb = [float(np.mean(gap[rng.randint(0, len(gap), len(gap))])) for _ in range(1000)]
    out = {"n_offtargets": int(len(d)), "n_actives": int(d.Active.sum()), "n_guides": len(guides),
           "conditional_acc_coef": round(float(ca), 4), "acc_coef_ci95": acc_ci,
           "mean_crisot_only_auprc": round(float(np.mean(cris_ap)), 4),
           "mean_crisot_plus_acc_auprc": round(float(np.mean(comb_ap)), 4),
           "auprc_gap_ci95": [round(float(np.percentile(gb, 2.5)), 4), round(float(np.percentile(gb, 97.5)), 4)]}
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
