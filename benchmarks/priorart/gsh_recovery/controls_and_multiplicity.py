"""Safe-harbour discrimination under the matched design, and multiplicity across the claim family.

Five analyses, in order:

  A. Reproduce the published AUROC and interval exactly, using the repository's own scorer.
  B. Report every positive tier separately with its n, which is what the 7-versus-16 question is about.
  C. Re-estimate the interval preserving the matched structure. The published bootstrap resamples
     positives and controls independently, but the controls were drawn per positive inside matched
     quantile buckets, so independent resampling discards the pairing.
  D. Control-selection sensitivity: how much the point estimate moves with the control draw.
  E. Where the eight blocklisted genotoxic loci rank after the blocklist is applied, since the
     blocklist zeroes the safety term inside an additive composite rather than excluding the locus.

Then the multiplicity correction over the pre-registered claim family.

Run from the repository root with the atlas mounted at data/out/.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SEED = 20260604
N_BOOT = 4000


def hdr(t):
    print("\n" + "=" * 94)
    print(t)
    print("=" * 94)


def main():
    from pen_stack.validate.blind_gsh_discovery import (
        _auroc_ci,
        _auroc_vec,
        _load_features,
        gsh_positives,
    )
    import yaml

    out = {}

    # ---------------------------------------------------------------- A, reproduce
    hdr("A. Reproduce the published figures with the repository's own scorer")
    df = _load_features("k562")
    cfg = yaml.safe_load(open("configs/gsh_validated_heldout.yaml", encoding="utf8"))
    positives = gsh_positives(df, cfg)
    controls = pd.read_parquet("data/gsh_matched_controls.parquet")

    # A per-row .get() against a multi-index of this size degrades to a linear scan, so the lookup is
    # built once as a plain dict keyed on (chrom, bin) and read by list comprehension.
    _keys = list(zip(df["chrom"].astype(str), df["bin"].astype(int)))
    _tables = {c: dict(zip(_keys, df[c].to_numpy(dtype=float)))
               for c in ("writability", "safety")}

    def score_rows(frame, col):
        t = _tables[col]
        idx = zip(frame["chrom"].astype(str), frame["bin"].astype(int))
        return np.array([t.get(k, np.nan) for k in idx], dtype=float)

    def block(pos_frame, label):
        # the published _tier_block restricts controls to those MATCHED to this tier's positives.
        # Using the whole control table instead changes the estimate, so the filter is reproduced here.
        ctl = controls[controls["positive"].isin(set(pos_frame["name"]))]
        pw = score_rows(pos_frame, "writability")
        cw = score_rows(ctl, "writability")
        pw, cw = pw[~np.isnan(pw)], cw[~np.isnan(cw)]
        a, ci = _auroc_ci(list(pw), list(cw))
        print(f"  {label:<34} n_pos={len(pw):<4} n_ctrl={len(cw):<5} AUROC={a:.4f}  95% CI {ci}")
        return {"label": label, "n_pos": int(len(pw)), "n_ctrl": int(len(cw)),
                "auroc": round(float(a), 4), "ci95_published_method": ci}

    tiers = sorted(set(positives["tier"]))
    print(f"  positive tiers present: {tiers}")
    curated = positives[positives["tier"] != "pellenz_candidate"]
    validated = positives[positives["tier"] == "validated"]
    out["A_curated_16"] = block(curated, "curated (validated + candidate)")
    out["A_validated_only"] = block(validated, "validated only")
    out["A_all_tiers"] = block(positives, "all tiers incl. pellenz")

    # ---------------------------------------------------------------- B, tier table
    hdr("B. Positive sets, by tier. This is the 7-versus-16 question")
    print(f"  {'tier':<22}{'n loci':>8}")
    for t in tiers:
        print(f"  {t:<22}{int((positives['tier'] == t).sum()):>8}")
    print(f"  {'curated (acceptance)':<22}{len(curated):>8}")
    print(f"  {'all tiers':<22}{len(positives):>8}")
    out["B_tier_counts"] = {t: int((positives["tier"] == t).sum()) for t in tiers}
    out["B_tier_counts"]["curated"] = int(len(curated))
    out["B_tier_counts"]["all"] = int(len(positives))

    # ---------------------------------------------------------------- C, matched bootstrap
    hdr("C. Interval preserving the matched structure")
    # each positive carries its own matched controls, keyed by the 'positive' column
    cl = controls.copy()
    cl["w"] = score_rows(cl, "writability")
    groups = {k: g["w"].dropna().to_numpy() for k, g in cl.groupby("positive")}
    cur_names = list(curated["name"])
    pos_by_name = {}
    for _, r in curated.iterrows():
        v = _tables["writability"].get((str(r["chrom"]), int(r["bin"])), np.nan)
        if not np.isnan(v):
            pos_by_name[r["name"]] = float(v)
    usable = [n for n in cur_names if n in pos_by_name and n in groups and len(groups[n])]
    print(f"  matched sets usable: {len(usable)} of {len(cur_names)} curated positives")

    def matched_auroc(names):
        ps, cs = [], []
        for n in names:
            ps.append(pos_by_name[n])
            cs.extend(groups[n].tolist())
        return _auroc_vec(np.array(ps), np.array(cs))

    point = matched_auroc(usable)
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(N_BOOT):
        draw = [usable[i] for i in rng.integers(0, len(usable), len(usable))]
        boots.append(matched_auroc(draw))
    boots = np.sort(np.array(boots))
    ci_m = [round(float(boots[int(0.025 * len(boots))]), 4),
            round(float(boots[int(0.975 * len(boots))]), 4)]
    print(f"  AUROC (matched sets)            {point:.4f}  95% CI {ci_m}   (resamples whole matched sets)")
    print("  published method, same positives: see A above (resamples positives and controls apart)")
    out["C_matched_bootstrap"] = {"auroc": round(float(point), 4), "ci95_matched": ci_m,
                                 "n_matched_sets": len(usable), "n_boot": N_BOOT}

    # ---------------------------------------------------------------- D, control sensitivity
    hdr("D. Sensitivity to the control draw")
    sizes = [1, 5, 10, 25, 50]
    rows = []
    for m in sizes:
        vals = []
        for rep in range(40):
            r2 = np.random.default_rng(SEED + rep)
            ps, cs = [], []
            for n in usable:
                ps.append(pos_by_name[n])
                g = groups[n]
                take = g if len(g) <= m else g[r2.integers(0, len(g), m)]
                cs.extend(np.atleast_1d(take).tolist())
            vals.append(_auroc_vec(np.array(ps), np.array(cs)))
        rows.append((m, float(np.mean(vals)), float(np.std(vals))))
        print(f"  controls per positive = {m:<4} mean AUROC {np.mean(vals):.4f}  sd {np.std(vals):.4f}")
    out["D_control_sensitivity"] = [{"controls_per_positive": m, "mean_auroc": round(a, 4),
                                     "sd": round(s, 4)} for m, a, s in rows]

    # ---------------------------------------------------------------- E, blocklist ranking
    hdr("E. Where the blocklisted genotoxic loci sit after the blocklist is applied")
    from pen_stack.wgenome.genotoxic_blocklist import blocklisted_bins
    bl = blocklisted_bins()
    print(f"  blocklisted bins: {len(bl)}")
    # the composite is writability = w_safety*safety + w_durability*p_durable with equal 0.5 weights,
    # and the blocklist sets safety to 0.0 and recomputes, so the post-flag score is 0.5*p_durable.
    W_SAFETY = W_DUR = 0.5
    atlas = pd.read_parquet("/phase_1/out/atlas_k562.parquet")[["chrom", "bin", "writability",
                                                                "safety", "p_durable"]]
    allw = atlas["writability"].to_numpy()
    allw_sorted = np.sort(allw)
    print(f"  genome bins scored: {len(allw):,}   median writability {np.median(allw):.4f}")
    key = pd.MultiIndex.from_arrays([atlas["chrom"].astype(str), atlas["bin"].astype(int)])
    atlas = atlas.set_index(key)
    print(f"\n  {'gene':<12}{'p_durable':>11}{'post-flag writ.':>17}{'percentile in genome':>22}")
    brows = []
    for k, info in bl.items():
        if k not in atlas.index:
            continue
        r = atlas.loc[k]
        if isinstance(r, pd.DataFrame):
            r = r.iloc[0]
        post = W_SAFETY * 0.0 + W_DUR * float(r["p_durable"])
        pct = float(np.searchsorted(allw_sorted, post) / len(allw_sorted) * 100)
        gene = (info or {}).get("gene") or "?"
        print(f"  {str(gene):<12}{float(r['p_durable']):>11.4f}{post:>17.4f}{pct:>21.1f}%")
        brows.append({"gene": gene, "bin": list(k), "p_durable": round(float(r["p_durable"]), 4),
                      "writability_after_flag": round(post, 4), "genome_percentile": round(pct, 1)})
    out["E_blocklisted_after_flag"] = brows
    out["E_genome_median_writability"] = round(float(np.median(allw)), 4)
    out["E_note"] = ("the blocklist zeroes the safety term and recomputes the additive composite, so a "
                     "flagged locus retains 0.5 x p_durable rather than being excluded from ranking")

    # ---------------------------------------------------------------- multiplicity
    hdr("Multiplicity across the pre-registered claim family (over the claim family)")
    # Only the claims that make a positive inferential finding are at risk of a false positive.
    fam = [
        {"claim": 1, "what": "human K562 head margin over learned baseline",
         "est": 0.065, "ci": [0.0257, 0.1033], "null": 0.0, "verdict": "PASS"},
        {"claim": 6, "what": "writability AUROC vs matched controls",
         "est": out["A_curated_16"]["auroc"], "ci": out["A_curated_16"]["ci95_published_method"],
         "null": 0.5, "verdict": "PASS (weak)"},
    ]
    m = 10  # the pre-registered family
    print(f"  family size m = {m} pre-registered claims; {m - len(fam)} are non-passes and carry no "
          f"false-positive risk")
    print(f"\n  {'claim':<7}{'estimate':>10}{'95% CI':>22}{'Bonferroni 99.5% CI':>26}{'survives':>10}")
    res = []
    for f in fam:
        lo, hi = f["ci"]
        se = (hi - lo) / (2 * 1.959964)
        z = 2.807034  # two-sided alpha = 0.05/10
        blo, bhi = f["est"] - z * se, f["est"] + z * se
        surv = (blo > f["null"]) if f["est"] > f["null"] else (bhi < f["null"])
        print(f"  {f['claim']:<7}{f['est']:>10.4f}{f'[{lo:.4f}, {hi:.4f}]':>22}"
              f"{f'[{blo:.4f}, {bhi:.4f}]':>26}{('yes' if surv else 'NO'):>10}")
        res.append({**f, "se_implied": round(se, 5),
                    "bonferroni_ci995": [round(blo, 4), round(bhi, 4)],
                    "survives_bonferroni": bool(surv)})
    out["multiplicity"] = {"family_size": m, "n_positive_findings": len(fam), "claims": res}

    with open("out_safe_harbour.json", "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out_safe_harbour.json")


if __name__ == "__main__":
    sys.exit(main())
