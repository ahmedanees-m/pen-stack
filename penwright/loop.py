"""The PENWRIGHT autonomous loop (P1: true multi-round self-correction).

A coordinating loop drives the six specialist agents across several rounds:

    (enforced safety gate)  ->  design  ->  off-target  ->  evidence
                            ->  calibration critic  ->  experiment designer

The critic's verdict feeds back into the next round: when a gate fails and a materially
different, verified revision exists, the design agent REDESIGNS and the loop re-runs — so
the system visibly self-improves round over round until it CONVERGES (no gate fails) or
plateaus. The safety adversary runs FIRST and a refusal short-circuits the entire loop
before any downstream reasoning (enforcing, not advisory).

Every quantity in the trace is copied from a PEN-STACK tool result. The loop is fully
deterministic (no LLM required); an optional LLM only narrates. Reported as a structured
agent trace a UI can render live.
"""
from __future__ import annotations

from typing import Any

from penwright import agents


def _score_design(design: dict) -> dict:
    """A grounded quality snapshot of a design, from verify(). The scalar `quality` rises as the design
    improves (illegal->legal, higher calibrated confidence, fewer soft flags) so round-over-round
    self-improvement is measurable. Every component is verifier-sourced; the weighting is presentation only."""
    from pen_stack.verify import verify
    v = verify(dict(design))
    legal = bool(v.legal)
    conf = v.confidence
    n_hard = len(v.violations)
    n_soft = len(v.soft_flags)
    refused = v.safety is not None and v.safety.decision == "refuse"
    # quality: legality dominates, then calibrated confidence (abstain = neutral 0.4), penalise open flaws
    quality = 0.0
    if not refused:
        quality += 2.0 if legal else 0.0
        quality += (conf if conf is not None else 0.4)
        quality -= 0.5 * n_hard
        quality -= 0.25 * n_soft
    return {
        "legal": legal if v.legal is not None else None,
        "confidence": conf,
        "n_hard_flags": n_hard,
        "n_soft_flags": n_soft,
        "safety_decision": (v.safety.decision if v.safety is not None else None),
        "refused": refused,
        "quality": round(quality, 4),
        "epistemic_status": v.epistemic_status,
    }


def run_autonomous_loop(goal: dict, *, seed_candidates: list[dict] | None = None,
                        cell_state: str = "K562", max_rounds: int = 5, min_confidence: float = 0.5,
                        patience: int = 2, actor: str = "penwright") -> dict[str, Any]:
    """Run the full multi-round autonomous loop from a design goal.

    Parameters
    ----------
    goal : dict
        The design intent (gene / cargo_bp / cell_type / edit_intent / writer_family ... plus any hazard
        annotations for the safety screen). Also used verbatim as the object the enforcing gate screens first.
    seed_candidates : list[dict] | None
        Optional explicit starting design(s). Use to drive the redesign story from a known-flawed candidate;
        otherwise the design agent generates the starting candidate from `goal`.
    max_rounds, min_confidence, patience
        Loop bounds and the critic's calibration threshold / plateau tolerance.

    Returns a dict with the ordered `rounds` (each carrying all six agents' events), the `quality_trajectory`,
    whether it `converged`, the `final_design`, and the `no_fabrication` invariant.
    """
    trace: list[dict] = []
    quality_trajectory: list[float] = []

    # ------------------------------------------------------------------ 0. enforced safety gate (first)
    gate = agents.safety_adversary(goal, actor=actor)
    if gate["refused"]:
        # refuse short-circuits the whole loop — nothing downstream runs. This is the hard-gate demonstration.
        return {
            "goal": goal, "converged": False, "refused": True, "n_rounds": 0,
            "final_design": None, "quality_trajectory": [],
            "rounds": [{"round": 0, "phase": "enforced_safety_gate", "agents": [gate],
                        "quality": None, "note": "REFUSED at the gate; no design was produced."}],
            "trace": [gate],
            "safety": gate,
            "no_fabrication": True,
            "note": "The enforcing bio-firewall refused a hazardous request before any downstream reasoning.",
        }

    # ------------------------------------------------------------------ establish the starting design
    if seed_candidates:
        working = dict(seed_candidates[0])
        alternatives = [dict(c) for c in seed_candidates[1:]]
        seed_event = {"agent": "design_agent", "tool": "seed", "action": "accepted seed candidate",
                      "n_survivors": len(seed_candidates), "top": working,
                      "summary": f"started from an explicit seed candidate ({len(seed_candidates)} supplied)"}
    else:
        gen = agents.design_agent(goal, keep=6, actor=actor)
        working = gen.get("top")
        alternatives = [c for c in gen.get("candidates", []) if c is not working][1:] if gen.get("candidates") else []
        seed_event = {**gen, "action": "generated candidate(s) from goal"}
        if working is None:
            return {
                "goal": goal, "converged": False, "refused": False, "n_rounds": 0,
                "final_design": None, "quality_trajectory": [],
                "rounds": [{"round": 0, "phase": "design", "agents": [gate, seed_event], "quality": None,
                            "note": "no surviving candidate (atlas absent for this cell type, or all discarded)."}],
                "trace": [gate, seed_event],
                "no_fabrication": True,
                "note": "The design agent produced no legal+safe candidate; the loop abstained rather than "
                        "fabricate a design.",
            }

    # ------------------------------------------------------------------ the rounds
    converged = False
    rounds: list[dict] = []
    best_quality = float("-inf")
    stale = 0
    redesign_event: dict = seed_event  # replaced by the critic-driven redesign at the end of each round
    for r in range(max_rounds):
        # (a) the design action that produced THIS round's working design
        design_event = seed_event if r == 0 else redesign_event

        # (b) enforced safety re-screen of the working design (defence in depth; visible per round)
        safety_event = agents.safety_adversary(working, actor=actor)
        if safety_event["refused"]:
            rounds.append({"round": r, "phase": "safety_short_circuit",
                           "agents": [design_event, safety_event], "quality": None,
                           "note": "a revision matched a hazard signature; refused and stopped."})
            trace.extend([design_event, safety_event])
            break

        # (c) grounded analysis agents
        offtarget_event = agents.offtarget_agent(working)
        evidence_event = agents.evidence_agent(working)

        # (d) quality snapshot BEFORE any redesign this round
        snap = _score_design(working)
        quality_trajectory.append(snap["quality"])

        # (e) the calibration critic — decides whether to trigger a redesign
        critic_event = agents.calibration_critic(working, min_confidence=min_confidence)

        # (f) experiment designer — the highest-information next experiment
        exp_event = agents.experiment_designer([working, *alternatives], cell_state, k=1)

        round_agents = [design_event, safety_event, offtarget_event, evidence_event, critic_event, exp_event]
        rounds.append({
            "round": r,
            "phase": "converged" if not critic_event["gate_failed"] else "redesign",
            "working_design": {k: v for k, v in working.items() if not str(k).startswith("_")},
            "quality": snap["quality"],
            "quality_detail": snap,
            "agents": round_agents,
            "note": critic_event["summary"],
        })
        trace.extend(round_agents)

        # (g) convergence / plateau logic
        improved = snap["quality"] > best_quality + 1e-9
        best_quality = max(best_quality, snap["quality"])
        stale = 0 if improved else stale + 1

        if not critic_event["gate_failed"]:
            converged = True
            break
        if critic_event["trigger_redesign"] and critic_event.get("revised_design"):
            # the critic's feedback drives the next round's design (self-correction)
            revised = critic_event["revised_design"]
            fix = "; ".join(f.get("rule_id", f.get("kind", "?")) for f in critic_event.get("flags", [])) or "revision"
            redesign_event = {"agent": "design_agent", "tool": "co_scientist.revise",
                              "action": f"redesigned from critic feedback ({fix})", "top": revised,
                              "summary": f"applied a deterministic, re-verified revision addressing: {fix}"}
            working = dict(revised)
            continue
        if stale >= patience:
            rounds[-1]["note"] += " | plateau: no improving revision available, stopping."
            break
        # no fix available and gate still failed -> stop (honest: cannot improve further)
        break

    final_snap = _score_design(working) if working is not None else None
    return {
        "goal": goal,
        "cell_state": cell_state,
        "converged": converged,
        "refused": False,
        "n_rounds": len(rounds),
        "final_design": {k: v for k, v in working.items() if not str(k).startswith("_")} if working else None,
        "final_quality": (final_snap or {}).get("quality"),
        "quality_trajectory": quality_trajectory,
        "improved_over_run": (len(quality_trajectory) >= 2 and quality_trajectory[-1] > quality_trajectory[0]),
        "rounds": rounds,
        "trace": trace,
        "safety": gate,
        "no_fabrication": True,
        "note": ("converged to a legal, safety-cleared design" if converged else
                 "stopped without full convergence (no further grounded improvement available)"),
    }


__all__ = ["run_autonomous_loop"]
