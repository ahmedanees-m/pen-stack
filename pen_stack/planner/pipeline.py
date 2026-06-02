"""End-to-end Write Planner (Phase 3, Step 3.4).

One call — ``plan_write(gene, intent, payload_bp, ct)`` — composes the inverse-design optimiser (3.1),
cargo/donor design (3.2), and delivery recommendation (3.3) into ranked, fully traceable plans. Every
numeric field is tagged with the module/dataset that produced it (provenance), so nothing is asserted
without a source. Heavy data (the Phase-1 writability atlas) is loaded lazily via the cross-link.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from pen_stack.planner.cargo import design_cargo
from pen_stack.planner.delivery import recommend_delivery
from pen_stack.planner.optimize import EditIntent, plan

_ATLAS = Path(__file__).resolve().parents[1] / "atlas" / "atlas.parquet"
BIN_BP = 1000


@lru_cache(maxsize=1)
def _writer_meta() -> dict:
    """family -> {length_aa, cargo_capacity_bp, deliv_class, reachability_tier} from the Writer Atlas."""
    atlas = pd.read_parquet(_ATLAS)
    core = atlas[atlas["entry_kind"] == "curated_core"] if "entry_kind" in atlas else atlas
    meta = {}
    for fam, sub in core.groupby("family"):
        r = sub.iloc[0]
        meta[fam] = {
            "length_aa": (int(r["length_aa"]) if pd.notna(r.get("length_aa")) else None),
            "cargo_capacity_bp": (int(r["cargo_capacity_bp"]) if pd.notna(r.get("cargo_capacity_bp")) else None),
            "deliv_class": r.get("deliv_class"),
            "reachability_tier": r.get("reachability_tier"),
        }
    return meta


def plan_write(gene: str, intent: EditIntent | str, payload_bp: int, ct: str = "k562",
               k: int = 5, writable_df: pd.DataFrame | None = None) -> list[dict]:
    """Return ranked, traceable write plans for a goal. Each plan = site + writer + cargo + delivery."""
    if writable_df is None:
        from pen_stack.atlas.crosslink import load_writability
        writable_df = load_writability(ct)
    cands = plan(gene, intent, payload_bp, writable_df, k=k)
    meta = _writer_meta()
    plans = []
    for _, row in cands.iterrows():
        fam = row["writer"]
        wm = meta.get(fam, {})
        writer_row = {"family": fam, "cargo_capacity_bp": wm.get("cargo_capacity_bp"),
                      "deliv_class": wm.get("deliv_class")}
        site = (row["chrom"], int(row["bin"]) * BIN_BP)
        cargo = design_cargo(payload_bp, writer_row, site, ct)
        eff_bp = (wm.get("length_aa") or 0) * 3
        deliv = recommend_delivery(eff_bp, payload_bp, ct)
        plans.append({
            "gene": gene, "intent": EditIntent(intent).value if not isinstance(intent, EditIntent) else intent.value,
            "site": {"chrom": row["chrom"], "bin": int(row["bin"]), "pos": site[1]},
            "writer": fam,
            "reachability_tier": wm.get("reachability_tier"),
            "safety": round(float(row["safety"]), 4),
            "durability": round(float(row["p_durable"]), 4),
            "writer_activity": round(float(row["writer_activity"]), 4),
            "on_target": bool(row["on_target"]),
            "score": round(float(row["score"]), 4),
            "cargo": cargo,
            "delivery": deliv,
            "provenance": {
                "safety": "wgenome.safety (LightGBM, COSMIC/DepMap/MLV)",
                "durability": "wgenome.durability (TRIP conditional chromatin model)",
                "writer_activity": "atlas.score.therapeutic (measured human-cell axis)",
                "reachability": "atlas.crosslink (Phase-1 reachable_tier1 + WT-KB tier)",
                "delivery": "planner.delivery (configs/delivery_rules.yaml)",
                "offtargets": "planner.cargo (bridge engine = Phase 1.5)",
            },
            "disclaimer": "Decision-support only; not a clinical directive. Tier-2/3 reachability is candidate.",
        })
    return plans


if __name__ == "__main__":  # pragma: no cover
    import json
    ps = plan_write("TRAC", EditIntent.KNOCK_IN_DISRUPT, 2000, "k562", k=3)
    print(json.dumps(ps[0], indent=2, default=str)[:1200])
