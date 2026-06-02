"""Two-stratum, goal-conditioned recovery@k benchmark (Phase 3, Step 3.5) — PAPER-DEFINING, gating.

Show the Write Planner recovers documented targeted-writes — *especially the non-obvious ones a naive
baseline cannot* — from the goal (gene + edit_intent) alone, with the precise site held out. The panel is
adversarial to the baseline by construction:

  * Control stratum (safe-harbour writes): a safety ranker should recover these — the Planner must not be
    worse.
  * Discriminating stratum (therapeutic-into-functional-locus writes): an intent-blind safety ranker keeps
    proposing safe harbours and *misses* the intended (often intragenic) target; the Planner, conditioned
    on edit_intent, recovers them. This is the headline.

Anti-leakage: the Planner scores a fixed candidate POOL (panel loci + decoy genes) from the goal only;
recovery@k = the documented locus appearing in the Planner's top-k. The baseline ranks the same pool by
safety alone (intent-blind). Reported per stratum with a McNemar exact test + bootstrap CI of the gap.

Inputs : data/benchmark_panel.csv (frozen, SHA-locked in prereg/paper3.yaml); Phase-1 writability atlas.
Outputs: out/benchmark_report.json.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from pen_stack.planner.optimize import load_intent_weights, score_candidates

_ROOT = Path(__file__).resolve().parents[2]
_PANEL = _ROOT / "data" / "benchmark_panel.csv"
_OUT = _ROOT / "out" / "benchmark_report.json"
BIN_BP = 1000
N_DECOYS = 30
SEED = 20260602


@lru_cache(maxsize=4)
def _gene_coords() -> pd.DataFrame:
    return pd.read_parquet(_ROOT.parent / "phase_1" / "app_data" / "gene_coords.parquet")


def _gene_candidate(gene: str, writable_df: pd.DataFrame) -> dict | None:
    """Aggregate a gene's body bins into one pool candidate (mean safety/durability + a representative bin)."""
    gc = _gene_coords()
    g = gc[gc["gene"] == gene]
    if g.empty:
        return None
    r = g.iloc[0]
    lo, hi = int(r["start"]) // BIN_BP, int(r["end"]) // BIN_BP
    body = writable_df[(writable_df["chrom"] == r["chrom"]) & (writable_df["bin"].between(lo, hi))]
    if body.empty:
        return None
    # represent the locus by its BEST writable bin — the site a planner would actually target within it
    best = body.loc[body["writability"].idxmax()]
    return {"gene": gene, "chrom": r["chrom"], "bin": int(best["bin"]),
            "safety": float(best["safety"]), "p_durable": float(best["p_durable"]),
            "reachable_tier1": best["reachable_tier1"]}


def build_pool(panel: pd.DataFrame, writable_df: pd.DataFrame, n_decoys: int = N_DECOYS) -> pd.DataFrame:
    """Candidate pool = panel genes + random decoy genes (deterministic), aggregated in this cell type."""
    rows = []
    for gene in panel["gene"].unique():
        c = _gene_candidate(gene, writable_df)
        if c:
            rows.append(c)
    gc = _gene_coords()
    rng = np.random.default_rng(SEED)
    pool_genes = set(panel["gene"])
    decoy_choices = gc[~gc["gene"].isin(pool_genes)]["gene"].dropna().unique()
    for gene in rng.choice(decoy_choices, size=min(n_decoys, len(decoy_choices)), replace=False):
        c = _gene_candidate(gene, writable_df)
        if c:
            rows.append(c)
    return pd.DataFrame(rows).drop_duplicates("gene").reset_index(drop=True)


def _writable(ct: str) -> pd.DataFrame:
    from pen_stack.atlas.crosslink import load_writability
    return load_writability(ct)


def recovery_at_k(panel: pd.DataFrame, k: int = 10, cargo_bp: int = 2000) -> pd.DataFrame:
    """Planner (goal-conditioned) vs baseline (intent-blind safety), recovery@k per panel entry."""
    rows = []
    pools: dict[str, pd.DataFrame] = {}
    for _, t in panel.iterrows():
        ct = t["ct"]
        if ct not in pools:
            pools[ct] = build_pool(panel, _writable(ct))
        pool = pools[ct].copy()
        # PLANNER: score the pool with this entry's intent. on_target marks the entry's own target gene
        # ONLY for *targeted* intents; safe-harbour is genome-wide (the destination is not a gene-to-avoid),
        # so on_target stays False and recovery is pure safety x durability ranking.
        genome_wide = bool(load_intent_weights()["intents"][t["intent"]].get("genome_wide", False))
        pool["on_target"] = (pool["gene"] == t["gene"]) & (not genome_wide)
        scored = score_candidates(pool, t["intent"], cargo_bp)
        planner_topk = list(scored.head(k)["gene"])
        # BASELINE: intent-blind, rank the same pool by safety only
        baseline_topk = list(pool.sort_values("safety", ascending=False).head(k)["gene"])
        rows.append({"name": t["name"], "gene": t["gene"], "stratum": t["stratum"],
                     "intent": t["intent"],
                     "planner_hit": int(t["gene"] in planner_topk),
                     "baseline_hit": int(t["gene"] in baseline_topk)})
    return pd.DataFrame(rows)


def stratified_report(rec: pd.DataFrame) -> dict:
    from statsmodels.stats.contingency_tables import mcnemar
    out = {}
    for s in ["control", "discriminating"]:
        sub = rec[rec["stratum"] == s]
        if sub.empty:
            continue
        b = int(((sub.planner_hit == 1) & (sub.baseline_hit == 0)).sum())   # planner wins
        c = int(((sub.planner_hit == 0) & (sub.baseline_hit == 1)).sum())   # baseline wins
        a = int(((sub.planner_hit == 1) & (sub.baseline_hit == 1)).sum())
        d = int(((sub.planner_hit == 0) & (sub.baseline_hit == 0)).sum())
        res = mcnemar([[a, b], [c, d]], exact=True)
        # bootstrap CI of the recovery gap (planner - baseline)
        diff = (sub.planner_hit - sub.baseline_hit).to_numpy()
        rng = np.random.default_rng(SEED)
        boot = [rng.choice(diff, size=len(diff), replace=True).mean() for _ in range(5000)]
        ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
        out[s] = {"n": int(len(sub)),
                  "planner_recovery": round(float(sub.planner_hit.mean()), 4),
                  "baseline_recovery": round(float(sub.baseline_hit.mean()), 4),
                  "planner_wins": b, "baseline_wins": c,
                  "mcnemar_pvalue": float(res.pvalue),
                  "gap_mean": round(float(diff.mean()), 4),
                  "gap_ci95": [round(ci[0], 4), round(ci[1], 4)],
                  "ci_excludes_zero": bool(ci[0] > 0)}
    return out


def run(k: int = 10, out: str | Path = _OUT) -> dict:
    panel = pd.read_csv(_PANEL)
    rec = recovery_at_k(panel, k=k)
    report = {"k": k, "n_panel": len(panel), "strata": stratified_report(rec),
              "per_case": rec.to_dict("records")}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    r = run()
    print(json.dumps(r["strata"], indent=2))
    print("\nper-case:")
    for c in r["per_case"]:
        print(f"  [{c['stratum'][:4]}] {c['name']:8s} {c['intent']:26s} planner={c['planner_hit']} baseline={c['baseline_hit']}")
