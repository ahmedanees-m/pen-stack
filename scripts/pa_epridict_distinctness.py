#!/usr/bin/env python3
"""Recompute the ePRIDICT-distinctness headline (Spearman rho and variance-partition R-squared) from source.

The prior-art claim is that PEN-STACK's durability axis (p_durable) is DISTINCT from ePRIDICT's integration
efficiency, not a renamed version of it. This reads the committed merged per-locus score table
(`benchmarks/priorart/epridict/shared_loci_scores.csv`, the 7295 shared K562 loci where both scores exist),
recomputes the Spearman correlation and the ordinary-least-squares variance explained, and asserts they match
the committed `epridict_orthogonality_metrics.json`. Deterministic and offline: no bootstrap, no network, no
model. Run by `make repro`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "priorart" / "epridict"
INPUT = BENCH / "shared_loci_scores.csv"
METRICS = json.loads((BENCH / "epridict_orthogonality_metrics.json").read_text(encoding="utf-8"))

TOL = 5e-4  # the committed values are display-rounded; assert the number, not the last float bit


def main() -> int:
    if not INPUT.exists():
        print(f"[fail] {INPUT} not found (committed derived table).", file=sys.stderr)
        return 2
    df = pd.read_csv(INPUT).dropna(subset=["epridict_efficiency", "p_durable"])
    x = df["epridict_efficiency"].to_numpy()
    y = df["p_durable"].to_numpy()
    print(f"[data] shared K562 loci with both scores: n={len(df)} (committed n_analyzed="
          f"{METRICS.get('n_analyzed')})")

    rho = float(spearmanr(y, x).statistic)
    r = float(pearsonr(y, x)[0])
    # variance partition: OLS p_durable ~ epridict_efficiency, report the R-squared (variance explained)
    xmat = np.vstack([np.ones_like(x), x]).T
    beta, *_ = np.linalg.lstsq(xmat, y, rcond=None)
    yhat = xmat @ beta
    r2 = float(1.0 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum())
    print(f"[recomputed] spearman rho = {rho:.5f} | pearson r = {r:.5f} | OLS R2 = {r2:.5f}")

    exp_rho = METRICS["spearman_rho"]
    exp_r = METRICS["pearson_r"]
    exp_r2 = METRICS["variance_partition"]["R2"]
    print(f"[committed]  spearman rho = {exp_rho:.5f} | pearson r = {exp_r:.5f} | OLS R2 = {exp_r2:.5f}")

    checks = {"spearman_rho": abs(rho - exp_rho) <= TOL, "pearson_r": abs(r - exp_r) <= TOL,
              "R2": abs(r2 - exp_r2) <= TOL}
    print(f"[check] within {TOL}: {checks}")
    if not all(checks.values()):
        print("[fail] recomputed distinctness metrics do not match the committed values", file=sys.stderr)
        return 1
    print(f"[ok] ePRIDICT-distinctness recomputed from source: rho ~ {rho:.3f}, R2 ~ {r2:.3f} "
          f"({round((1 - r2) * 100)}% of durability variance unexplained by ePRIDICT efficiency). "
          f"Decision: {METRICS.get('decision')}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
