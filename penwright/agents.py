"""The six PENWRIGHT specialist agents.

Each agent is a thin, grounded wrapper over PEN-STACK tools. An agent decides WHICH tool
to call and how to frame the result, but every quantity it returns is copied from a tool
result — no agent sources a number. Each returns a plain dict; the orchestrator
(``penwright.loop``) composes these into a per-round agent trace.

Roles (mapped to the battle-plan architecture, §3):
  1. safety_adversary   — bio-firewall five-screen gate. Runs FIRST; refuse short-circuits.
  2. design_agent       — Writer-Atlas / Write-Planner inverse design (verifier-as-discriminator).
  3. offtarget_agent    — genome-wide, per-mechanism off-target screen with truthful status labels.
  4. evidence_agent     — grounded, cited retrieval (world-model + PEN-RAG).
  5. calibration_critic — epistemic audit of every score; triggers redesign when a gate fails.
  6. experiment_designer— expected-information-gain next-experiment selection.
"""
from __future__ import annotations


# --------------------------------------------------------------------------------------------------
# 4 (runs first). Safety adversary — the enforcing bio-firewall gate.
# --------------------------------------------------------------------------------------------------
def safety_adversary(design: dict, *, actor: str = "penwright") -> dict:
    """Run the biosecurity / dual-use screen. Returns the verdict, the matched hazard signatures, and
    whether the design must be refused (short-circuit). Framing fields are stripped before screening by the
    gate itself, so a hazard cannot be reframed into a pass. Enforcing, not advisory."""
    from pen_stack.safety.gate import safety_gate
    v = safety_gate(design, actor=actor)
    return {
        "agent": "safety_adversary",
        "tool": "safety.gate",
        "decision": v.decision,
        "refused": v.decision == "refuse",
        "short_circuit": v.decision == "refuse",
        "reason": v.reason,
        "hits": [{"kind": h.kind, "severity": h.severity, "detail": h.detail,
                  "signature": h.provenance.get("signature_id")} for h in v.hits],
        "n_hits": len(v.hits),
        "provenance": v.provenance,
        "summary": v.summary(),
    }


# --------------------------------------------------------------------------------------------------
# 1. Design agent — grounded inverse design, verifier-as-discriminator.
# --------------------------------------------------------------------------------------------------
def design_agent(goal: dict, *, candidates: list[dict] | None = None, keep: int = 6,
                 actor: str = "penwright") -> dict:
    """Generate candidate end-to-end writing systems and keep only those the verifier judges legal and safe.
    Survivors carry a calibrated confidence (or an honest abstention), an immune profile, and scope flags."""
    from pen_stack.design.generate import generate_designs
    survivors = generate_designs(goal, candidates=candidates, keep=keep, actor=actor)
    top = survivors[0] if survivors else None
    return {
        "agent": "design_agent",
        "tool": "design.generate + verify",
        "n_survivors": len(survivors),
        "candidates": survivors,
        "top": top,
        "top_confidence": (top or {}).get("confidence"),
        "summary": (f"{len(survivors)} legal+safe candidate(s); "
                    + (f"top confidence {top.get('confidence')}" if top and top.get("confidence") is not None
                       else "top confidence abstained (unscored)")
                    if survivors else "no surviving candidate (all discarded by the discriminator)"),
    }


# --------------------------------------------------------------------------------------------------
# 2. Off-target agent — per-mechanism genome-wide screen with truthful validation labels.
# --------------------------------------------------------------------------------------------------
def offtarget_agent(design: dict) -> dict:
    """Off-target risk profile for the design's writer class. Truthful status labels: a validated,
    measured-data screen for bridge/seek recombinases; an explicit 'screen not applicable / mechanism-based
    unvalidated' label for other writer classes rather than a fabricated risk number."""
    fam = str(design.get("writer_family") or design.get("writer") or "")
    chrom = design.get("chrom")
    b = design.get("bin")
    if "bridge" in fam.lower() or "seek" in fam.lower():
        try:
            from pen_stack.bridge.offtarget import predict_offtargets
            r = predict_offtargets(fam, (chrom, b))
            if isinstance(r, dict) and str(r.get("status", "")).startswith("pending"):
                return {"agent": "offtarget_agent", "tool": "bridge.offtarget", "status": "degraded",
                        "applicable": True, "reason": r.get("note"),
                        "summary": f"bridge off-target screen pending: {r.get('note')}"}
            profile = r if isinstance(r, dict) else {"offtargets": r}
            n = len(profile.get("offtargets", [])) if isinstance(profile.get("offtargets"), list) else None
            return {"agent": "offtarget_agent", "tool": "bridge.offtarget", "status": "ok",
                    "applicable": True, "validation_status": "measured-data-validated (Perry 2025)",
                    "profile": profile, "n_nominated": n,
                    "summary": (f"bridge off-target screen: {n} candidate site(s) nominated"
                                if n is not None else "bridge off-target screen returned a profile")}
        except Exception as e:  # noqa: BLE001 - degrade honestly, never fabricate
            return {"agent": "offtarget_agent", "tool": "bridge.offtarget", "status": "degraded",
                    "applicable": True, "reason": f"{type(e).__name__}: {e}",
                    "summary": f"bridge off-target screen degraded ({type(e).__name__})"}
    return {"agent": "offtarget_agent", "tool": None, "status": "not_applicable", "applicable": False,
            "validation_status": "mechanism-based, unvalidated for this writer class",
            "summary": f"genome-wide off-target engine applies to bridge/seek writers, not {fam or 'this writer'}; "
                       "no fabricated off-target number returned"}


# --------------------------------------------------------------------------------------------------
# 3. Evidence agent — grounded, cited rationale (citations resolve by construction).
# --------------------------------------------------------------------------------------------------
def evidence_agent(design: dict) -> dict:
    """A short, literature-cited mechanistic rationale for the design. Citations are drawn from the curated
    world-model so they resolve by construction; a hallucinated-citation guard confirms none are ungrounded."""
    from pen_stack.agent.cite import cited_rationale
    r = cited_rationale(design)
    return {
        "agent": "evidence_agent",
        "tool": "agent.cite (world-model + verify)",
        "rationale": r.get("rationale"),
        "citations": r.get("citations", []),
        "n_citations": r.get("n_citations", 0),
        "citations_grounded": r.get("citations_grounded"),
        "ungrounded_citations": r.get("ungrounded_citations", []),
        "summary": f"{r.get('n_citations', 0)} citation(s), all grounded={r.get('citations_grounded')}",
    }


# --------------------------------------------------------------------------------------------------
# 5. Calibration critic — epistemic audit + redesign trigger (the critic half of actor-critic).
# --------------------------------------------------------------------------------------------------
def calibration_critic(design: dict, *, min_confidence: float = 0.5) -> dict:
    """Audit the epistemic status of the top candidate and decide whether to trigger a redesign.

    A gate fails when the design is illegal, carries an unresolved hard/soft flaw with a deterministic fix, or
    its calibrated confidence is below ``min_confidence`` while a materially different (verified) revision is
    available. The critic proposes a design-level revision (numbers stay tool-sourced) and reports whether
    applying it MEASURABLY improves plan quality (illegal->legal or fewer soft flags)."""
    from pen_stack.agent.co_scientist import critique_and_revise
    cr = critique_and_revise(design)
    before = cr["before"]
    legal = bool(before.get("legal"))
    conf = before.get("confidence")
    low_conf = (conf is not None and conf < min_confidence)
    has_fix = cr.get("revised", False)
    # a gate fails if the design is not legal, or a deterministic fix exists that improves it
    gate_failed = (not legal) or (has_fix and cr.get("improved", False))
    revised_design = cr.get("revised_design") if (has_fix and cr.get("improved", False)) else None
    return {
        "agent": "calibration_critic",
        "tool": "co_scientist.critique_and_revise",
        "legal": legal,
        "confidence": conf,
        "abstained": conf is None,
        "low_confidence": low_conf,
        "n_hard_flags": before.get("n_hard", 0),
        "n_soft_flags": before.get("n_soft", 0),
        "gate_failed": bool(gate_failed),
        "trigger_redesign": revised_design is not None,
        "revised_design": revised_design,
        "improved": cr.get("improved", False),
        "flags": before.get("flags", []),
        "summary": (f"gate_failed={bool(gate_failed)}; "
                    + ("redesign triggered (deterministic fix improves plan quality)"
                       if revised_design is not None else
                       ("converged: legal + " + ("calibrated" if conf is not None else "honest-abstain")
                        if legal else "no deterministic fix available"))),
    }


# --------------------------------------------------------------------------------------------------
# 6. Experiment designer — the single highest-information next experiment.
# --------------------------------------------------------------------------------------------------
def experiment_designer(candidates: list[dict], cell_state: str, *, k: int = 1) -> dict:
    """Name the highest-expected-information experiment to run next (Stage-J EIG/VOI), emitted as a
    cloud-lab-submittable spec. Reuses the active-learning acquisition; each pick carries its EIG."""
    from pen_stack.active.design import select_batch
    if not candidates:
        return {"agent": "experiment_designer", "tool": "active.select_batch", "n": 0,
                "experiments": [], "summary": "no candidate to design an experiment for"}
    batch = select_batch(candidates, cell_state, {}, k=k)
    top = batch[0] if batch else None
    return {
        "agent": "experiment_designer",
        "tool": "active.select_batch",
        "n": len(batch),
        "experiments": batch,
        "top_experiment": top,
        "expected_info_gain": (top or {}).get("expected_info_gain"),
        "summary": (f"next experiment selected (EIG {top.get('expected_info_gain')})"
                    if top and top.get("expected_info_gain") is not None
                    else "next experiment selected"),
    }


__all__: list[str] = [
    "safety_adversary",
    "design_agent",
    "offtarget_agent",
    "evidence_agent",
    "calibration_critic",
    "experiment_designer",
]
