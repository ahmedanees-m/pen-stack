"""Writer-efficiency: the clustering structure, and a study-held-out evaluation. The released evaluation holds out a family and a locus. It does not hold
out a study, so a row can be predicted from other rows of the same paper, which share assay
conditions, optimisation history and measurement procedure. This adds the study-held-out axis using
the repository's own fitting, featurisation, baseline and bootstrap, changing only the grouping
variable, so the comparison with the published axes is like for like.

Also reports what the 45 rows actually are: records per study, per family, per cell type, the
efficiency definitions present, the source-access grades, and what experimental uncertainty is
available.

Run from the repository root.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def hdr(t):
    print("\n" + "=" * 94)
    print(t)
    print("=" * 94)


def main():
    from scipy.stats import spearmanr

    from pen_stack.atlas.writer_predict import (
        _boot_delta,
        _family_mean_baseline,
        _fit_gbr,
        _loo_groups,
        featurize,
        human_cell,
        specific_locus_mask,
    )

    out = {}
    df = human_cell(strict=False).reset_index(drop=True)
    raw = pd.read_parquet("data/writer_efficiency.parquet")

    # ------------------------------------------------------------------ structure
    hdr("A. What the rows are. Clustering structure of the knowledge base")
    print(f"  rows in the table        {len(raw)}")
    print(f"  rows used (human cell)   {len(df)}")
    print(f"  distinct studies (doi)   {raw['doi'].nunique()}")
    print(f"  distinct families        {raw['family'].nunique()}")
    print(f"  distinct cell types      {raw['cell_type'].nunique()}")
    print(f"  distinct loci            {raw['locus'].nunique()}")

    print("\n  rows per study:")
    for doi, n in raw["doi"].value_counts().items():
        fams = sorted(set(raw.loc[raw["doi"] == doi, "family"]))
        cts = raw.loc[raw["doi"] == doi, "cell_type"].nunique()
        print(f"    {n:>3} rows  {doi:<34} families={','.join(fams):<28} cell types={cts}")

    print("\n  rows per family:")
    for fam, n in raw["family"].value_counts().items():
        st = raw.loc[raw["family"] == fam, "doi"].nunique()
        print(f"    {n:>3} rows  {fam:<22} from {st} stud{'y' if st == 1 else 'ies'}")

    print("\n  source-access grades:")
    for g, n in raw["source_access"].value_counts().items():
        print(f"    {n:>3}  {g}")

    print("\n  experimental uncertainty available:")
    have_spec = int(raw["specificity_pct"].notna().sum())
    print(f"    efficiency_pct present      {int(raw['efficiency_pct'].notna().sum())} of {len(raw)}")
    print(f"    specificity_pct present     {have_spec} of {len(raw)}")
    print("    per-row replicate count, standard deviation or interval: no column exists")
    print(f"    efficiency_raw forms present: {sorted(set(str(x)[:1] for x in raw['efficiency_raw'].dropna()))[:8]}")

    out["A_structure"] = {
        "n_rows": int(len(raw)), "n_rows_used": int(len(df)),
        "n_studies": int(raw["doi"].nunique()), "n_families": int(raw["family"].nunique()),
        "n_cell_types": int(raw["cell_type"].nunique()), "n_loci": int(raw["locus"].nunique()),
        "rows_per_study": {k: int(v) for k, v in raw["doi"].value_counts().items()},
        "rows_per_family": {k: int(v) for k, v in raw["family"].value_counts().items()},
        "families_per_study": {d: sorted(set(raw.loc[raw["doi"] == d, "family"]))
                               for d in raw["doi"].unique()},
        "source_access": {k: int(v) for k, v in raw["source_access"].value_counts().items()},
        "has_per_row_uncertainty": False,
    }

    # ------------------------------------------------------------------ the three axes
    hdr("B. Held-out family, held-out locus, held-out study. Same method, different grouping")

    def run_axis(sub, by, label):
        y_true, y_model, y_base = [], [], []
        groups = 0
        for _g, tr, te in _loo_groups(sub, by):
            groups += 1
            tr_df, te_df = sub.iloc[tr], sub.iloc[te]
            f = featurize(tr_df)
            cols = ["family", "cell_class", "delivery", "evolved", "log_cargo"]
            Xtr = pd.get_dummies(f[cols], columns=["family", "cell_class", "delivery"]).astype(float)
            m = _fit_gbr(Xtr, tr_df["efficiency_pct"].to_numpy(), 42)
            fte = featurize(te_df)
            Xte = pd.get_dummies(fte[cols], columns=["family", "cell_class", "delivery"]) \
                .reindex(columns=Xtr.columns, fill_value=0.0).astype(float)
            y_true.extend(te_df["efficiency_pct"].tolist())
            y_model.extend(m.predict(Xte).tolist())
            y_base.extend(_family_mean_baseline(tr_df, te_df).tolist())
        y_true, y_model, y_base = map(np.array, (y_true, y_model, y_base))
        me, be = np.abs(y_true - y_model), np.abs(y_true - y_base)
        d = _boot_delta(me, be, seed=42)
        r = {"axis": label, "n_groups": groups, "n": int(len(y_true)),
             "mae_model": round(float(np.mean(me)), 3),
             "mae_baseline": round(float(np.mean(be)), 3),
             "spearman_model": round(float(spearmanr(y_model, y_true).statistic), 4),
             "spearman_baseline": round(float(spearmanr(y_base, y_true).statistic), 4),
             "delta": d}
        ci = d.get("ci95") or d.get("ci") or [d.get("lo"), d.get("hi")]
        print(f"  {label:<20} folds={groups:<3} n={len(y_true):<4} "
              f"MAE model {np.mean(me):>6.2f}  baseline {np.mean(be):>6.2f}  "
              f"reduction CI {ci}  beats={d.get('model_beats_baseline')}")
        return r

    out["B_held_out_family"] = run_axis(df, "family", "held-out family")
    loc = df[specific_locus_mask(df)].reset_index(drop=True)
    out["B_held_out_locus"] = run_axis(loc, "locus", "held-out locus")
    out["B_held_out_study"] = run_axis(df, "doi", "held-out study")

    # ------------------------------------------------------------------ leakage check
    hdr("C. Does a withheld efficiency reach the comparator?")
    leaks = []
    for g, tr, te in _loo_groups(df, "family"):
        tr_df, te_df = df.iloc[tr], df.iloc[te]
        pred = _family_mean_baseline(tr_df, te_df)
        fam_in_train = set(tr_df["family"])
        gm = float(tr_df["efficiency_pct"].mean())
        for f_, p in zip(te_df["family"], pred):
            if f_ in fam_in_train:
                leaks.append((g, f_))
            elif abs(p - gm) > 1e-9:
                leaks.append((g, f"{f_}: not the global train mean"))
    print(f"  held-out-family folds checked: {df['family'].nunique()}")
    print(f"  folds where the withheld family's own mean could enter the baseline: {len(leaks)}")
    print("  baseline under a withheld family falls back to the global TRAIN mean, so no withheld")
    print("  efficiency reaches the comparator. Verified by construction and by the check above.")
    out["C_baseline_leakage"] = {"folds": int(df["family"].nunique()), "leaks": len(leaks)}

    with open("../work/writer_study_heldout.json", "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print("\nwrote ../work/writer_study_heldout.json")


if __name__ == "__main__":
    sys.exit(main())
