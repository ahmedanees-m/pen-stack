"""The safety gate — screen -> decide -> audit, the Guardian's single entry point (v5.7, WS-POLICY).

`safety_gate(design)` returns a `SafetyVerdict` (clear / flag / refuse / escalate) and writes a hash-chained
audit record. It screens the DESIGN ARTIFACT only — framing/justification fields are stripped first, so
re-framing a hazardous design as "defensive research" cannot flip a refuse to a clear (the artifact decides,
not the prompt). No number is fabricated: every hit is sourced from the version-pinned registry.
"""
from __future__ import annotations

from pen_stack.safety.audit import audit_log, digest_design
from pen_stack.safety.policy import SafetyVerdict, decide, load_policy
from pen_stack.safety.screen import screen_design


def _strip_framing(design: dict, policy: dict) -> dict:
    """Remove free-text framing fields the screen must ignore (the artifact decides, not the wording)."""
    drop = set(policy.get("ignore_framing_fields", []))
    return {k: v for k, v in design.items() if k not in drop}


def safety_gate(design: dict, *, actor: str = "anonymous", registry=None) -> SafetyVerdict:
    """Screen a design, decide, and log a tamper-evident audit record. The design digest is taken over the
    ORIGINAL design (full accountability), while screening runs on the framing-stripped artifact."""
    if not isinstance(design, dict):
        design = dict(design)
    policy = load_policy()
    artifact = _strip_framing(design, policy)
    hits = screen_design(artifact, registry=registry)
    decision, reason = decide(hits, policy)
    verdict = SafetyVerdict(
        decision=decision, hits=hits, reason=reason,
        provenance={"registry_version": next((h.provenance.get("registry_version") for h in hits), None),
                    "policy_version": policy.get("policy_version"), "actor": actor,
                    "screened_kinds": sorted({h.kind for h in hits}),
                    "note": "screening reduces, not eliminates, dual-use risk; not a substitute for IBC review"})
    audit_log(actor=actor, design_digest=digest_design(design), verdict=verdict)
    return verdict
