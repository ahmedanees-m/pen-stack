"""Write-type router (Phase 3.3, WS-ROUTE).

The v3.2 pipeline handled one workflow — single insertion. ``route(design)`` makes that the *insertion
sub-graph* of a router that dispatches on ``write_type`` (insertion / excision / inversion / replacement /
regulatory_rewrite / landing_pad_install / multiplex), selecting the relevant rule subset + steps per type.
An unsupported or ambiguous write type **defers** (scope flag) — it never guesses. Rarer types ship as
legality/reachability coverage first (status `coverage_only`), stated honestly.

The router selects *which rules apply*; the solver (WS-R) still evaluates them. Routing + legality compose
into the v3.3 verifier (WS-V).
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource
from pen_stack.rules import Design, load_ruleset
from pen_stack.rules.solver import evaluate, is_legal


@lru_cache(maxsize=1)
def load_write_types(path=None) -> dict:
    p = resource("configs/write_types.yaml") if path is None else path
    return yaml.safe_load(open(p, encoding="utf-8").read())["write_types"]


def route(design: Design) -> dict:
    """Dispatch a design to its write-type sub-graph. Unsupported/ambiguous -> deferred (scope flag)."""
    wt = (design.write_type or "").strip()
    table = load_write_types()
    if wt not in table:
        return {"write_type": wt, "supported": False, "deferred": True,
                "reason": f"unsupported/ambiguous write type {wt!r}; supported: {sorted(table)}",
                "rule_categories": [], "steps": []}
    spec = table[wt]
    return {"write_type": wt, "supported": True, "deferred": False,
            "status": spec["status"], "rule_categories": spec["rule_categories"],
            "steps": spec["steps"], "writer_classes": spec.get("writer_classes", []),
            "coverage_only": spec["status"] == "coverage_only",
            "scope_note": spec.get("scope_note"),
            "description": spec["description"]}


def route_and_evaluate(design: Design) -> dict:
    """Route, then evaluate ONLY the routed rule categories against the design. Returns routing + legality."""
    routing = route(design)
    if routing["deferred"]:
        return {"routing": routing, "legal": None, "deferred": True, "rule_results": []}
    cats = set(routing["rule_categories"])
    rs = load_ruleset()
    sub = [r for r in rs.rules if r.category in cats]
    from pen_stack.rules.schema import Ruleset
    results = evaluate(design, Ruleset(version=rs.version, rules=sub))
    return {"routing": routing, "legal": is_legal(results), "deferred": False,
            "rule_results": [r.model_dump() for r in results]}
