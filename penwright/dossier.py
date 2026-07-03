"""Assemble the human-facing design dossier from an autonomous-loop run.

The dossier is the deliverable the battle plan describes (§3 Output): chosen system + locus +
rationale + cited evidence + off-target profile + immune axes + biosecurity verdict + a
convergence/validation verdict + the next-best experiment — every field traceable to a tool.
"""
from __future__ import annotations

from typing import Any


def _last_agent(rounds: list[dict], name: str) -> dict | None:
    for rd in reversed(rounds):
        for ev in rd.get("agents", []):
            if ev.get("agent") == name:
                return ev
    return None


def build_dossier(run: dict) -> dict[str, Any]:
    """Fold a ``run_autonomous_loop`` result into a compact dossier. Reads the LAST occurrence of each
    agent (the converged state). A refused run yields a refusal dossier."""
    rounds = run.get("rounds", [])
    safety = run.get("safety", {})
    if run.get("refused"):
        return {
            "goal": run.get("goal"),
            "refused": True,
            "final_design": None,
            "safety": safety,
            "converged": False,
            "no_fabrication": True,
            "verdict": "REFUSED — hazardous request blocked at the enforcing biosecurity gate.",
        }

    critic = _last_agent(rounds, "calibration_critic") or {}
    offtarget = _last_agent(rounds, "offtarget_agent") or {}
    evidence = _last_agent(rounds, "evidence_agent") or {}
    experiment = _last_agent(rounds, "experiment_designer") or {}
    final_design = run.get("final_design") or {}

    return {
        "goal": run.get("goal"),
        "refused": False,
        "converged": run.get("converged"),
        "n_rounds": run.get("n_rounds"),
        "quality_trajectory": run.get("quality_trajectory"),
        "improved_over_run": run.get("improved_over_run"),
        "final_design": final_design,
        "chosen_system": {
            "writer_family": final_design.get("writer_family"),
            "delivery_vehicle": final_design.get("delivery_vehicle"),
            "write_type": final_design.get("write_type"),
            "edit_intent": final_design.get("edit_intent"),
            "cargo_bp": final_design.get("cargo_bp"),
            "cell_type": final_design.get("cell_type") or run.get("cell_state"),
        },
        "confidence": critic.get("confidence"),
        "calibration": {"legal": critic.get("legal"), "abstained": critic.get("abstained"),
                        "n_soft_flags": critic.get("n_soft_flags"), "gate_failed": critic.get("gate_failed")},
        "safety": safety,
        "offtarget": offtarget,
        "evidence": evidence,
        "immune_profile": final_design.get("immune_profile"),
        "next_experiment": experiment.get("top_experiment"),
        "no_fabrication": run.get("no_fabrication", True),
        "verdict": ("CONVERGED — legal, safety-cleared, evidence-cited design"
                    if run.get("converged") else
                    "INCOMPLETE — stopped without full convergence (reported honestly)"),
    }


__all__ = ["build_dossier"]
