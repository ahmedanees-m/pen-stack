"""The Verdict object returned by the verification service (Phase 3.3, WS-V).

Carries legality + the named rejections + a calibrated confidence + an epistemic status + scope flags, with
legality and confidence kept as separate fields (never collapsed). Serializable for REST/MCP.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Verdict(BaseModel):
    legal: bool | None                      # True/False; None when the write type is deferred
    deferred: bool = False
    write_type: str
    routing: dict[str, Any] = Field(default_factory=dict)
    rule_results: list[dict] = Field(default_factory=list)
    violations: list[dict] = Field(default_factory=list)      # named hard-rule rejections + citation
    soft_flags: list[dict] = Field(default_factory=list)      # soft penalties raised
    scope_flags: list[dict] = Field(default_factory=list)     # known-unknowns + rule scope flags
    confidence: float | None = None         # calibrated confidence on the SOFT components (distinct axis)
    interval: list[float] | None = None
    epistemic_status: str = "not-computable"
    provenance: dict[str, Any] = Field(default_factory=dict)
    no_fabrication: bool = True
    writer_critique: dict[str, Any] | None = None   # v4.0 WS-WV: critique of a generated candidate writer
                                                     # (pass/flag + reasons); NEVER a claim that it works
    delivery_profile: dict[str, Any] | None = None  # v5.1 WS-IMMUNE: documented ordinal immune/safety/efficacy
                                                     # priors for the chosen vehicle (NEVER a predicted magnitude)

    def summary(self) -> str:
        if self.deferred:
            return f"DEFERRED ({self.write_type}): {self.routing.get('reason', 'unsupported write type')}"
        verdict = "LEGAL" if self.legal else "ILLEGAL"
        conf = f"conf={self.confidence}" if self.confidence is not None else "conf=n/a (abstained)"
        why = "" if self.legal else " | " + "; ".join(v["rule_id"] for v in self.violations)
        return f"{verdict} [{self.epistemic_status}, {conf}]{why}"
