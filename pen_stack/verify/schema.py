"""The Verdict object returned by the verification service.

Carries legality + the named rejections + a calibrated confidence + an epistemic status + scope flags, with
legality and confidence kept as separate fields (never collapsed). Serializable for REST/MCP.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from pen_stack.safety.policy import SafetyVerdict


class Verdict(BaseModel):
    """Frozen: the verification result is immutable once returned, so legality, the named violations, the
    calibrated confidence, and the nested (also-frozen) safety verdict cannot be rewritten after the fact.
    Build a changed verdict with `model_copy(update=...)` if a transform genuinely needs one."""
    model_config = ConfigDict(frozen=True)

    legal: bool | None # True/False; None when the write type is deferred
    deferred: bool = False
    write_type: str
    routing: dict[str, Any] = Field(default_factory=dict)
    rule_results: list[dict] = Field(default_factory=list)
    violations: list[dict] = Field(default_factory=list) # named hard-rule rejections + citation
    soft_flags: list[dict] = Field(default_factory=list) # soft penalties raised
    scope_flags: list[dict] = Field(default_factory=list) # known-unknowns + rule scope flags
    confidence: float | None = None # calibrated confidence on the SOFT components (distinct axis)
    interval: list[float] | None = None
    epistemic_status: str = "not-computable"
    provenance: dict[str, Any] = Field(default_factory=dict)
    no_fabrication: bool = True
    writer_critique: dict[str, Any] | None = None # critique of a generated candidate writer
                                                     # (pass/flag + reasons); NEVER a claim that it works
    delivery_profile: dict[str, Any] | None = None # documented ordinal immune/safety/efficacy
                                                     # priors for the chosen vehicle (NEVER a predicted magnitude)
    immune_profile: dict[str, Any] | None = None # per-axis immune-risk vector (genotox/CD8/
                                                     # innate/NAb/anti-PEG), each w/ own uncertainty + validation
                                                     # label; collapsed_score is None (never fused); magnitude KU
    safety: SafetyVerdict | None = None # the Guardian: biosecurity/dual-use screen
                                                     # (clear/flag/refuse/escalate); a refused design is NOT
                                                     # evaluated further; orthogonal to immune_profile

    def summary(self) -> str:
        if self.safety is not None and self.safety.decision == "refuse":
            return f"REFUSED (safety): {self.safety.reason}"
        if self.deferred:
            return f"DEFERRED ({self.write_type}): {self.routing.get('reason', 'unsupported write type')}"
        verdict = "LEGAL" if self.legal else "ILLEGAL"
        conf = f"conf={self.confidence}" if self.confidence is not None else "conf=n/a (abstained)"
        why = "" if self.legal else " | " + "; ".join(v["rule_id"] for v in self.violations)
        return f"{verdict} [{self.epistemic_status}, {conf}]{why}"
