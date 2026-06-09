"""The rule solver — evaluate a design against the rule base (Phase 3.3, WS-R / R2).

``evaluate(design, ruleset) -> [RuleResult]`` runs each rule's registered evaluator, deterministically and
ordered, returning a per-rule verdict with reason + citation. ``legal = every APPLICABLE hard_reject rule
passes`` — a not-applicable hard rule (its inputs absent) never blocks. Legality and confidence are kept
separate: this module decides *legality* only; the verifier (WS-V) attaches calibrated confidence on top.
"""
from __future__ import annotations

from pen_stack.rules.evaluators import get_evaluator
from pen_stack.rules.loader import load_ruleset
from pen_stack.rules.schema import Design, RuleResult, Ruleset


def evaluate(design: Design, ruleset: Ruleset | None = None) -> list[RuleResult]:
    rs = ruleset or load_ruleset()
    results: list[RuleResult] = []
    for rule in rs.rules:
        fn = get_evaluator(rule.evaluator)
        results.append(fn(design, rule))
    return results


def is_legal(results: list[RuleResult]) -> bool:
    """Legal = no applicable hard_reject rule is violated."""
    return not any(r.is_blocking for r in results)


def legality_report(design: Design, ruleset: Ruleset | None = None) -> dict:
    """Structured legality summary: legal bool + violations (named, with reason+citation) + flags + scope."""
    results = evaluate(design, ruleset)
    violations = [r for r in results if r.is_blocking]
    flags = [r for r in results if r.kind == "soft_penalty" and r.status == "flag"]
    scope = [r for r in results if r.kind == "scope_flag" and r.status == "scope"]
    return {
        "legal": is_legal(results),
        "n_rules_evaluated": len(results),
        "n_applicable": sum(1 for r in results if r.status != "not_applicable"),
        "violations": [{"rule_id": r.rule_id, "reason": r.reason, "citation": r.citation} for r in violations],
        "soft_flags": [{"rule_id": r.rule_id, "reason": r.reason, "value": r.value} for r in flags],
        "scope_flags": [{"rule_id": r.rule_id, "reason": r.reason} for r in scope],
        "rule_results": [r.model_dump() for r in results],
    }
