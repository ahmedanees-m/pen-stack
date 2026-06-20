"""Scope matcher over the known-unknowns registry (Phase 3.2, WS-EP / EP2).

Matches an incoming question against `configs/known_unknowns.yaml` and, on a hit, returns a structured
deferral ("this requires X, which PEN-STACK does not model") instead of letting the agent guess. This is the
*out-of-scope* arm of trustworthiness, distinct from the clinical-directive refusal in `agent/guardrails.py`
(which this complements): guardrails refuse *clinical advice*; the scope matcher defers *biology beyond any
tool here* (the unknown funnel: structure→phenotype, in-vivo immunogenicity, long-term durability, epistasis,
polygenic, germline).

Deterministic substring + regex matching (no LLM) so the deferral is reproducible and testable. The result
feeds `agent.epistemic.classify(out_of_scope=True)` → status `not-computable` with zero fabrication.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from pen_stack._resources import resource

_CFG = "configs/known_unknowns.yaml"


@lru_cache(maxsize=1)
def load_registry(path: str | Path | None = None) -> list[dict]:
    p = Path(path) if path else resource(_CFG)
    data = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
    return data.get("known_unknowns", [])


def match_scope(question: str, registry: list[dict] | None = None) -> dict | None:
    """Return a structured deferral if the question hits a known-unknown, else None (in scope).

    A hit = any `match_terms` substring (lowercased) OR any `patterns` regex matches. Returns the matched
    entry's id/title/requires/why + a ready-to-surface deferral message.
    """
    reg = registry if registry is not None else load_registry()
    q = question.lower()
    for entry in reg:
        hit_term = next((t for t in entry.get("match_terms", []) if t in q), None)
        hit_pat = None
        if not hit_term:
            for pat in entry.get("patterns", []):
                if re.search(pat, q, re.IGNORECASE):
                    hit_pat = pat
                    break
        if hit_term or hit_pat:
            return {"out_of_scope": True, "id": entry["id"], "title": entry["title"],
                    "requires": entry["requires"], "why": entry["why"],
                    "matched_on": hit_term or f"pattern:{hit_pat}",
                    "deferral": (f"This question is out of scope for PEN-STACK: it concerns "
                                 f"{entry['title']}, which requires {entry['requires']}. "
                                 f"{entry['why']}. PEN-STACK does not model this and will not guess a value.")}
    return None


def is_out_of_scope(question: str) -> bool:
    return match_scope(question) is not None
