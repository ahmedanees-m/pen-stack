"""Clarifying-question planner (v6.14, Stage A, A-WS3).

Given a :class:`WriteRequest`, return the minimal set of questions needed to make it actionable: the required
fields that are unspecified or ambiguous. The extractor already populates ``clarifications`` during parsing;
this module is the standalone planner an agent calls to decide whether to ask before composing a write, and to
get a clean, de-duplicated question list. It never guesses a value: a missing required field becomes a question.
"""
from __future__ import annotations

from pen_stack.spec.writespec import WriteRequest

# fields that must be present for a write to be composable (by write-type)
_REQUIRED_TARGET = {"insertion", "excision", "inversion", "replacement", "regulatory_rewrite",
                    "landing_pad_install", "multiplex"}


def clarifying_questions(spec: WriteRequest) -> list[str]:
    """The minimal de-duplicated question list for the underspecified / ambiguous required fields."""
    qs: list[str] = list(spec.clarifications)  # carry the extractor's questions
    if spec.write_type in _REQUIRED_TARGET and spec.target.kind == "unspecified":
        q = "Which gene, locus, att/landing site, or disease phenotype should the write target?"
        if q not in qs:
            qs.append(q)
    # an insertion with no cargo at all is underspecified
    if spec.write_type == "insertion" and not spec.cargo:
        qs.append("What cargo should be inserted (size in bp/kb, and any features such as promoter / CDS / polyA)?")
    # an unresolved term needs disambiguation, not a guess
    for term in spec.unresolved:
        qs.append(f"The term '{term}' could not be resolved to a gene / locus / cell / phenotype; please clarify it.")
    # de-duplicate, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def is_actionable(spec: WriteRequest) -> bool:
    """True when no clarifying question remains (the spec is complete enough to compose a write)."""
    return not clarifying_questions(spec)
