"""Published, machine-readable rule spec (v6.12 PEN-VERIFY, F-WS1).

Exports the genome-writing rule base (``configs/rules/*.yaml``) as a single citable, machine-readable document:
every rule with its id, kind, category, mechanism, the named evaluator that executes it, its parameters, its
provenance (DOI or note), a test reference, and its scope limit. The spec is a faithful export of the live
ruleset, not a second copy of the logic: ``spec_parity`` proves the exported records round-trip to the exact
``Ruleset`` the solver loads (0 mismatches), every rule names a registered evaluator (so the spec is
executable), and every rule carries a DOI or an explicit note. This is what makes the rules externally
readable and citable without changing any decision.
"""
from __future__ import annotations

import json
from typing import Any

from pen_stack.rules.evaluators import registered_evaluators
from pen_stack.rules.loader import RULES_VERSION, load_ruleset
from pen_stack.rules.schema import Rule

_FIELDS = ("id", "kind", "category", "mechanism", "evaluator", "param", "provenance", "test_ref", "scope")


def export_spec() -> dict[str, Any]:
    """Return the machine-readable rule spec: a version, the category list, and one record per rule with its
    full provenance, the executing evaluator, and whether it carries a citation."""
    rs = load_ruleset()
    registered = registered_evaluators()
    rules: list[dict[str, Any]] = []
    for r in rs.rules:
        prov = r.provenance or {}
        doi = list(prov.get("doi", []) or [])
        rules.append({
            "id": r.id, "kind": r.kind, "category": r.category, "mechanism": r.mechanism,
            "evaluator": r.evaluator, "param": r.param, "provenance": prov,
            "citation": doi, "note": prov.get("note"), "test_ref": r.test_ref, "scope": r.scope,
            "evaluator_registered": r.evaluator in registered,
            "has_citation": bool(doi or prov.get("note")),
        })
    return {
        "spec": "PEN-STACK genome-writing rule base",
        "version": rs.version,
        "n_rules": len(rules),
        "categories": sorted({r["category"] for r in rules}),
        "kinds": sorted({r["kind"] for r in rules}),
        "note": "A rule is data, not code: each record names the evaluator that executes it against a Design. "
                "Relocating the rules into this spec changes no decision (proven by the parity tests).",
        "rules": rules,
    }


def spec_parity() -> dict[str, Any]:
    """F-G1: the exported spec faithfully reproduces the live ruleset. Checks (a) every exported record
    round-trips to the identical ``Rule`` the solver loaded (0 mismatches), (b) every rule names a registered
    evaluator, and (c) every rule carries a DOI or a note."""
    spec = export_spec()
    live = load_ruleset().rules
    reload = [Rule(**{k: rec[k] for k in _FIELDS}) for rec in spec["rules"]]
    mismatches = sorted({a.id for a, b in zip(live, reload, strict=True) if a != b}
                        | ({r.id for r in live} ^ {r.id for r in reload}))
    return {
        "n_rules": spec["n_rules"],
        "round_trip_mismatches": mismatches,
        "parity_0_mismatch": len(mismatches) == 0,
        "all_evaluators_registered": all(r["evaluator_registered"] for r in spec["rules"]),
        "uncited_rules": [r["id"] for r in spec["rules"] if not r["has_citation"]],
        "all_rules_cited": all(r["has_citation"] for r in spec["rules"]),
        "rules_version": RULES_VERSION,
    }


def write_spec(path: str = "benchmarks/verify/rule_spec.json") -> str:
    """Write the machine-readable spec to ``path`` (committed artifact). Returns the path."""
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(export_spec(), fh, indent=2)
        fh.write("\n")
    return path
