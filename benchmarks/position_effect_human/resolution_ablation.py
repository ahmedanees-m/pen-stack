"""Resolution ablation with everything except spatial aggregation held constant. The published comparison sets an exact-site correlation of 0.5711 against a
coarse-resolution 0.1595 and attributes the fall to resolution. Those two figures do not come from a
controlled contrast: they use different feature sets, different source tracks and different
normalisation. In particular the coarse analysis carries H3K4me3 and omits H3K36me3, which is the
top-weighted feature of the shipped head, so the comparison changes the model's most important input
at the same time as it changes resolution.

This script varies spatial aggregation and nothing else. Same loci, same five mark definitions, same
committed source columns, same normalisation, same training procedure, same sealed chromosome split.
For a bin width w, every integration falling in the same w-wide bin receives the mean feature vector
of that bin, which is what a server returning one value per bin would supply for all of them.
Aggregation is applied to train and test alike, as a coarse server would.

Run from the repository root.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

BENCH = "benchmarks/position_effect_human"
MARKS = {"H3K27ac_mean": "H3K27ac", "H3K4me1_mean": "H3K4me1", "H3K9me3_mean": "H3K9me3",
         "H3K27me3_mean": "H3K27me3", "H3K36me3_mean": "H3K36me3"}
FULL = ["H3K27ac", "H3K4me1", "H3K9me3", "H3K27me3", "H3K36me3"]
INDEPENDENT = ["H3K27ac", "H3K4me1", "H3K36me3"]
WIDTHS = [0, 1_000, 5_000, 10_000, 50_000, 200_000, 1_000_000, 10_000_000]


def label(w):
    if w == 0:
        return "exact site"
    if w < 1_000_000:
        return f"{w // 1000} kb"
    return f"{w // 1_000_000} Mb"


def main():
    from pen_stack.twin.position_effect import PositionEffectModel

    split = json.loads(open(f"{BENCH}/split.json", encoding="utf8").read())
    held = set(split["chrom_holdout"]["test_chroms"])
    df = pd.read_parquet(f"{BENCH}/leemans_scored_input.parquet")
    df["expr_y"] = df["expr_y"].astype(float)
    print(f"integrations {len(df)}   held-out chromosomes {sorted(held)}")

    def frame(aggregated):
        tw = pd.DataFrame({"dataset": "Leemans2019", "organism": "human", "cell_type": "K562",
                           "chrom": aggregated["chrom"].astype(str),
                           "cassette": aggregated["prom_name"].astype(str),
                           "expression_raw": aggregated["expr_y"],
                           "silenced": aggregated["class"].astype(str).str.lower().eq("repressed")})
        for src, dst in MARKS.items():
            tw[dst] = aggregated[src].astype(float)
        return tw

    def rho(tw, marks):
        drop = [c for c in MARKS.values() if c not in marks]
        te = tw["chrom"].isin(held).to_numpy()
        tr, ten = tw[~te].copy(), tw[te].copy()
        m = PositionEffectModel().fit(tr.drop(columns=drop))
        pred = m.predict_expression(ten.drop(columns=drop))
        return float(spearmanr(pred, ten["expression_raw"].to_numpy()).statistic), int(len(ten))

    print("\n" + "=" * 96)
    print("Spatial aggregation swept, everything else held constant")
    print("=" * 96)
    print(f"{'bin width':<13}{'bins':>8}{'shared bins':>13}{'max per bin':>13}"
          f"{'rho FULL':>11}{'rho INDEP':>11}{'n test':>9}")
    rows = []
    for w in WIDTHS:
        if w == 0:
            agg = df.copy()
            nb, shared, mx = len(df), 0, 1
        else:
            d = df.copy()
            d["_bin"] = (d["pos"] // w).astype("int64")
            grp = d.groupby(["chrom", "_bin"])
            occ = grp.size()
            nb, shared, mx = int(len(occ)), int((occ > 1).sum()), int(occ.max())
            means = grp[list(MARKS)].transform("mean")
            agg = d.copy()
            for c in MARKS:
                agg[c] = means[c]
        tw = frame(agg)
        r_full, n_te = rho(tw, FULL)
        r_ind, _ = rho(tw, INDEPENDENT)
        print(f"{label(w):<13}{nb:>8}{shared:>13}{mx:>13}{r_full:>11.4f}{r_ind:>11.4f}{n_te:>9}")
        rows.append({"bin_width_bp": w, "label": label(w), "n_bins": nb,
                     "bins_with_more_than_one_integration": shared, "max_integrations_per_bin": mx,
                     "rho_full": round(r_full, 4), "rho_independent": round(r_ind, 4),
                     "n_test": n_te})

    out = {
        "note": ("spatial aggregation is the only variable; loci, mark definitions, source columns, "
                 "normalisation, training procedure and the sealed chromosome split are identical "
                 "across rows"),
        "feature_set_used": FULL,
        "independent_variant": INDEPENDENT,
        "held_out_chromosomes": sorted(held),
        "rows": rows,
        "published_contrast": {
            "exact_site_rho": 0.5711,
            "coarse_atlas_rho": 0.1595,
            "why_not_controlled": ("the coarse figure comes from the atlas pipeline with ENCODE "
                                   "fold-change tracks, five marks including H3K4me3 and excluding "
                                   "H3K36me3, and within-dataset z-scoring; the exact-site figure "
                                   "uses the committed Leemans columns with H3K36me3, which is the "
                                   "top-weighted feature of the shipped head. Feature set, source "
                                   "tracks and normalisation all differ alongside resolution"),
        },
    }
    with open("out_resolution_ablation.json", "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out_resolution_ablation.json")


if __name__ == "__main__":
    sys.exit(main())
