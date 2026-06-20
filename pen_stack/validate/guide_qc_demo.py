"""WS-G2 acceptance - SYNTHETIC failure-mode unit test for the guide-QC ranking logic (deterministic, CI-safe).

IMPORTANT: the guides in this panel are HAND-CONSTRUCTED, not real bridge-RNA guides with measured
outcomes. Each "bad" guide is synthesised to exercise ONE documented failure MECHANISM by construction:
  * self_complementary - a deliberate palindrome (GC-repeat)
  * cross_loop - donor set to revcomp(target) so the two loops are complementary
  * many_offtargets - an otherwise-clean guide stamped with offtarget_count = 6
So this is a POSITIVE-CONTROL UNIT TEST: it checks that the QC scorer penalises each known failure mode and
ranks the constructed-bad guides below a clean control. It is NOT retrospective validation against real guide
outcomes, and makes NO claim of generating superior novel guides. The failure mechanisms (self-complementarity,
TBL-DBL cross-loop, off-targets) are real and documented; the specific sequences here are illustrative.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.bridge.fold_qc import _complementarity # noqa: F401 (kept for transparency of the metric)
from pen_stack.bridge.guide_qc import rank_variants

_OUT = Path(__file__).resolve().parents[2] / "out" / "guide_qc_demo.json"

_GOOD_T = "ACAAGCTGGAAGAACTGAAG"
_GOOD_D = "GACATCTACAAGGACATCGA"
_PAIR = {"A": "T", "T": "A", "G": "C", "C": "G"}


def _revcomp(s: str) -> str:
    return "".join(_PAIR[b] for b in reversed(s))


# SYNTHETIC panel (all sequences hand-constructed): one clean control + three guides each built to trip ONE
# failure mode. These are illustrative constructions, NOT real guides with measured outcomes.
PANEL = [
    {"name": "clean", "target_guide": _GOOD_T, "donor_guide": _GOOD_D, "klass": "good",
     "synthetic": True},
    {"name": "self_complementary", "target_guide": "GCGCGCGCGCGCGCGCGCGC",
     "donor_guide": _GOOD_D, "klass": "bad", "synthetic": True}, # constructed palindromic loop
    {"name": "cross_loop", "target_guide": _GOOD_T, "donor_guide": _revcomp(_GOOD_T),
     "klass": "bad", "synthetic": True}, # donor = revcomp(target) by code
    {"name": "many_offtargets", "target_guide": _GOOD_T, "donor_guide": _GOOD_D,
     "offtarget_count": 6, "klass": "bad", "synthetic": True}, # clean guide, off-target stamped
]


def run(out: str | Path = _OUT) -> dict:
    ranked = rank_variants(PANEL)
    order = [r["name"] for r in ranked]
    by_class = {p["name"]: p["klass"] for p in PANEL}
    good_scores = [r["qc_score"] for r in ranked if by_class[r["name"]] == "good"]
    bad_scores = [r["qc_score"] for r in ranked if by_class[r["name"]] == "bad"]
    report = {
        "data_type": "SYNTHETIC (hand-constructed guides; not real measured guide outcomes)",
        "ranking": [{"name": r["name"], "qc_score": r["qc_score"], "flags": r["flags"],
                     "klass": by_class[r["name"]], "synthetic": True} for r in ranked],
        "best_is_good": by_class[order[0]] == "good",
        "all_bad_below_good": bool(min(good_scores) > max(bad_scores)),
        "every_bad_flagged": all(r["flags"] for r in ranked if by_class[r["name"]] == "bad"),
        "scope": "SYNTHETIC positive-control unit test of the ranking logic: constructed guides, each tripping "
                 "one documented failure mode, must rank below a clean control and be flagged. NOT retrospective "
                 "validation against real guide outcomes; no claim of generating superior novel guides.",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
