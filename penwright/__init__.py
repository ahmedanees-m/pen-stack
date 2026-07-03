"""PENWRIGHT — the autonomous genome-writing co-scientist built on PEN-STACK.

This package is the *new system* layered on top of the prior PEN-STACK / bio-firewall
infrastructure. PEN-STACK supplies the grounded tools (Writable Genome, Writer Atlas,
Write Planner, off-target engine, oracle mesh, biosecurity gate); PENWRIGHT supplies the
autonomous loop that orchestrates six specialist agents across multiple rounds of
design -> enforced-safety -> critique -> redesign -> convergence, and emits an auditable,
safety-gated design dossier with a cryptographically signed passport.

Design invariant, inherited from the substrate and never violated here: every quantity in
a dossier traces to a PEN-STACK tool call or an OOD-gated oracle. PENWRIGHT orchestrates,
critiques, and presents; it never sources a number.

Public entry points:
    run_autonomous_loop(goal, ...)  -> a full multi-round run + structured agent trace
    build_dossier(run)              -> the human-facing dossier
    issue_passport(dossier, ...)    -> a signed, tamper-evident design passport
"""
from __future__ import annotations

__version__ = "0.1.0"

from penwright.dossier import build_dossier
from penwright.loop import run_autonomous_loop
from penwright.passport import issue_passport, verify_passport

__all__ = [
    "run_autonomous_loop",
    "build_dossier",
    "issue_passport",
    "verify_passport",
    "__version__",
]
