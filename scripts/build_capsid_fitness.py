"""Reproducible build (v6.11 D-WS2): train the AAV capsid-fitness model on the FLIP-AAV benchmark and report the
learned-vs-baseline result. Run on the VM (needs the FLIP-AAV splits + scikit-learn).

Download FLIP-AAV splits: https://github.com/J-SNACKKB/FLIP/raw/main/splits/aav/splits.zip -> splits/{split}.csv
(columns: sequence, target, set, validation). Built on Bryant et al. 2021 (Nat Biotechnol 10.1038/s41587-020-00793-4,
packaging fitness) / Ogden et al. 2019 (Science 10.1126/science.aaw2900). Writes models/capsid_fitness.pkl (~3 MB,
ships) + benchmarks/delivery/capsid_fitness_metrics.json (committed).

RESULT (committed): the windowed one-hot gradient-boosting model beats a mutation-burden baseline on both splits,
sampled Spearman 0.920 vs 0.522 (CI [0.387, 0.411]); mut_des (mutant->designed) 0.814 vs 0.752 (CI [0.061, 0.064]).

Usage: SPLITS=/path/to/splits OUT=/path/to/out python build_capsid_fitness.py
"""
from __future__ import annotations

import collections
import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

SPLITS = os.environ.get("SPLITS", "/deliv/splits")
OUT = os.environ.get("OUT", "/out")
W0, W1 = 555, 595 # window over the Bryant 561-588 mutagenized VP1 region (+ flanks)
WL = W1 - W0
AAS = "ACDEFGHIKLMNPQRSTVWY"
AAi = {a: i for i, a in enumerate(AAS)}


def win(s: str) -> str:
    return (s[W0:W1] + "-" * WL)[:WL]


def onehot(w: str) -> np.ndarray:
    x = np.zeros(WL * 20, dtype="float32")
    for i, a in enumerate(w):
        j = AAi.get(a)
        if j is not None:
            x[i * 20 + j] = 1.0
    return x


def spearman(a, b) -> float:
    a = pd.Series(a).rank().to_numpy()
    b = pd.Series(b).rank().to_numpy()
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def main() -> dict:
    out = {}
    for split in ["sampled", "mut_des"]:
        d = pd.read_csv(f"{SPLITS}/{split}.csv")
        d["w"] = d["sequence"].map(win)
        tr = d[d.set == "train"].reset_index(drop=True)
        te = d[d.set == "test"].reset_index(drop=True)
        arr = np.array([list(w) for w in tr["w"]])
        cons = "".join(collections.Counter(arr[:, i]).most_common(1)[0][0] for i in range(WL))
        base_te = te["w"].map(lambda w: -sum(1 for a, b in zip(w, cons) if a != b)).to_numpy()
        base_sp = spearman(base_te, te["target"].to_numpy())
        m = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.1, max_leaf_nodes=63, random_state=0)
        m.fit(np.vstack([onehot(w) for w in tr["w"]]), tr["target"].to_numpy())
        learn_te = m.predict(np.vstack([onehot(w) for w in te["w"]]))
        learn_sp = spearman(learn_te, te["target"].to_numpy())
        rng = np.random.RandomState(7)
        tt = te["target"].to_numpy()
        diffs = [spearman(learn_te[bi], tt[bi]) - spearman(base_te[bi], tt[bi])
                 for bi in (rng.randint(0, len(te), len(te)) for _ in range(300))]
        ci = [round(float(np.percentile(diffs, 2.5)), 4), round(float(np.percentile(diffs, 97.5)), 4)]
        out[split] = {"n_train": int(len(tr)), "n_test": int(len(te)), "baseline_spearman": round(base_sp, 4),
                      "learned_spearman": round(learn_sp, 4), "gap": round(learn_sp - base_sp, 4),
                      "gap_ci95": ci, "learned_beats_baseline": bool(ci[0] > 0)}
        print(split, out[split])
        if split == "mut_des":
            os.makedirs(OUT, exist_ok=True)
            pickle.dump({"model": m, "window": [W0, W1], "consensus": cons, "aas": AAS,
                         "target": "FLIP-AAV packaging fitness (Bryant 2021 / Dallago 2021)"},
                        open(f"{OUT}/capsid_fitness.pkl", "wb"))
    out["method"] = {"model": "windowed one-hot (VP1 555-595) HistGradientBoostingRegressor",
                     "baseline": "mutation burden (negative Hamming from the train-set consensus window)",
                     "benchmark": "FLIP-AAV (Dallago 2021; Bryant 2021 10.1038/s41587-020-00793-4)",
                     "metric": "Spearman on held-out test; bootstrap (300) CI on learned-minus-baseline gap"}
    json.dump(out, open(f"{OUT}/capsid_fitness_metrics.json", "w"), indent=2)
    return out


if __name__ == "__main__":
    main()
