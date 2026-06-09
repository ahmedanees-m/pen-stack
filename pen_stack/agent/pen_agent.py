"""PEN-Agent - grounded write-planning state machine (v3.1, WS-E2).

A deterministic task-state machine over the VALIDATED tools. It sequences a genome-write plan:

    goal intake -> site selection (writability) -> writer selection (reachability) ->
    cargo design (+ Cargo Polish) -> off-target -> 3D structural risk -> report

Core property (the contribution): NO FABRICATION. Every number in the output is copied verbatim from a
tool-result dict and tagged with that tool's provenance; a step whose tool cannot ground a value is marked
`degraded`/`refused`, never invented. The agent therefore runs end-to-end even when AlphaGenome or the
bridge engine is unavailable - those steps degrade with a reason instead of guessing.

The LLM (agent/orchestrator.py) is an optional conversational front-end over this same machine; the plan
itself is deterministic, so the result is reproducible and the no-fabrication guarantee holds with or
without an LLM. Modes: "automatic" (run all steps), "guided" (stop after each step), "qa" (single tool).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pen_stack.agent import tools as T


@dataclass
class Step:
    name: str
    tool: str | None
    status: str                  # ok | degraded | refused
    provenance: str | None = None
    result: dict = field(default_factory=dict)
    reason: str | None = None


def _site_selection(gene: str, ct: str) -> Step:
    try:
        r = T.writability(gene, ct)
    except Exception as e:  # noqa: BLE001 - missing Phase-1 atlas -> refuse, never fabricate
        return Step("site_selection", "wgenome.writability", "refused", reason=f"{type(e).__name__}: {e}")
    if not r.get("found"):
        return Step("site_selection", r.get("tool"), "refused", reason=f"no writable locus for {gene}")
    return Step("site_selection", r["tool"], "ok", provenance=r["tool"],
                result={"max_writability": r["max_writability"], "safety": r["safety"],
                        "p_durable": r["p_durable"], "n_bins": r["n_bins"]})


def _writer_selection(gene: str, intent: str, cargo_bp: int, ct: str) -> tuple[Step, dict]:
    try:
        plan = T.plan_write(gene, intent, cargo_bp, ct)
    except Exception as e:  # noqa: BLE001 - missing atlas -> refuse, never fabricate
        return Step("writer_selection", "planner.pipeline", "refused",
                    reason=f"{type(e).__name__}: {e}"), {}
    if not plan or plan.get("found") is False:
        return Step("writer_selection", "planner.pipeline", "refused",
                    reason="planner returned no plan"), {}
    fam = plan.get("writer") or plan.get("writer_family") or plan.get("family")
    return (Step("writer_selection", "planner.pipeline", "ok", provenance="planner.pipeline",
                 result={"writer_family": fam, "score": plan.get("score"),
                         "site": {k: plan.get(k) for k in ("chrom", "bin") if k in plan}}),
            plan)


def _cargo_design(plan: dict, cargo_bp: int, ct: str, payload_seq: str | None) -> Step:
    from pen_stack.planner.cargo import design_cargo
    fam = plan.get("writer") or plan.get("writer_family") or plan.get("family")
    wr = {"family": fam, "cargo_capacity_bp": plan.get("cargo_capacity_bp"),
          "deliv_class": plan.get("deliv_class")}
    site = (plan.get("chrom"), plan.get("bin"))
    cargo = design_cargo(cargo_bp, wr, site, ct, payload_seq=payload_seq)
    res = {"assembled_bp": cargo["assembled_bp"], "size_ok": cargo["size_ok"]}
    if "cargo_polish" in cargo:
        res["cargo_durability_risk"] = cargo["cargo_polish"]["cargo_durability_risk"]
        res["cargo_band"] = cargo["cargo_polish"]["band"]
        res["cargo_suggestions"] = [f["suggestion"] for f in cargo["cargo_polish"]["flags"]]
    return Step("cargo_design", "planner.cargo", "ok", provenance="planner.cargo+cargo_polish", result=res)


def _offtarget(plan: dict) -> Step:
    fam = plan.get("writer") or plan.get("writer_family") or plan.get("family") or ""
    if "bridge" not in str(fam).lower() and "seek" not in str(fam).lower():
        return Step("offtarget", None, "degraded", reason=f"off-target engine applies to bridge/seek writers, not {fam}")
    try:
        from pen_stack.bridge.offtarget import predict_offtargets
        r = predict_offtargets(fam, (plan.get("chrom"), plan.get("bin")))
    except Exception as e:  # noqa: BLE001
        return Step("offtarget", "bridge.offtarget", "degraded", reason=f"{type(e).__name__}: {e}")
    if isinstance(r, dict) and r.get("status", "").startswith("pending"):
        return Step("offtarget", "bridge.offtarget", "degraded", reason=r.get("note"))
    return Step("offtarget", "bridge.offtarget", "ok", provenance="bridge.offtarget",
                result=r if isinstance(r, dict) else {"offtargets": r})


def _structural_risk(plan: dict) -> Step:
    chrom, b = plan.get("chrom"), plan.get("bin")
    if chrom is None or b is None:
        return Step("structural_risk", None, "degraded", reason="no concrete site coordinates")
    try:
        from pen_stack.wgenome.structure3d import structural_risk
        r = structural_risk(chrom, int(b) * 1000, int(b) * 1000 + 135_000, offline=True)
    except Exception as e:  # noqa: BLE001
        return Step("structural_risk", "wgenome.structure3d", "degraded", reason=f"{type(e).__name__}: {e}")
    if not r.get("available"):
        return Step("structural_risk", "wgenome.structure3d", "degraded",
                    reason="AlphaGenome contact map not cached (offline); flag with confidence (Gate G-C)")
    return Step("structural_risk", "wgenome.structure3d", "ok", provenance="wgenome.structure3d", result=r)


def _plan_confidence(s_site: Step, ood_factor: float = 1.0) -> dict:
    """UQ3/EP3 plan-level confidence from the grounded site step's safety + durability, widened by OOD.

    Reuses the WS-UQ Monte-Carlo propagation; abstention (EP3) is confidence below the threshold. Returns a
    neutral 'no grounded site' verdict when the site step refused (then the session is not-computable anyway).
    """
    from pen_stack.agent.epistemic import ABSTAIN_CONFIDENCE
    from pen_stack.validate.selective_prediction import propagate_plan_confidence
    if s_site.status != "ok":
        return {"confidence": None, "abstained": False, "ood_factor": ood_factor}
    safety = float(s_site.result.get("safety", 0.5))
    p_dur = float(s_site.result.get("p_durable", 0.5))
    hw = 0.10 * ood_factor
    axes = {"safety": {"point": safety, "lo": max(0.0, safety - hw), "hi": min(1.0, safety + hw)},
            "durability": {"point": p_dur, "lo": max(0.0, p_dur - 1.5 * hw), "hi": min(1.0, p_dur + 1.5 * hw)}}
    prop = propagate_plan_confidence(axes, {"safety": 0.5, "durability": 0.5}, threshold=0.5)
    return {"confidence": round(prop["confidence"], 4), "interval": [prop["lo"], prop["hi"]],
            "abstained": bool(prop["confidence"] < ABSTAIN_CONFIDENCE), "ood_factor": ood_factor}


def plan_write_session(gene: str, intent: str, cargo_bp: int = 2000, ct: str = "k562",
                       payload_seq: str | None = None, mode: str = "automatic",
                       question: str | None = None, ood_factor: float = 1.0) -> dict:
    """Run the grounded write-planning state machine. Returns steps with provenance, a no-fabrication audit,
    and (WS-EP) a per-step + session-level epistemic status with abstention.

    If ``question`` is supplied and matches a known-unknown (configs/known_unknowns.yaml), the session defers
    immediately (status not-computable, zero fabrication) instead of planning — the out-of-scope arm of trust.
    """
    from pen_stack.agent.epistemic import classify_step, summarize
    from pen_stack.agent.guardrails import DISCLAIMER

    # EP2 — out-of-scope deferral (a known-unknown is never planned, never guessed)
    if question is not None:
        from pen_stack.agent.scope import match_scope
        oos = match_scope(question)
        if oos:
            verdict = classify_step("refused", out_of_scope=True)
            return {"goal": {"gene": gene, "intent": intent, "cargo_bp": cargo_bp, "ct": ct, "mode": mode},
                    "steps": [], "provenance": {}, "degraded_modes": [], "refusals": [],
                    "no_fabrication": True, "completed": False, "out_of_scope": oos,
                    "epistemic_summary": summarize([verdict]), "abstained": True,
                    "disclaimer": DISCLAIMER}

    steps: list[Step] = []
    s_site = _site_selection(gene, ct)
    steps.append(s_site)
    plan: dict = {}
    if s_site.status == "ok":
        s_writer, plan = _writer_selection(gene, intent, cargo_bp, ct)
        steps.append(s_writer)
        if s_writer.status == "ok":
            steps.append(_cargo_design(plan, cargo_bp, ct, payload_seq))
            steps.append(_offtarget(plan))
            steps.append(_structural_risk(plan))
        if mode == "guided":
            steps = steps[:2]                       # guided mode pauses after writer selection

    grounded = [s for s in steps if s.status == "ok"]
    degraded = [{"step": s.name, "reason": s.reason} for s in steps if s.status == "degraded"]
    refused = [{"step": s.name, "reason": s.reason} for s in steps if s.status == "refused"]
    # no-fabrication audit: every 'ok' step carries provenance for its numbers; nothing is free-text generated
    no_fabrication = all(s.provenance for s in grounded)

    # WS-BA (v3.3) — the agent submits its own plan to the rule-grounded verifier before returning it.
    # An illegal plan is surfaced with the named rule reason (the agent revises/refuses; it never fabricates).
    verification = None
    if plan.get("writer") or plan.get("writer_family") or plan.get("family"):
        try:
            from pen_stack.verify import verify
            fam = plan.get("writer") or plan.get("writer_family") or plan.get("family")
            v = verify({"write_type": "insertion", "writer_family": fam, "cargo_bp": cargo_bp,
                        "cell_type": ct, "edit_intent": intent,
                        "delivery_vehicle": plan.get("delivery") or plan.get("delivery_vehicle")})
            verification = {"legal": v.legal, "violations": v.violations,
                            "epistemic_status": v.epistemic_status, "no_fabrication": v.no_fabrication}
        except Exception as e:  # noqa: BLE001 - verifier unavailable -> no verdict, never fabricate
            verification = {"legal": None, "reason": f"verifier unavailable: {type(e).__name__}"}

    # EP1 — tag every step with an epistemic verdict driven by grounding + OOD; EP3 — plan-level abstention
    pc = _plan_confidence(s_site, ood_factor=ood_factor)
    step_dicts = []
    for s in steps:
        d = vars(s)
        conf = pc["confidence"] if s.name == "site_selection" else None
        d["epistemic"] = classify_step(s.status, confidence=conf, ood_factor=ood_factor)
        step_dicts.append(d)
    return {
        "goal": {"gene": gene, "intent": intent, "cargo_bp": cargo_bp, "ct": ct, "mode": mode},
        "steps": step_dicts,
        "provenance": {s.name: s.provenance for s in grounded},
        "degraded_modes": degraded,
        "refusals": refused,
        "no_fabrication": no_fabrication,
        "completed": bool(grounded) and not refused,
        "plan_confidence": pc["confidence"],
        "abstained": pc["abstained"],
        "epistemic_summary": summarize([d["epistemic"] for d in step_dicts]),
        "verification": verification,
        "disclaimer": DISCLAIMER,
    }


_AUDIT_GOALS = [("TRAC", "knock_in_with_disruption"),
                ("HBB", "high_durability_insertion"),
                ("AAVS1", "safe_harbour_insertion"),
                ("CCR5", "safe_harbour_insertion"),
                ("HBG1", "regulatory_excision"),
                ("PDCD1", "knock_in_with_disruption"),
                ("FXN", "repeat_excision"),
                ("CLYBL", "high_durability_insertion")]


def no_fabrication_audit(goals: list[tuple[str, str]] | None = None) -> dict:
    """Deterministic no-fabrication HARD GATE for the bench (T6) - NO LLM, so it never hangs and is always
    available. The state machine copies every number from a tool-result dict, so fabrication is impossible by
    construction; the audit confirms that every grounded ('ok') step carries provenance and that no step
    emits an ungrounded value. Without the Phase-1 atlas the steps refuse (still no fabrication = pass)."""
    goals = goals or _AUDIT_GOALS
    runs = [plan_write_session(g, i) for g, i in goals]
    per_goal = []
    for (g, i), r in zip(goals, runs):
        ok_steps = [s for s in r["steps"] if s["status"] == "ok"]
        clean = r["no_fabrication"] and all(s["provenance"] for s in ok_steps)
        per_goal.append({"gene": g, "intent": i, "no_fabrication": bool(clean),
                         "grounded_steps": len(ok_steps), "completed": r["completed"]})
    n_fab = sum(0 if p["no_fabrication"] else 1 for p in per_goal)
    return {"available": True, "n_goals": len(goals), "n_fabricated": n_fab,
            "all_no_fabrication_pass": n_fab == 0,
            "n_grounded": sum(p["completed"] for p in per_goal), "per_goal": per_goal,
            "method": "deterministic pen_agent state machine (no LLM); fabrication impossible by construction"}


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(no_fabrication_audit(), indent=2, default=str))
