"""LLM guardrails for PEN-STACK platform services (Phase 2, §2B).

The contract every service obeys: **grounded** (answers from the curated atlas + indexed literature),
**cited** (every factual claim carries a source), **defer-to-models** (any quantitative claim is produced
by a validated tool call, never guessed by the LLM), **decision-support** (never a clinical directive),
**budget-aware**, **auditable** (a provenance block accompanies every answer).
"""
from __future__ import annotations

import re

DISCLAIMER = ("Decision-support only — PEN-STACK returns calibrated risk/durability/reachability "
              "estimates, not clinical directives. Tier-2/3 reachability is candidate and requires "
              "experimental validation. Verify all designs experimentally.")

# Questions PEN-STACK must refuse: clinical directives, diagnosis, dosing, treatment decisions for a
# specific patient. (Scientific questions about loci/writers/safety are in scope.)
_REFUSE_PATTERNS = [
    r"\bshould i (treat|inject|dose|administer|give)\b",
    r"\b(diagnos|prescrib|dosage|dosing)\w*\b",
    r"\b(my|this|the) patient\b",
    r"\bdose\b.{0,40}\b(child|patient|human|person|kid|baby|infant)\b",  # dosing for a person = clinical
    r"\b(what|which) dose\b",                                            # dosing questions are clinical
    r"\bis it safe (to|for) (a |the |my )?(patient|human|person|child)\b",
    r"\bclinical (decision|recommendation|advice) for\b",
]


def out_of_scope(question: str) -> str | None:
    """Return a refusal reason if the question is a clinical directive, else None."""
    q = question.lower()
    for pat in _REFUSE_PATTERNS:
        if re.search(pat, q):
            return ("This is a clinical-directive question. PEN-STACK is decision-support "
                    "infrastructure for genome-writing design and does not give clinical advice.")
    return None


def enforce_grounded(answer: dict) -> dict:
    """Assert the auditable contract on a finished answer: numeric claims must trace to a tool call."""
    answer.setdefault("disclaimer", DISCLAIMER)
    answer.setdefault("provenance", [])
    answer.setdefault("citations", [])
    # if the answer reports numbers, there must be a tool-call provenance entry backing them
    has_number = bool(re.search(r"\d", str(answer.get("answer", ""))))
    if has_number and not answer["provenance"]:
        answer["warning"] = "numeric claim without tool provenance — suppressed"
        answer["answer"] = "(suppressed: a number was produced without a backing tool call)"
    return answer
