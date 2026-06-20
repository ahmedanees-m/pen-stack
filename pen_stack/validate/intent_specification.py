"""Intent specification-compliance (v3.1, WS-A2) - NOT a predictive benchmark.

This reframes the former "discriminating-stratum recovery@k" result. For a *targeted* intent the planner
ranks the goal's own gene first by construction (see docs/benchmark_circularity.md), so gene-level recovery
is definitional and must NOT be reported as predictive skill or carry a p-value/CI.

What remains valid is a **behavioral-correctness** property: does the same locus change rank under opposing
goals exactly as specified? An in-gene site must rank HIGH under a disruption/excision intent (hitting the
gene is the goal) and LOW under safe-harbour insertion (the gene must be avoided). We report this as an
exact-match correctness table, never as recovery or a hypothesis test.

Outputs: out/intent_specification.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pen_stack.planner.optimize import EditIntent, plan

_OUT = Path(__file__).resolve().parents[2] / "out" / "intent_specification.json"
_WDF = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / "atlas_k562.parquet"

# (gene, targeted-intent) pairs whose documented write is INSIDE the gene/element.
_CASES = [
    ("TRAC", EditIntent.KNOCK_IN_DISRUPT),
    ("PDCD1", EditIntent.KNOCK_IN_DISRUPT),
    ("B2M", EditIntent.KNOCK_IN_DISRUPT),
    ("BCL11A", EditIntent.REG_EXCISION),
    ("HBG1", EditIntent.REG_EXCISION),
    ("FXN", EditIntent.REPEAT_EXCISION),
    ("ALB", EditIntent.HIGH_DURABILITY),
]


def _top_is_on_target(gene: str, intent: EditIntent, wdf: pd.DataFrame, k: int = 5) -> bool | None:
    ranked = plan(gene, intent, 2000, wdf, k=k)
    if ranked.empty:
        return None
    return bool(ranked.iloc[0]["on_target"])


def specification_table(wdf: pd.DataFrame | None = None) -> pd.DataFrame:
    if wdf is None:
        wdf = pd.read_parquet(_WDF)
    rows = []
    for gene, targeted in _CASES:
        # under the targeted intent the in-gene site SHOULD rank #1 (hitting the gene is the goal)
        under_targeted = _top_is_on_target(gene, targeted, wdf)
        # under safe-harbour the same in-gene site should NOT rank #1 (the gene must be avoided)
        under_safe = _top_is_on_target(gene, EditIntent.SAFE_HARBOUR, wdf)
        correct = (under_targeted is True) and (under_safe is False)
        rows.append({"gene": gene, "targeted_intent": targeted.value,
                     "top_on_target_under_targeted": under_targeted,
                     "top_on_target_under_safe_harbour": under_safe,
                     "specification_correct": correct})
    return pd.DataFrame(rows)


def run(out: str | Path = _OUT) -> dict:
    tab = specification_table()
    n = len(tab)
    n_correct = int(tab["specification_correct"].sum())
    report = {
        "what_this_is": "behavioral specification-compliance, NOT a predictive benchmark or recovery metric",
        "property": "the same locus must rank high under a targeted intent and low under safe-harbour",
        "n_cases": n,
        "n_correct": n_correct,
        "all_correct": n_correct == n,
        "table": tab.to_dict("records"),
        "scope": "definitional by design; no recovery@k, p-value, or CI is attached to this result. The "
                 "predictive headline is the blind safe-harbour discovery (WS-A3), not this table.",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
