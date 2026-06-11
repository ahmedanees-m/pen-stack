"""Refusal taxonomy + decision policy — the Guardian (v5.7, WS-POLICY).

Turns screen hits into a principled, logged decision: {clear, flag, refuse, escalate}. Conservative by
construction — an ambiguous dual-use signal ESCALATES to human review rather than silently passing or
blanket-refusing. The decision is driven by the highest-severity hit and the version-pinned policy config.

`SafetyVerdict` lives here (not in gate.py) so the lightweight `Verdict` schema can import it without pulling
in the screen/audit machinery.
"""
from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, Field

from pen_stack._resources import resource
from pen_stack.safety.screen import ScreenHit

_POLICY_REL = "configs/safety/policy.yaml"
Decision = Literal["clear", "flag", "refuse", "escalate"]
_RANK = {"high": 3, "medium": 2, "low": 1}


class SafetyVerdict(BaseModel):
    decision: Decision
    hits: list[ScreenHit] = Field(default_factory=list)
    reason: str = ""
    provenance: dict = Field(default_factory=dict)

    @property
    def refused(self) -> bool:
        return self.decision == "refuse"

    def summary(self) -> str:
        n = len(self.hits)
        return f"SAFETY:{self.decision.upper()} ({n} hit{'s' if n != 1 else ''}) — {self.reason}"


def load_policy() -> dict:
    return yaml.safe_load(resource(_POLICY_REL).read_text(encoding="utf-8"))


def _highest_severity(hits: list[ScreenHit]) -> str | None:
    if not hits:
        return None
    return max((h.severity for h in hits), key=lambda s: _RANK.get(s, 0))


def decide(hits: list[ScreenHit], policy: dict | None = None) -> tuple[Decision, str]:
    """(hits) -> (decision, reason). Highest-severity hit governs; ambiguous medium -> escalate."""
    pol = policy or load_policy()
    mapping = pol.get("severity_to_decision", {"high": "refuse", "medium": "escalate", "low": "flag"})
    top = _highest_severity(hits)
    if top is None:
        return "clear", "no hazard signal"
    decision: Decision = mapping.get(top, "escalate")  # type: ignore[assignment]
    reasons = {
        "refuse": "matches a high-severity hazard signature",
        "escalate": "dual-use signal requires human review",
        "flag": "low-severity advisory",
        "clear": "no hazard signal",
    }
    detail = "; ".join(sorted({h.detail for h in hits if h.severity == top}))
    return decision, f"{reasons.get(decision, decision)}: {detail}"
