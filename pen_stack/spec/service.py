"""WriteSpec service (v6.14, Stage A): the one call the surfaces (REST / MCP / web builder) use.

``parse_request`` runs the grounded extractor, plans clarifying questions, and (optionally) the feasibility
check, returning a single JSON-able payload: the typed WriteSpec, the assumptions behind every inferred field,
the clarifying questions for anything underspecified, the unresolved terms, the downstream design adapter, and
the feasibility verdict. Nothing is fabricated: unresolved stays null, inferred is labelled, ambiguous asks.
"""
from __future__ import annotations

from typing import Any

from pen_stack.spec.clarify import clarifying_questions
from pen_stack.spec.extract import extract_writespec


def parse_request(prose: str, *, overrides: dict | None = None, check_feasibility: bool = True) -> dict[str, Any]:
    """Parse prose into a typed WriteSpec + clarifications + (optionally) a feasibility verdict."""
    spec = extract_writespec(prose, overrides=overrides)
    qs = clarifying_questions(spec)
    out: dict[str, Any] = {
        "writespec": spec.model_dump(),
        "assumptions": spec.assumptions,
        "clarifications": qs,
        "actionable": not qs,
        "unresolved": spec.unresolved,
        "ontology_validation": spec.ontology_validation(),
        "legacy_design": spec.to_legacy_design(),
        "no_fabrication": True,
    }
    if check_feasibility:
        from pen_stack.spec.satisfy import check_satisfiable
        out["feasibility"] = check_satisfiable(spec).model_dump()
    return out
