#!/usr/bin/env python3
"""Recompute the headline human K562 expression-robustness result from source, not from a stored number.

This trains the shipped position-effect twin on the measured Leemans 2019 K562 TRIP data
(`benchmarks/position_effect_human/leemans_scored_input.parquet`, a committed derived features table built
from the public Leemans expression and ENCODE chromatin marks), holds out chromosomes 3, 8, and 12 exactly as
the sealed pre-registration specifies, scores held-out Spearman correlation, and asserts the recomputed value
matches the committed metrics. Run by `make repro-human`.

The split is by chromosome (chr3/8/12), not a random partition, so it is deterministic without a seed; the
model's own random_state is fixed. Offline: no network, no LLM, no oracle calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "position_effect_human"
INPUT = BENCH / "leemans_scored_input.parquet"
SPLIT = json.loads((BENCH / "split.json").read_text(encoding="utf-8"))
METRICS = json.loads((BENCH / "metrics.json").read_text(encoding="utf-8"))

HELD = set(SPLIT["chrom_holdout"]["test_chroms"])           # {chr3, chr8, chr12}, sealed
MARKS = {"H3K27ac_mean": "H3K27ac", "H3K4me1_mean": "H3K4me1", "H3K9me3_mean": "H3K9me3",
         "H3K27me3_mean": "H3K27me3", "H3K36me3_mean": "H3K36me3"}
FULL = ["H3K27ac", "H3K4me1", "H3K9me3", "H3K27me3", "H3K36me3"]
INDEPENDENT = ["H3K27ac", "H3K4me1", "H3K36me3"]            # lamina/heterochromatin marks removed (de-circular)


def main() -> int:
    if not INPUT.exists():
        print(f"[fail] {INPUT} not found. It is a committed derived table; fetch the release with "
              "`bash scripts/fetch_artifacts.sh` if you are on a partial checkout.", file=sys.stderr)
        return 2
    from pen_stack.twin.position_effect import PositionEffectModel

    df = pd.read_parquet(INPUT)
    df["expr_y"] = df["expr_y"].astype(float)
    tw = pd.DataFrame({"dataset": "Leemans2019", "organism": "human", "cell_type": "K562",
                       "chrom": df["chrom"].astype(str), "cassette": df["prom_name"].astype(str),
                       "expression_raw": df["expr_y"],
                       "silenced": df["class"].astype(str).str.lower().eq("repressed")})
    for src, dst in MARKS.items():
        tw[dst] = df[src].astype(float)
    te = tw["chrom"].isin(HELD).to_numpy()
    tr, teN = tw[~te].copy(), tw[te].copy()
    y_te = teN["expression_raw"].to_numpy()
    print(f"[split] chromosome-holdout {sorted(HELD)}: train={len(tr)} held-out={len(teN)}")

    def twin_rho(feature_marks):
        drop = [c for c in MARKS.values() if c not in feature_marks]
        m = PositionEffectModel().fit(tr.drop(columns=drop))
        return float(spearmanr(m.predict_expression(teN.drop(columns=drop)), y_te).statistic)

    rho_full = twin_rho(FULL)
    rho_indep = twin_rho(INDEPENDENT)
    print(f"[recomputed] shipped-twin FULL rho = {rho_full:.4f} | INDEPENDENT (de-circular) rho = {rho_indep:.4f}")

    sealed = METRICS["fresh_sealed_heldout"]
    exp_full, exp_indep = sealed["shipped_twin_full_rho"], sealed["independent_variant_rho"]
    print(f"[committed]  shipped_twin_full_rho = {exp_full} | independent_variant_rho = {exp_indep}")

    tol = 0.02  # lightgbm is not bit-identical across BLAS/thread builds; assert the number, not the byte
    ok_full = abs(rho_full - exp_full) <= tol
    ok_indep = abs(rho_indep - exp_indep) <= tol
    print(f"[check] full within {tol}: {ok_full} | independent within {tol}: {ok_indep}")
    if not (ok_full and ok_indep):
        print("[fail] recomputed correlation does not match the committed metrics", file=sys.stderr)
        return 1
    print(f"[ok] headline result recomputed from source (rho ~ {rho_full:.3f}, held out on chr3/8/12).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
