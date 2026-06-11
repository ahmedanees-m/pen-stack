"""pen_stack.safety — the Guardian (v5.7).

A defensive biosecurity / dual-use screening gate that every design submitted to `verify()` passes before it
is evaluated, scored, generated, or exported. It answers a question orthogonal to the immunology subsystem
(v5.1-v5.6): not "will the patient react?" but "is this design itself hazardous / dual-use?". A design that
matches a select-agent, pandemic-pathogen, or controlled-toxin signature is refused or escalated, by
construction; legitimate therapeutic designs pass untouched. It is a safeguard, not a guarantee, and not a
substitute for institutional biosafety review.
"""
from __future__ import annotations

from pen_stack.safety.audit import audit_log, verify_chain
from pen_stack.safety.gate import safety_gate
from pen_stack.safety.policy import SafetyVerdict, decide
from pen_stack.safety.registry import HazardRegistry
from pen_stack.safety.screen import ScreenHit, screen_design

__all__ = [
    "safety_gate", "SafetyVerdict", "screen_design", "ScreenHit", "decide",
    "HazardRegistry", "audit_log", "verify_chain",
]
