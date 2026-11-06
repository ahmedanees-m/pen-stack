"""Writer-efficiency: source provenance against writer family, and the sensitivity that follows.

Source-access grade and writer family are not separable in this table. All six records that are not
`pmc_verbatim` belong to `bridge_IS110`, and that family carries no `pmc_verbatim` record, so
restricting the table by source grade and removing a family are close to the same operation. A
subset selected on source grade therefore does not isolate provenance quality, and this script
reports the structure rather than presenting such a subset as a provenance control.

What it establishes, on the repository's own featurisation, fitting, baseline and bootstrap, with
only the row basis changed:

  * the held-out-locus axis carries no non-primary row at all, because every non-primary human
    record sits at an aggregate pseudo-locus that the specific-locus mask already excludes, so that
    axis is invariant to the source-grade basis and is reported as identical rather than re-derived;
  * the held-out-family result spans zero on the full basis and on the three families that carry
    full primary-source provenance, so the cross-family outcome does not rest on source grade;
  * the held-out-study axis is reported on each basis, and its released-basis metrics are committed
    here.

The frozen split and the dataset parquet are inputs and are never written. The subset basis is
passed as a parameter, so `split.json` and its checksum stand unchanged.

Run from the repository root:  python benchmarks/writer_efficiency/provenance_sensitivity.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_PRIMARY_GRADE = "pmc_verbatim"


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
    raw = pd.read_parquet("data/writer_efficiency.parquet")
    full = human_cell(strict=False).reset_index(drop=True)

    # ---------------------------------------------------------------- the structure
    hdr("A. Source grade against writer family")
    ct = pd.crosstab(raw["family"], raw["source_access"])
    print(ct.to_string())
    weak = raw[raw["source_access"] != _PRIMARY_GRADE]
    bridge = raw[raw["family"] == "bridge_IS110"]
    collinear = set(weak.index) == set(bridge.index)
    print(f"\n  records not {_PRIMARY_GRADE:<14} {len(weak)}")
    print(f"  records in bridge_IS110        {len(bridge)}")
    print(f"  the two sets are identical     {collinear}")
    print(f"  bridge_IS110 primary records   "
          f"{int((bridge['source_access'] == _PRIMARY_GRADE).sum())}")
    print("\n  Consequence: a subset taken on source grade is also a subset taken on family, so it")
    print("  measures family composition and not provenance quality.")
    out["A_grade_against_family"] = {
        "crosstab": {f: {g: int(n) for g, n in row.items()} for f, row in ct.iterrows()},
        "n_non_primary": int(len(weak)),
        "n_bridge_IS110": int(len(bridge)),
        "non_primary_set_equals_bridge_set": bool(collinear),
        "bridge_IS110_primary_records": int((bridge["source_access"] == _PRIMARY_GRADE).sum()),
        "non_primary_rows": [
            {"family": r["family"], "system": r["system"], "organism": r["organism"],
             "cell_type": r["cell_type"], "locus": r["locus"],
             "efficiency_pct": float(r["efficiency_pct"]), "efficiency_raw": str(r["efficiency_raw"]),
             "source_access": r["source_access"], "doi": r["doi"]}
            for _, r in weak.iterrows()],
    }

    # ---------------------------------------------------------------- why the locus axis is clean
    hdr("B. Why the held-out-locus axis carries no non-primary row")
    loc_full = full[specific_locus_mask(full)].reset_index(drop=True)
    dropped = full[~specific_locus_mask(full)]
    print(f"  human records                        {len(full)}")
    print(f"  held-out-locus basis                 {len(loc_full)}")
    print(f"  removed by the specific-locus mask   {len(dropped)}")
    print("\n  records the mask removes:")
    for _, r in dropped.iterrows():
        print(f"    {r['family']:<18} {r['cell_type']:<12} {r['locus']:<16} {r['source_access']}")
    n_weak_on_locus = int((loc_full["source_access"] != _PRIMARY_GRADE).sum())
    print(f"\n  non-primary records on the held-out-locus basis   {n_weak_on_locus}")
    print(f"  the held-out-locus basis is wholly primary-source {n_weak_on_locus == 0}")
    out["B_locus_basis"] = {
        "n_human": int(len(full)), "n_locus_basis": int(len(loc_full)),
        "n_removed_by_mask": int(len(dropped)),
        "removed": [{"family": r["family"], "locus": r["locus"],
                     "source_access": r["source_access"]} for _, r in dropped.iterrows()],
        "n_non_primary_on_locus_basis": n_weak_on_locus,
        "locus_basis_wholly_primary_source": n_weak_on_locus == 0,
    }

    # ---------------------------------------------------------------- the axes, three bases
    def run_axis(sub, by, specific_locus=False):
        sub = (sub[specific_locus_mask(sub)] if specific_locus else sub).reset_index(drop=True)
        y_true, y_model, y_base, folds = [], [], [], []
        cols = ["family", "cell_class", "delivery", "evolved", "log_cargo"]
        for g, tr, te in _loo_groups(sub, by):
            tr_df, te_df = sub.iloc[tr], sub.iloc[te]
            Xtr = pd.get_dummies(featurize(tr_df)[cols],
                                 columns=["family", "cell_class", "delivery"]).astype(float)
            m = _fit_gbr(Xtr, tr_df["efficiency_pct"].to_numpy(), 42)
            Xte = pd.get_dummies(featurize(te_df)[cols],
                                 columns=["family", "cell_class", "delivery"]) \
                .reindex(columns=Xtr.columns, fill_value=0.0).astype(float)
            y_true.extend(te_df["efficiency_pct"].tolist())
            y_model.extend(m.predict(Xte).tolist())
            y_base.extend(_family_mean_baseline(tr_df, te_df).tolist())
            folds.append({"group": str(g), "n_train": int(len(tr)), "n_test": int(len(te))})
        if not y_true:
            return None
        yt, ym, yb = map(np.array, (y_true, y_model, y_base))
        me, be = np.abs(yt - ym), np.abs(yt - yb)
        return {"n": int(len(yt)), "n_folds": len(folds), "folds": folds,
                "mae_model": float(np.mean(me)), "mae_baseline_family_mean": float(np.mean(be)),
                "spearman_model": float(spearmanr(ym, yt).statistic),
                "spearman_baseline": float(spearmanr(yb, yt).statistic),
                "delta": _boot_delta(me, be, seed=42)}

    hdr("C. Reproduce the released result before any subset is reported")
    released = json.loads(open(os.path.join(_HERE, "result.json"), encoding="utf8").read())
    check = {"held_out_family": run_axis(full, "family"),
             "held_out_locus": run_axis(full, "locus", specific_locus=True)}
    exact = True
    for axis in ("held_out_family", "held_out_locus"):
        a, b = released[axis], check[axis]
        for k in ("n", "mae_model", "mae_baseline_family_mean"):
            same = a[k] == b[k] if isinstance(a[k], int) else abs(a[k] - b[k]) < 1e-12
            exact &= same
            print(f"  {axis:<18} {k:<26} {'matches' if same else 'DIFFERS'}")
        same_ci = all(abs(x - y) < 1e-12 for x, y in zip(a["delta"]["ci95"], b["delta"]["ci95"]))
        exact &= same_ci
        print(f"  {axis:<18} {'delta.ci95':<26} {'matches' if same_ci else 'DIFFERS'}")
    print(f"\n  released metrics reproduce exactly   {exact}")
    out["C_reproduces_released_result"] = bool(exact)
    if not exact:
        raise SystemExit("the axis runner does not reproduce result.json; subset metrics withheld")

    strict = human_cell(strict=True).reset_index(drop=True)
    primary = full[full["source_access"] == _PRIMARY_GRADE].reset_index(drop=True)
    bases = [("full", "every human-cell record, the released basis", full),
             ("strict_grade", "pmc_verbatim and abstract, which leaves bridge_IS110 a single "
                              "record and the cross-family fold degenerate", strict),
             ("primary_source", "pmc_verbatim only, which is the three families carrying full "
                                "primary-source provenance", primary)]

    hdr("D. The three axes on each basis")
    out["D_axes"] = {}
    for key, note, d in bases:
        comp = {k: int(v) for k, v in d["family"].value_counts().items()}
        print(f"\n  basis {key}  n={len(d)}  families={d['family'].nunique()}  {comp}")
        print(f"    {note}")
        rec = {"description": note, "n": int(len(d)), "n_families": int(d["family"].nunique()),
               "family_composition": comp, "axes": {}}
        for axis, by, sl in (("held_out_family", "family", False),
                             ("held_out_locus", "locus", True),
                             ("held_out_study", "doi", False)):
            r = run_axis(d, by, specific_locus=sl)
            rec["axes"][axis] = r
            if r is None:
                print(f"    {axis:<16} no evaluable fold")
                continue
            lo, hi = r["delta"]["ci95"]
            print(f"    {axis:<16} folds={r['n_folds']:<3} n={r['n']:<3} "
                  f"MAE {r['mae_model']:>6.2f} against {r['mae_baseline_family_mean']:>6.2f}   "
                  f"reduction [{lo:+.2f}, {hi:+.2f}]  excludes zero "
                  f"{r['delta']['model_beats_baseline']}")
        out["D_axes"][key] = rec

    # ---------------------------------------------------------------- the invariance claim
    hdr("E. Is the held-out-locus axis invariant to the source-grade basis?")
    ref = out["D_axes"]["full"]["axes"]["held_out_locus"]
    inv = {}
    for key in ("strict_grade", "primary_source"):
        cand = out["D_axes"][key]["axes"]["held_out_locus"]
        same = (ref["n"] == cand["n"]
                and all(abs(ref[k] - cand[k]) < 1e-12 for k in
                        ("mae_model", "mae_baseline_family_mean", "spearman_model",
                         "spearman_baseline"))
                and ref["delta"]["ci95"] == cand["delta"]["ci95"])
        inv[key] = bool(same)
        print(f"  full against {key:<16} identical {same}   n {ref['n']} and {cand['n']}")
    out["E_locus_axis_invariant"] = inv

    dest = os.path.join(_HERE, "provenance_sensitivity.json")
    with open(dest, "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\nwrote {os.path.relpath(dest, os.getcwd())}")


if __name__ == "__main__":
    sys.exit(main())
