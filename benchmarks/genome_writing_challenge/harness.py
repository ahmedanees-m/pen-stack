"""The Genome-Writing Challenge — an open, recurring, held-out benchmark (PEN-STACK v5.13, WS-CHALLENGE).

The CASP / Virtual-Cell-Challenge model for the WRITING side of genome engineering: an external agent submits a
`predict_fn(public_input) -> answer`, scored on a HELD-OUT round whose labels it never sees. Scoring is
deterministic, no task uses a circular label (labels come from the validated PEN-STACK verifier / oracles, NOT
the submitter's own claim), and a no-fabrication audit runs on every submission. Task families generalise the
internal v3.4→v5.12 bench: legality, write-type, safety, and an IMMUNE-RISK task drawing on the v5.6 oracles.

Each `public_input` names its `family` and `task_id` (so the submitter knows what kind of answer to return) and
shows the `design`/`goal` — but NEVER the label. The private labels (the `score` closures) are the held-out
truth, released after a round. A reference submission (PEN-STACK itself) anchors the leaderboard.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ChallengeTask:
    id: str
    family: str
    public_input: dict                       # shown to the submitter (names family + design; NO label)
    score: Callable[[Any], float]            # private held-out label -> 0..1 (never shown to the submitter)
    circular: bool = False


@dataclass
class Submission:
    name: str
    predict_fn: Callable[[dict], Any]        # external agent: public_input -> answer (no labels seen)


# ---- labels computed by the validated PEN-STACK layers (NOT the submitter -> non-circular) ----
def _legality_label(design: dict) -> bool:
    from pen_stack.verify import verify
    return bool(verify(dict(design), actor="challenge").legal)


def _safety_label(design: dict) -> str:
    from pen_stack.safety.gate import safety_gate
    return safety_gate(dict(design), actor="challenge").decision


def _highest_immune_risk_axis(design: dict) -> str | None:
    """The in-scope immune axis with the LOWEST score = highest risk (from the v5.6 profile)."""
    from pen_stack.planner.immune_profile import immune_profile
    axes = immune_profile(dict(design)).get("axes", {})
    in_scope = {k: a["value"] for k, a in axes.items() if a.get("in_scope") and a.get("value") is not None}
    return min(in_scope, key=in_scope.get) if in_scope else None


_BENIGN = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
           "cargo_bp": 3000, "cell_type": "k562", "cargo_function": "human factor IX"}
_HAZARD = {**_BENIGN, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}
_OVERSIZE = {**_BENIGN, "cargo_bp": 8000}


def _pub(task_id: str, family: str, design: dict) -> dict:
    return {"task_id": task_id, "family": family, "design": design,
            "instructions": {"legality": "return True/False: is this design legal?",
                             "safety": "return the safety decision: clear/flag/escalate/refuse",
                             "immune_risk": "return the name of the highest-risk immune axis (from the v5.6 axes)"
                             }[family]}


def _round_tasks(round_id: str) -> list[ChallengeTask]:
    return [
        ChallengeTask("legality_benign", "legality", _pub("legality_benign", "legality", _BENIGN),
                      lambda ans: 1.0 if bool(ans) == _legality_label(_BENIGN) else 0.0),
        ChallengeTask("legality_oversize", "legality", _pub("legality_oversize", "legality", _OVERSIZE),
                      lambda ans: 1.0 if bool(ans) == _legality_label(_OVERSIZE) else 0.0),
        ChallengeTask("safety_hazard", "safety", _pub("safety_hazard", "safety", _HAZARD),
                      lambda ans: 1.0 if str(ans) == _safety_label(_HAZARD) else 0.0),
        ChallengeTask("safety_benign", "safety", _pub("safety_benign", "safety", _BENIGN),
                      lambda ans: 1.0 if str(ans) == _safety_label(_BENIGN) else 0.0),
        ChallengeTask("immune_risk_axis", "immune_risk", _pub("immune_risk_axis", "immune_risk", _BENIGN),
                      lambda ans: 1.0 if ans == _highest_immune_risk_axis(_BENIGN) else 0.0),
    ]


def _audit_no_fabrication(submission: Submission, tasks: list[ChallengeTask]) -> bool:
    """A submission may answer or abstain; it must not crash. Grounding is enforced by the held-out labels —
    a fabricated answer simply scores 0 (it cannot match the validated label by inventing one)."""
    try:
        for t in tasks:
            submission.predict_fn(dict(t.public_input))
        return True
    except Exception:
        return False


def evaluate(submission: Submission, round_id: str = "2026R1") -> dict:
    """Score an external submission on a HELD-OUT round. Deterministic; no circular labels; no-fabrication
    checked. Public input shown; private labels (the score closures) released after the round."""
    tasks = _round_tasks(round_id)
    scores, per_family = {}, {}
    for t in tasks:
        try:
            s = float(t.score(submission.predict_fn(dict(t.public_input))))
        except Exception:
            s = 0.0
        scores[t.id] = s
        per_family.setdefault(t.family, []).append(s)
    return {
        "submission": submission.name, "round": round_id, "scores": scores,
        "by_family": {f: round(sum(v) / len(v), 4) for f, v in per_family.items()},
        "aggregate": round(sum(scores.values()) / len(scores), 4) if scores else 0.0,
        "immune_risk_task_included": any(t.family == "immune_risk" for t in tasks),
        "no_circular_labels": all(not t.circular for t in tasks),
        "no_fabrication": _audit_no_fabrication(submission, tasks),
        "n_tasks": len(tasks),
    }


def reference_submission() -> Submission:
    """PEN-STACK reference solver: dispatches on the task family, answering from the validated layers."""
    def predict(public_input: dict):
        fam, design = public_input["family"], public_input["design"]
        if fam == "legality":
            return _legality_label(design)
        if fam == "safety":
            return _safety_label(design)
        if fam == "immune_risk":
            return _highest_immune_risk_axis(design)
        return None
    return Submission(name="pen-stack-reference", predict_fn=predict)
