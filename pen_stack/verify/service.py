"""The verification service, `verify(design) -> Verdict` (Phase 3.3, WS-V).

The first-class "for the AI" surface: submit a proposed genomic write, get back a structured verdict,
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
    (safety / p_durable / writer_activity). Otherwise None (abstain), never fabricated."""
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


def verify(design: Design | dict, question: str | None = None, *, actor: str = "anonymous") -> Verdict:
    """Verify a proposed write. ``design`` may be a Design or a plain dict (e.g. from REST/MCP JSON).

    v5.7 the Guardian: a biosecurity / dual-use safety gate runs FIRST. A design that matches a high-severity
    hazard signature is REFUSED and returned un-evaluated (not scored further); every call is logged to the
    tamper-evident audit trail. The safety verdict is orthogonal to the v5.6 immune profile and is attached to
    every Verdict. ``actor`` is recorded in the audit log."""
    if isinstance(design, dict):
        d = dict(design)
        question = question or d.pop("question", None)
        screen_payload = dict(d)
        design = Design(**d)
    else:
        screen_payload = {**design.model_dump(exclude_none=False), **(design.model_extra or {})}

    # v5.7 WS-INTEGRATE: the safety gate is the first thing every caller inherits.
    from pen_stack.safety.gate import safety_gate
    safety = safety_gate(screen_payload, actor=actor)
    if safety.decision == "refuse":
        return Verdict(
            legal=None, deferred=False, write_type=design.write_type, routing={},
            rule_results=[], violations=[], soft_flags=[],
            scope_flags=[{"kind": "safety_refused", "reason": safety.reason,
                          "signatures": [h.provenance.get("signature_id") for h in safety.hits]}],
            confidence=None, interval=None, epistemic_status="refused",
            provenance={"rules_version": RULES_VERSION, "source": "safety_gate(refused)"},
            no_fabrication=True, safety=safety)

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
            provenance={"rules_version": RULES_VERSION, "source": "router(deferred)"}, no_fabrication=True,
            safety=safety)

    results = routed["rule_results"]
    violations = [r for r in results if r["kind"] == "hard_reject" and r["status"] == "violate"]
    soft = [r for r in results if r["kind"] == "soft_penalty" and r["status"] == "flag"]
    rule_scope = [{"kind": "rule_scope", "rule_id": r["rule_id"], "reason": r["reason"]}
                  for r in results if r["kind"] == "scope_flag" and r["status"] == "scope"]
    scope_flags += rule_scope

    # v7.1.5: chromosome validation + gene/chromosome concordance + chromosome-context advisory. The free-text
    # chrom field does not move the scored locus (scoring is indexed by the gene's resolved coordinates), so a
    # mismatch / invalid value / chromosome-context note is surfaced as a scope flag, never silently ignored.
    from pen_stack.planner.chromosome import chromosome_concordance, chromosome_context
    conc = chromosome_concordance(design.gene, getattr(design, "chrom", None))
    if conc["status"] in ("invalid", "mismatch", "unverifiable"):
        scope_flags.append({"kind": f"chromosome_{conc['status']}", "reason": conc["message"],
                            "entered": conc["entered"], "gene_chrom": conc["gene_chrom"]})
    ctx = chromosome_context(getattr(design, "chrom", None))
    if ctx:
        scope_flags.append({"kind": "chromosome_context", "chrom": ctx["chrom"], "reason": ctx["note"]})

    pc = _plan_confidence(design)
    verdict = classify(grounded=True, confidence=pc["confidence"], out_of_scope=oos_hit)

    # v4.0 WS-WV: if the design carries a GENERATED candidate writer sequence, critique it (fold / active
    # site / deliverability / reachability), never a claim that it works. Adds a scope flag, never confidence.
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

    # v5.1 WS-IMMUNE: if the design names a delivery vehicle, surface its DOCUMENTED ordinal immune/safety/
    # efficacy priors (with the standing "magnitude is a known-unknown" scope flag). This never adds confidence
    # and never predicts a magnitude, it exposes the curated qualitative tradeoff so safety can be weighed.
    delivery_profile = None
    if design.delivery_vehicle:
        from pen_stack.planner.delivery_immunology import safety_efficacy_profile
        delivery_profile = safety_efficacy_profile(design.delivery_vehicle)
        if delivery_profile and delivery_profile.get("tradeoff"):
            scope_flags.append({"kind": "delivery_immune_profile",
                                "vehicle": delivery_profile["vehicle"],
                                "tradeoff": delivery_profile["tradeoff"],
                                "magnitude_id": delivery_profile["magnitude_scope_flag"]["id"],
                                "reason": "documented ordinal immune/safety priors surfaced; the in-vivo immune "
                                          "MAGNITUDE remains a known-unknown (not predicted)"})

    # v5.4 WS-INNATE: if a cargo SEQUENCE is supplied, compute its innate-sensing load from sequence
    # (CpG/TLR9 for DNA, U/dsRNA for mRNA). Surfaced as a scope flag; the realized innate RESPONSE magnitude
    # is a known-unknown. Cargo form = the writer output form, else the vehicle's first compatible form.
    if design.cargo_seq:
        form = design.writer_output_form
        if not form and design.delivery_vehicle:
            from pen_stack.planner.delivery_vehicles import vehicle as _veh
            forms = (_veh(design.delivery_vehicle) or {}).get("compatible_cargo_form") or []
            form = forms[0] if forms else None
        if form:
            from pen_stack.planner.innate_sensing import innate_sensing
            inr = innate_sensing(design.cargo_seq, form)
            if inr.available:
                scope_flags.append({"kind": "cargo_innate_sensing", "cargo_form": form,
                                    "innate_score": inr.value["innate_score"], "pathway": inr.value["pathway"],
                                    "reason": "computed sequence-intrinsic innate-sensing load; the realized "
                                              "in-vivo innate RESPONSE magnitude is a known-unknown"})
                if delivery_profile is not None:
                    delivery_profile = dict(delivery_profile)
                    delivery_profile["cargo_innate"] = inr.value

    # v5.6 WS-PROFILE: the unified per-axis immune-risk profile (genotox / CD8 epitope / innate / pre-existing
    # NAb / anti-PEG), each with its own uncertainty + WS-CALIB validation label; collapsed_score is None
    # (never fused into one number); the in-vivo magnitude + patient titer stay known-unknowns.
    immune_profile = None
    if design.delivery_vehicle:
        from pen_stack.planner.immune_profile import immune_profile as _immune_profile
        extra = design.model_extra or {}
        immune_profile = _immune_profile({
            "delivery_vehicle": design.delivery_vehicle, "serotype": extra.get("serotype"),
            "cargo_seq": design.cargo_seq, "writer_output_form": design.writer_output_form,
            "pegylated": extra.get("pegylated")})

    return Verdict(
        legal=routed["legal"], deferred=False, write_type=design.write_type, routing=routing,
        rule_results=results,
        violations=[{"rule_id": v["rule_id"], "reason": v["reason"], "citation": v.get("citation", [])}
                    for v in violations],
        soft_flags=[{"rule_id": s["rule_id"], "reason": s["reason"], "value": s.get("value")} for s in soft],
        scope_flags=scope_flags,
        confidence=pc["confidence"], interval=pc["interval"], epistemic_status=verdict.status,
        provenance={"rules_version": RULES_VERSION, "source": "rules.solver + L4(uncertainty/scope/epistemic)"},
        no_fabrication=True, writer_critique=writer_critique, delivery_profile=delivery_profile,
        immune_profile=immune_profile, safety=safety)
