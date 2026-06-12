"""Capability + scope manifests — the self-describing AI contract (v6.1, WS-MANIFEST).

The differentiator: PEN-STACK describes not only WHAT it can do (capability manifest) but — uniquely —
machine-readably WHAT IT REFUSES TO ANSWER (scope manifest: the known-unknowns registry + the oracle scope
cards). An external agent fetches both and ROUTES on them, instead of reading prose. Both are generated from the
live registry / scope cards (never hand-written), versioned under the 1.0 stability commitment.
"""
from __future__ import annotations

from typing import Any

import pen_stack

# the stable public tools (the 1.0 surface). Each is a thin contract over a validated entry point; none fabricate.
_TOOLS = [
    {"name": "verify_write", "summary": "legality + safety + calibrated confidence + immune profile for a design",
     "input": "Design", "output": "Verdict", "entrypoint": "pen_stack.verify.verify", "fabricates": False},
    {"name": "safety_screen", "summary": "biosecurity / dual-use gate (clear/flag/escalate/refuse)",
     "input": "Design", "output": "SafetyVerdict", "entrypoint": "pen_stack.safety.safety_gate",
     "fabricates": False},
    {"name": "generate_designs", "summary": "grounded candidate writing systems (verifier-as-discriminator)",
     "input": "Goal | candidates", "output": "list[Design(candidate)]",
     "entrypoint": "pen_stack.design.generate_designs", "fabricates": False},
    {"name": "pareto_front", "summary": "non-dominated tradeoff frontier (incl. grounded immune-risk axis)",
     "input": "list[Design]", "output": "list[Design(candidate)]",
     "entrypoint": "pen_stack.design.pareto_front", "fabricates": False},
    {"name": "predict_outcome", "summary": "calibrated, OOD-gated, phenotype-bounded write outcome",
     "input": "Design + cell_state", "output": "Outcome(candidate)",
     "entrypoint": "pen_stack.twin.predict_outcome", "fabricates": False},
    {"name": "immune_profile", "summary": "per-axis immune-risk screen (never collapsed into one number)",
     "input": "Design", "output": "ImmuneProfile", "entrypoint": "pen_stack.planner.immune_profile.immune_profile",
     "fabricates": False},
    {"name": "suggest_experiment", "summary": "active-learning next-experiment batch (EIG + immune-VOI)",
     "input": "Designs + cell_state", "output": "ExperimentBatch",
     "entrypoint": "pen_stack.active.select_batch", "fabricates": False},
    {"name": "co_scientist_session", "summary": "drive the full loop: strategies + outcomes + experiments + safety",
     "input": "Goal + cell_state", "output": "Session", "entrypoint": "pen_stack.agent.co_scientist.co_scientist_session",
     "fabricates": False},
    {"name": "run_loop", "summary": "one gated DBTL loop (autonomy Level 3, human in control)",
     "input": "Goal + cell_state", "output": "LoopHistory", "entrypoint": "pen_stack.loop.run_loop",
     "fabricates": False},
    {"name": "challenge_evaluate", "summary": "score a submission on a held-out Genome-Writing Challenge round",
     "input": "Submission + round_id", "output": "ChallengeResult",
     "entrypoint": "benchmarks.genome_writing_challenge.harness.evaluate", "fabricates": False},
]

_POLICY = ("outputs outside scope are returned as `out_of_scope` (known-unknown) or `extrapolating` (OOD) and are "
           "NEVER asserted; every number is tool-sourced (no fabrication); contracts are versioned + "
           "deprecation-policed under the 1.0 stability commitment (docs/STABILITY.md).")


def capability_manifest() -> dict[str, Any]:
    """Machine-readable: WHAT PEN-STACK can do. An agent routes on this, not on prose."""
    return {
        "name": "pen-stack", "version": pen_stack.__version__, "stability": "stable",
        "contract_version": "6.1.0",
        "guarantees": ["rule-grounded legality", "calibrated confidence", "explicit scope / known-unknowns",
                       "biosecurity safety gate", "no fabrication"],
        "tools": _TOOLS,
        "oracles": _oracle_summary(),
        "surfaces": {"rest": "/capabilities, /scope, /oracles, /verify, /generate, /predict, /immune, /safety, "
                             "/suggest, /session, /openapi.json", "mcp": "pen_stack.agent.mcp_server",
                     "challenge": "benchmarks/genome_writing_challenge"},
    }


def _oracle_summary() -> dict:
    """Live-oracle roll-up (v6.4): which foundation models execute live, their latency class, what is held/deferred."""
    from pen_stack.oracles.status import summary
    return summary()


def _known_unknowns() -> list[dict]:
    """The known-unknowns as PUBLIC data (id/title/requires/why) — internal matcher fields are not exposed."""
    from pen_stack.agent.scope import load_registry
    return [{"id": e["id"], "title": e["title"], "requires": e.get("requires"),
             "why": " ".join((e.get("why") or "").split())} for e in load_registry()]


def _oracle_scope_cards() -> list[dict]:
    """Each wrapped model's in-distribution envelope (what it is valid for, and what it is NOT)."""
    from pen_stack.oracles.cache import load_scope_cards
    out = []
    for model, c in load_scope_cards().items():
        out.append({"model": model, "family": c.get("family"), "version": c.get("version"),
                    "output_kind": c.get("output_kind"),
                    "valid_for": " ".join((c.get("valid_for") or "").split()),
                    "not_valid_for": " ".join((c.get("not_valid_for") or "").split()),
                    "generalizes_to_unseen_loci": c.get("generalizes_to_unseen_loci")})
    return out


def scope_manifest() -> dict[str, Any]:
    """Machine-readable: WHAT PEN-STACK REFUSES TO ANSWER. The contract that makes depending on it safe."""
    return {
        "name": "pen-stack", "version": pen_stack.__version__, "contract_version": "6.1.0",
        "known_unknowns": _known_unknowns(),
        "oracle_scope_cards": _oracle_scope_cards(),
        "policy": _POLICY,
    }
