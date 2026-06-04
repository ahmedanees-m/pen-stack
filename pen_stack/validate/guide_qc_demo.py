"""WS-G2 acceptance - retrospective guide-QC down-ranking on a curated set (deterministic, CI-safe).

The bar is RETROSPECTIVE: known-bad bridge-RNA guides (self-complementary loops, cross-loop complementarity,
many off-targets) must rank BELOW a clean guide. No claim of generating superior novel guides - this is a
ranking/QC layer over the validated fold-QC + off-target primitives.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.bridge.fold_qc import _complementarity  # noqa: F401  (kept for transparency of the metric)
from pen_stack.bridge.guide_qc import rank_variants

_OUT = Path(__file__).resolve().parents[2] / "out" / "guide_qc_demo.json"

_GOOD_T = "ACAAGCTGGAAGAACTGAAG"
_GOOD_D = "GACATCTACAAGGACATCGA"
_PAIR = {"A": "T", "T": "A", "G": "C", "C": "G"}


def _revcomp(s: str) -> str:
    return "".join(_PAIR[b] for b in reversed(s))


# curated variants: one clean guide + three known-bad failure modes.
PANEL = [
    {"name": "clean", "target_guide": _GOOD_T, "donor_guide": _GOOD_D, "klass": "good"},
    {"name": "self_complementary", "target_guide": "GCGCGCGCGCGCGCGCGCGC",
     "donor_guide": _GOOD_D, "klass": "bad"},                                  # palindromic loop
    {"name": "cross_loop", "target_guide": _GOOD_T, "donor_guide": _revcomp(_GOOD_T),
     "klass": "bad"},                                                          # donor = revcomp(target)
    {"name": "many_offtargets", "target_guide": _GOOD_T, "donor_guide": _GOOD_D,
     "offtarget_count": 6, "klass": "bad"},                                    # otherwise clean but off-target
]


def run(out: str | Path = _OUT) -> dict:
    ranked = rank_variants(PANEL)
    order = [r["name"] for r in ranked]
    by_class = {p["name"]: p["klass"] for p in PANEL}
    good_scores = [r["qc_score"] for r in ranked if by_class[r["name"]] == "good"]
    bad_scores = [r["qc_score"] for r in ranked if by_class[r["name"]] == "bad"]
    report = {
        "ranking": [{"name": r["name"], "qc_score": r["qc_score"], "flags": r["flags"],
                     "klass": by_class[r["name"]]} for r in ranked],
        "best_is_good": by_class[order[0]] == "good",
        "all_bad_below_good": bool(min(good_scores) > max(bad_scores)),
        "every_bad_flagged": all(r["flags"] for r in ranked if by_class[r["name"]] == "bad"),
        "scope": "retrospective down-ranking of known-bad guides; ranking, not validated novel design.",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
