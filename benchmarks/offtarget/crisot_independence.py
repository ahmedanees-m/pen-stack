"""CRISOT independence account at assay, guide and example level. The nuclease path wraps the published CRISOT specificity scorer, developed
by Chen et al. using CHANGE-seq and SITE-seq data. Two of the four assays in this evaluation are those
same assays, so the comparison against a homology baseline is not independent of the scorer's own
development data on those two. This script reports the overlap and recomputes the comparison on the
subsets where independence holds.

Run from the repository root.
"""
import json

import numpy as np
import pandas as pd

DEV = {"changeseq", "siteseq"}      # assays used during CRISOT development
IND = {"guideseq", "circleseq"}     # assays not used during its development


def summarise(sub, label, seed=7, reps=4000):
    gap = (sub["crisot"] - sub["homology"]).to_numpy()
    rng = np.random.default_rng(seed)
    bs = np.sort([gap[rng.integers(0, len(gap), len(gap))].mean() for _ in range(reps)])
    lo, hi = float(bs[int(0.025 * len(bs))]), float(bs[int(0.975 * len(bs))])
    print("{:<48} pairs={:<4} crisot={:.4f}  homology={:.4f}  gap={:+.4f}  "
          "CI[{:+.4f}, {:+.4f}]  excludes 0: {}".format(
              label, len(sub), sub["crisot"].mean(), sub["homology"].mean(),
              gap.mean(), lo, hi, "yes" if lo > 0 else "NO"))
    return {"label": label, "pairs": int(len(sub)),
            "mean_crisot_auprc": round(float(sub["crisot"].mean()), 4),
            "mean_homology_auprc": round(float(sub["homology"].mean()), 4),
            "mean_gap": round(float(gap.mean()), 4), "ci95": [round(lo, 4), round(hi, 4)],
            "excludes_zero": bool(lo > 0)}


def main():
    d = pd.read_csv("benchmarks/offtarget/offtarget_bench_fixture.csv")
    m = json.load(open("benchmarks/offtarget/offtarget_bench_metrics.json", encoding="utf8"))

    print("=" * 104)
    print("A. Assay-level structure and overlap with the scorer's development data")
    print("=" * 104)
    print("{:<12}{:>7}{:>8}{:>8}{:>12}   {}".format(
        "assay", "rows", "guides", "active", "prevalence", "used in CRISOT development"))
    assay_rows = {}
    for a, g in d.groupby("assay"):
        print("{:<12}{:>7}{:>8}{:>8}{:>11.3f}   {}".format(
            a, len(g), g["guide"].nunique(), int(g["active"].sum()), g["active"].mean(),
            "YES" if a in DEV else "no"))
        assay_rows[a] = {"rows": int(len(g)), "guides": int(g["guide"].nunique()),
                         "active": int(g["active"].sum()),
                         "prevalence": round(float(g["active"].mean()), 4),
                         "in_development_data": a in DEV}

    byg = d.groupby("guide")["assay"].agg(lambda s: set(s))
    dev_guides = sorted({g for g, a in byg.items() if a & DEV})
    both = sorted({g for g, a in byg.items() if (a & IND) and (a & DEV)})
    ind_only = sorted({g for g, a in byg.items() if (a & IND) and not (a & DEV)})

    print()
    print("=" * 104)
    print("B. Guide-level independence")
    print("=" * 104)
    print("guides in total                                     : {}".format(d["guide"].nunique()))
    print("guides appearing in a development assay             : {}".format(len(dev_guides)))
    print("guides appearing ONLY in an independent assay       : {}".format(len(ind_only)))
    print("  -> {}".format(", ".join(ind_only)))
    print("guides in BOTH, so not example-level independent    : {}".format(len(both)))
    print("  -> {}".format(", ".join(both) if both else "none"))

    rows = []
    for assay, ab in (m.get("assays") or {}).items():
        for g, gb in (ab.get("guides") or {}).items():
            rows.append({"assay": assay, "guide": g,
                         "n_cand": gb.get("n_candidates"), "n_active": gb.get("n_active"),
                         "crisot": gb.get("crisot_auprc"), "homology": gb.get("homology_auprc")})
    r = pd.DataFrame(rows).dropna(subset=["crisot", "homology"])

    print()
    print("=" * 104)
    print("C. The comparison, by independence stratum. Guide-level bootstrap over guide-assay pairs")
    print("=" * 104)
    out = {"assay_structure": assay_rows, "guides_development": dev_guides,
           "guides_independent_only": ind_only, "guides_in_both": both,
           "n_guide_assay_pairs": int(len(r)), "strata": {}}
    out["strata"]["all_four_assays"] = summarise(r, "all four assays, as published")
    out["strata"]["development_only"] = summarise(r[r.assay.isin(DEV)],
                                                  "CHANGE-seq and SITE-seq (development assays)")
    out["strata"]["independent_assays"] = summarise(r[r.assay.isin(IND)],
                                                    "GUIDE-seq and CIRCLE-seq (independent assays)")
    strict = r[r.assay.isin(IND) & r.guide.isin(ind_only)]
    out["strata"]["strict_independent"] = summarise(
        strict, "STRICT: independent assays, guides unseen in development")

    with open("out_crisot_independence.json", "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out_crisot_independence.json")


if __name__ == "__main__":
    main()
