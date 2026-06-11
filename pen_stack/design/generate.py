"""Generative inverse design — verifier-as-discriminator (v5.8, WS-GEN).

Generation PROPOSES candidate end-to-end writing systems; the v3.3 `verify()` — now safety-gated (v5.7),
legality-checked (v3.3), calibrated (v3.2), and immune-profiled (v5.6) — DISPOSES. A candidate that is hazardous
(safety refuse/escalate) or illegal is DISCARDED, never returned as a claim: the `as_claim()` guard generalised
to whole designs. Survivors are explicitly `output_kind="candidate"` — calibrated and immune-profiled, but never
asserted to work.
"""
from __future__ import annotations

from typing import Any

from pen_stack.design.space import candidate_space
from pen_stack.verify import verify

# a survivor must be legal AND safe (cleared or low-severity advisory); refuse/escalate are discarded.
_SAFE_DECISIONS = {"clear", "flag"}


def _confidence_key(d: dict) -> tuple:
    c = d.get("confidence")
    return (c is not None, c if c is not None else -1.0)


def generate_designs(goal: dict | None = None, *, candidates: list[dict] | None = None,
                     n: int = 200, keep: int = 25, actor: str = "generator") -> list[dict[str, Any]]:
    """Generate -> discriminate with `verify()`. Returns the surviving candidates, each carrying a calibrated
    confidence (or explicit abstention), the v5.6 immune profile, the safety decision, and scope flags, sorted
    by confidence. Hazardous (refuse/escalate) or illegal proposals are discarded, never returned.

    Pass an explicit ``candidates`` list to discriminate a known pool (atlas-independent); otherwise candidates
    are enumerated from ``goal`` via the planner-backed candidate space."""
    pool = candidates if candidates is not None else candidate_space(goal or {}, n=n)
    survivors: list[dict] = []
    for d in pool:
        v = verify(dict(d), actor=actor)
        decision = v.safety.decision if v.safety is not None else "clear"
        if v.legal is not True or decision not in _SAFE_DECISIONS:
            continue                                              # discarded by the discriminator
        survivors.append({
            **d,
            "confidence": v.confidence, "interval": v.interval,
            "immune_profile": v.immune_profile,                   # v5.6 grounded per-axis vector
            "safety_decision": decision, "legal": v.legal,
            "scope_flags": v.scope_flags, "output_kind": "candidate",
        })
    survivors.sort(key=_confidence_key, reverse=True)
    return survivors[:keep]
