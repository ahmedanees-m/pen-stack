"""The verification service — `verify(design) -> Verdict` (Phase 3.3, WS-V).

The first-class "for the AI" surface: submit a proposed genomic write, get back a structured verdict —
legality (from the WS-R rule solver), the named reason + citation for any rejection, a calibrated confidence
on the *soft* components (from the v3.2 L4 trust layer), an epistemic status, and any out-of-scope flags.
Thin orchestration over existing layers; it generates **no new numbers** (no-fabrication holds: legality is
rule-deterministic, confidence comes from the calibrated tool, scope from the registry).

Legality and confidence are DISTINCT axes (v3.3 Principle 2) and are never collapsed: a design can be
legal-but-low-confidence or illegal-with-certainty. The Verdict carries both, separately.
"""
from __future__ import annotations

from typing import Any

from pen_stack.rules import Design
from pen_stack.rules.loader import RULES_VERSION
from pen_stack.verify.schema import Verdict


def _plan_confidence(design: Design) -> dict:
    """Calibrated plan confidence on the SOFT components, only when the design carries the per-axis scores
    (safety / p_durable / writer_activity). Otherwise None (abstain) — never fabricated."""
    extra = design.model_extra or {}
    keys = ("safety", "p_durable", "writer_activity")
    if not all(k in extra and extra[k] is not None for k in keys):
        return {"confidence": None, "interval": None}
    import pandas as pd

    from pen_stack.planner.optimize import attach_uncertainty
    row = pd.DataFrame([{"chrom": design.chrom or "chr?", "bin": 0,
                         "safety": float(extra["safety"]), "p_durable": float(extra["p_durable"]),
                         "writer_activity": float(extra["writer_activity"]), "score": 0.0}])
    intent = design.edit_intent or "safe_harbour_insertion"
    out = attach_uncertainty(row, intent, ood_factor=float(extra.get("ood_factor", 1.0)))
    r = out.iloc[0]
    return {"confidence": float(r["confidence"]), "interval": [float(r["score_lo"]), float(r["score_hi"])]}


def verify(design: Design | dict, question: str | None = None) -> Verdict:
    """Verify a proposed write. ``design`` may be a Design or a plain dict (e.g. from REST/MCP JSON)."""
    if isinstance(design, dict):
        question = question or design.pop("question", None)
        design = Design(**design)

    from pen_stack.agent.epistemic import classify
    from pen_stack.planner.router import route_and_evaluate

    routed = route_and_evaluate(design)
    routing = routed["routing"]

    # scope: out-of-scope question (known-unknowns) + rule scope_flags
    scope_flags: list[dict[str, Any]] = []
    oos_hit = False
    if question:
        from pen_stack.agent.scope import match_scope
        m = match_scope(question)
        if m:
            oos_hit = True
            scope_flags.append({"kind": "known_unknown", "id": m["id"], "reason": m["deferral"]})

    if routed["deferred"]:
        verdict = classify(grounded=False, out_of_scope=True)
        return Verdict(
            legal=None, deferred=True, write_type=design.write_type, routing=routing,
            rule_results=[], violations=[], soft_flags=[],
            scope_flags=scope_flags + [{"kind": "unsupported_write_type", "reason": routing["reason"]}],
            confidence=None, interval=None, epistemic_status=verdict.status,
            provenance={"rules_version": RULES_VERSION, "source": "router(deferred)"}, no_fabrication=True)

    results = routed["rule_results"]
    violations = [r for r in results if r["kind"] == "hard_reject" and r["status"] == "violate"]
    soft = [r for r in results if r["kind"] == "soft_penalty" and r["status"] == "flag"]
    rule_scope = [{"kind": "rule_scope", "rule_id": r["rule_id"], "reason": r["reason"]}
                  for r in results if r["kind"] == "scope_flag" and r["status"] == "scope"]
    scope_flags += rule_scope

    pc = _plan_confidence(design)
    verdict = classify(grounded=True, confidence=pc["confidence"], out_of_scope=oos_hit)

    # v4.0 WS-WV: if the design carries a GENERATED candidate writer sequence, critique it (fold / active
    # site / deliverability / reachability) — never a claim that it works. Adds a scope flag, never confidence.
    writer_critique = None
    cand_seq = (design.model_extra or {}).get("writer_candidate_seq")
    if cand_seq:
        from pen_stack.atlas.writer_verify import critique_candidate
        writer_critique = critique_candidate(
            cand_seq, writer_family=design.writer_family or "bridge_IS110",
            delivery_vehicle=design.delivery_vehicle, no_integration=design.no_integration,
            site_seq=design.site_seq)
        scope_flags.append({"kind": "writer_candidate_critique", "pass": writer_critique["pass"],
                            "flags": writer_critique["flags"],
                            "reason": "generated writer is critiqued, never claimed to work (v4.0 WS-WV)"})

    return Verdict(
        legal=routed["legal"], deferred=False, write_type=design.write_type, routing=routing,
        rule_results=results,
        violations=[{"rule_id": v["rule_id"], "reason": v["reason"], "citation": v.get("citation", [])}
                    for v in violations],
        soft_flags=[{"rule_id": s["rule_id"], "reason": s["reason"], "value": s.get("value")} for s in soft],
        scope_flags=scope_flags,
        confidence=pc["confidence"], interval=pc["interval"], epistemic_status=verdict.status,
        provenance={"rules_version": RULES_VERSION, "source": "rules.solver + L4(uncertainty/scope/epistemic)"},
        no_fabrication=True, writer_critique=writer_critique)
