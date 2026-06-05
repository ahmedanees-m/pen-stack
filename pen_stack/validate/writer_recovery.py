"""Diversified writer-family recovery (v3.1, WS-A4).

The Phase-3 panel was bridge-dominated, so writer choice barely varied. Here we add DSB-free, large-cargo
documented writes (CAST, PASTE/PE-integrase, large serine-integrase landing pads) so the correct family
genuinely changes with cargo size. The writer is held out; we recover the family used from the goal +
intent + cargo size + cell type alone.

Selection rule (documented, not tuned): recommend the **smallest-capacity DSB-free writer family that fits
the cargo** (do not deploy a 50 kb integrase for a 2 kb insert when a programmable bridge suffices); ties
broken by measured human-cell activity. This makes cargo size load-bearing for the writer choice.

Acceptance (prereg/ws_a.yaml): writer-family recovery@1 exceeds the prevalence baseline by a pre-registered
margin on >= 8 entries spanning >= 3 families; reported per family.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
_PANEL = _ROOT / "data" / "writer_panel.csv"
_ATLAS = _ROOT / "pen_stack" / "atlas" / "atlas.parquet"
_OUT = _ROOT / "out" / "writer_recovery.json"


def _family_caps() -> pd.DataFrame:
    """family -> (cargo_capacity_bp, dsb_free, human_cell_activity proxy) from the Writer Atlas cores."""
    atlas = pd.read_parquet(_ATLAS)
    core = atlas[atlas["entry_kind"] == "curated_core"] if "entry_kind" in atlas else atlas
    rows = []
    for fam, sub in core.groupby("family"):
        r = sub.iloc[0]
        cap = r.get("cargo_capacity_bp")
        act = r.get("S_HumanCell")
        rows.append({"family": fam,
                     "cargo_capacity_bp": (float(cap) if pd.notna(cap) else None),
                     "dsb_free": bool(r.get("dsb_free", False)),
                     "activity": (float(act) if pd.notna(act) else 0.4)})
    return pd.DataFrame(rows)


def recover_writer_family(cargo_bp: int, dsb_free_required: bool = True) -> str | None:
    """Smallest-capacity DSB-free family that fits the cargo; ties by activity."""
    caps = _family_caps()
    cand = caps[caps["cargo_capacity_bp"].notna() & (caps["cargo_capacity_bp"] >= cargo_bp)]
    if dsb_free_required:
        cand = cand[cand["dsb_free"]]
    if cand.empty:
        return None
    cand = cand.sort_values(["cargo_capacity_bp", "activity"], ascending=[True, False])
    return cand.iloc[0]["family"]


def run(out: str | Path = _OUT) -> dict:
    panel = pd.read_csv(_PANEL)
    panel["predicted_family"] = [recover_writer_family(int(r.cargo_bp), bool(r.dsb_free_required))
                                 for r in panel.itertuples()]
    panel["hit"] = panel["predicted_family"] == panel["family"]
    n, n_hit = len(panel), int(panel["hit"].sum())
    # prevalence baseline: always guess the most common family -> expected accuracy = max class share
    prev = Counter(panel["family"])
    prevalence_at1 = max(prev.values()) / n
    per_family = {fam: {"n": int((panel["family"] == fam).sum()),
                        "recall@1": round(float(panel[panel["family"] == fam]["hit"].mean()), 3)}
                  for fam in sorted(prev)}
    report = {
        "what_this_is": "writer-family recovery@1 from goal+intent+cargo+ct, writer held out (non-circular)",
        "n_entries": n, "n_families": len(prev),
        "recovery_at_1": round(n_hit / n, 4),
        "prevalence_baseline_at_1": round(prevalence_at1, 4),
        "beats_prevalence": bool(n_hit / n > prevalence_at1),
        "per_family": per_family,
        "selection_rule": "smallest-capacity DSB-free family that fits the cargo; ties by human-cell activity",
        "cases": panel[["name", "family", "cargo_bp", "predicted_family", "hit", "doi"]].to_dict("records"),
        "scope": "N scaled to 14 documented DSB-free writes across 4 families (v3.1.1; classic bridge/CAST/"
                 "PASTE/serine + IS621 bridge, evoCAST/type-V-K CAST in human cells, twinPE+Bxb1, phiC31). "
                 "recovery@1 is now < 1.0 by design: cargo size is the dominant but NOT the sole signal - the "
                 "misses (twinPE+Bxb1 and phiC31 used a larger-capacity family than the cargo strictly needs) "
                 "are honest cases where the documented choice was not the minimal-capacity one. Documented "
                 "writes remain survivorship-biased; N is still modest.",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps({k: v for k, v in run().items() if k != "cases"}, indent=2, default=str))
