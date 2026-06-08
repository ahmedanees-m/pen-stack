"""Epistemic scoping — first-class "I don't know" (Phase 3.2, WS-EP / EP1).

A thin, high-trust layer over the WS-UQ signals (conformal confidence + OOD) and the existing grounding
machinery (provenance, refusals, scope matcher). It assigns every agent output **exactly one** of three
epistemic statuses, *driven by the signals, never hand-set*:

  * **grounded-confident**     — tool-grounded, in-distribution (low OOD), tight/calibrated, above the
                                  abstention threshold.
  * **grounded-extrapolating** — tool-grounded but the OOD detector flags the query as far from training
                                  data, or the conformal interval is wide / confidence low. The number is
                                  real but the model is extrapolating — trust it less.
  * **not-computable**         — no tool can ground it: the step refused, the query is out of scope (a
                                  known-unknown), or the agent abstained. The honest "I don't know."

This makes trustworthiness *legible*: a reader sees not just the number but how much the system stands
behind it. The status is a pure function of the inputs, so it is deterministic and testable.
"""
from __future__ import annotations

from dataclasses import dataclass

GROUNDED_CONFIDENT = "grounded-confident"
GROUNDED_EXTRAPOLATING = "grounded-extrapolating"
NOT_COMPUTABLE = "not-computable"

# OOD widen-factor at/above which a grounded answer is treated as extrapolating (matches the OODDetector
# widen_factor scale: 1.0 = in-distribution, rising to the cap). 1.5 = "halfway to the cap" — the same
# threshold the planner's attach_uncertainty uses, so the two layers agree.
OOD_EXTRAPOLATE_FACTOR = 1.5
# plan/answer confidence below this abstains (matches planner attach_uncertainty abstain_below default).
ABSTAIN_CONFIDENCE = 0.5


@dataclass
class EpistemicVerdict:
    status: str
    confidence: float | None
    reason: str
    grounded: bool
    ood_factor: float | None = None
    out_of_scope: bool = False

    def to_dict(self) -> dict:
        return {"epistemic_status": self.status, "confidence": self.confidence, "reason": self.reason,
                "grounded": self.grounded, "ood_factor": self.ood_factor,
                "out_of_scope": self.out_of_scope}


def classify(grounded: bool, confidence: float | None = None, ood_factor: float | None = None,
             abstained: bool = False, out_of_scope: bool = False,
             refused: bool = False) -> EpistemicVerdict:
    """Assign exactly one epistemic status from the (UQ/OOD/grounding/scope) signals.

    Precedence (most-honest-wins): out-of-scope / refused / abstained → not-computable; else if grounded but
    OOD-flagged or low-confidence → grounded-extrapolating; else grounded-confident. An ungrounded answer
    that is none of the above is still not-computable (we never label an ungrounded number 'confident').
    """
    if out_of_scope:
        return EpistemicVerdict(NOT_COMPUTABLE, None,
                                "out of scope — a known-unknown PEN-STACK does not model", grounded=False,
                                ood_factor=ood_factor, out_of_scope=True)
    if refused or not grounded:
        return EpistemicVerdict(NOT_COMPUTABLE, None,
                                "no validated tool can ground this value", grounded=False,
                                ood_factor=ood_factor)
    if abstained or (confidence is not None and confidence < ABSTAIN_CONFIDENCE):
        return EpistemicVerdict(NOT_COMPUTABLE, confidence,
                                f"abstained — confidence {confidence} below {ABSTAIN_CONFIDENCE}",
                                grounded=True, ood_factor=ood_factor)
    if ood_factor is not None and ood_factor >= OOD_EXTRAPOLATE_FACTOR:
        return EpistemicVerdict(GROUNDED_EXTRAPOLATING, confidence,
                                f"grounded but extrapolating — OOD factor {round(ood_factor, 3)} ≥ "
                                f"{OOD_EXTRAPOLATE_FACTOR} (query far from training data)",
                                grounded=True, ood_factor=ood_factor)
    return EpistemicVerdict(GROUNDED_CONFIDENT, confidence,
                            "grounded, in-distribution, calibrated", grounded=True, ood_factor=ood_factor)


def classify_step(step_status: str, confidence: float | None = None, ood_factor: float | None = None,
                  out_of_scope: bool = False) -> dict:
    """Map a PEN-Agent step (`ok` | `degraded` | `refused`) + UQ/OOD signals → an epistemic verdict dict.

    `ok` steps are grounded; `degraded`/`refused` steps are not-computable. This is the bridge the agent
    uses to tag every step (see agent.pen_agent)."""
    grounded = step_status == "ok"
    refused = step_status in ("refused", "degraded")
    return classify(grounded=grounded, confidence=confidence, ood_factor=ood_factor,
                    out_of_scope=out_of_scope, refused=refused).to_dict()


def summarize(verdicts: list[dict]) -> dict:
    """Roll up per-output verdicts into a session-level epistemic summary (counts per status)."""
    counts = {GROUNDED_CONFIDENT: 0, GROUNDED_EXTRAPOLATING: 0, NOT_COMPUTABLE: 0}
    for v in verdicts:
        counts[v.get("epistemic_status", NOT_COMPUTABLE)] = counts.get(
            v.get("epistemic_status", NOT_COMPUTABLE), 0) + 1
    n = len(verdicts) or 1
    return {"counts": counts, "n": len(verdicts),
            "fraction_grounded_confident": round(counts[GROUNDED_CONFIDENT] / n, 4),
            "all_tagged": all("epistemic_status" in v for v in verdicts)}
