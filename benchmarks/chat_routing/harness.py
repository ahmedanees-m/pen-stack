"""Routing benchmark (PEN-CHAT P-WS4).

Scores the deterministic router (`pen_stack.web.router.classify`) on a sealed, labelled query set across the four
lanes (design / explain / meta / general). Deterministic, no LLM/embedder, so it is fully reproducible in CI.

Reports per-lane precision/recall/F1, the confusion matrix, and THE safety-critical metric (gate P-G2):
    routing_safety_metric = P(a write/result request is routed to a NON-grounded lane, i.e. 'general')
A write/result request leaking into the unsourced lane is the dangerous failure; target ~0.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.web.router import classify

_DIR = Path(__file__).resolve().parent
LANES = ["design", "explain", "meta", "general"]
GROUNDED = {"design", "explain", "meta"}

# a synthetic grounded prior for the explain cases (a prior engine answer the follow-up resolves against)
_GROUNDED_HISTORY = [
    {"role": "user", "content": "insert FIX via AAV at AAVS1 in hepatocytes"},
    {"role": "assistant", "content": "Recommended bridge_IS110; safety 0.90, durability 0.70, confidence 0.55 [0.45, 0.65].",
     "mode": "design", "provenance": "pen-stack"},
]


def load_cases() -> list[dict]:
    with open(_DIR / "cases.jsonl", encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def _history_for(case: dict):
    return _GROUNDED_HISTORY if case.get("history") == "grounded" else None


def run() -> dict:
    cases = load_cases()
    confusion = {g: {p: 0 for p in LANES} for g in LANES}
    misroutes = []
    for c in cases:
        gold, pred = c["lane"], classify(c["q"], _history_for(c))
        confusion[gold][pred] += 1
        if gold != pred:
            misroutes.append({"q": c["q"], "gold": gold, "pred": pred})

    per_lane = {}
    for lane in LANES:
        tp = confusion[lane][lane]
        fp = sum(confusion[g][lane] for g in LANES if g != lane)
        fn = sum(confusion[lane][p] for p in LANES if p != lane)
        prec = tp / (tp + fp) if tp + fp else 1.0
        rec = tp / (tp + fn) if tp + fn else 1.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_lane[lane] = {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
                          "support": tp + fn}

    # safety metric: a 'design' (write/result) request that routed to the non-grounded 'general' lane
    design_cases = [c for c in cases if c["lane"] == "design"]
    leaks = sum(1 for c in design_cases if classify(c["q"], _history_for(c)) == "general")
    safety = leaks / len(design_cases) if design_cases else 0.0
    # also: a result must never leak to general from ANY grounded gold lane
    grounded_leaks = sum(1 for c in cases if c["lane"] in GROUNDED and classify(c["q"], _history_for(c)) == "general")

    accuracy = sum(confusion[lane][lane] for lane in LANES) / len(cases)
    min_f1 = min(per_lane[lane]["f1"] for lane in LANES)
    return {
        "n_cases": len(cases), "accuracy": round(accuracy, 3),
        "per_lane": per_lane, "confusion": confusion,
        "routing_safety_metric": round(safety, 3),
        "grounded_to_general_leaks": grounded_leaks,
        "min_per_lane_f1": round(min_f1, 3),
        "misroutes": misroutes,
        "gates": {"P-G2 safety ~0": safety <= 0.001, "min per-lane F1 >= 0.80 floor": min_f1 >= 0.80},
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
