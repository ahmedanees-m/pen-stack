"""Groundedness benchmark (PEN-CHAT P-WS5, re-scoped v7.1.1).

The corrected framing: the chat ANSWERS general and social questions (labelled), grounds genome-writing questions in
the cited corpus, and abstains ONLY on a specific unsourceable empirical claim. The honesty metric is therefore
FALSE-GROUNDING (a non-engine fact presented as a PEN-STACK result), not answer-suppression.

Measured deterministically (allow_llm=False, lexical retriever; reproducible in CI):
  * citation_coverage  - on the CITED answers, every factual line maps to a source (gate P-G3, target 1.0);
  * unsupported_claims - a cited answer never lacks sources / leaks an [unverified] number (target 0);
  * false_grounding    - a general/social/abstain answer mislabelled as a PEN-STACK result (target 0);
  * helpful_answer_rate - general + social questions are ANSWERED, not abstained (regression guard, target 1.0);
  * abstention_correct  - the specific unsourceable empirical claims abstain.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("PEN_RAG_NO_EMBED", "1")

from pen_stack.rag.ground import ground_general  # noqa: E402

_DIR = Path(__file__).resolve().parent
_UNVERIFIED = "[unverified]"


def load_cases() -> list[dict]:
    with open(_DIR / "cases.jsonl", encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def run() -> dict:
    cases = load_cases()
    citation_hits = citation_total = unsupported = false_grounding = 0
    by_gold = {"cited": [0, 0], "general": [0, 0], "social": [0, 0], "abstain": [0, 0]}  # [pass, n]
    for c in cases:
        g = ground_general(c["q"], allow_llm=False)
        gold, status, prov = c["gold"], g["status"], g["provenance"]
        by_gold[gold][1] += 1
        ok = False
        if gold == "cited":
            ok = status == "grounded" and prov == "literature-cited" and bool(g.get("sources"))
            lines = [ln for ln in g["reply"].splitlines() if ln.strip().startswith("- ")]
            citation_total += len(lines)
            citation_hits += sum(1 for ln in lines if "[" in ln and "]" in ln)
            if status == "grounded" and (not g.get("sources") or _UNVERIFIED in g["reply"]):
                unsupported += 1
        elif gold == "general":
            ok = status == "general" and prov == "general"          # ANSWERED + labelled, NOT abstained
        elif gold == "social":
            ok = status == "social" and prov == "general"
        elif gold == "abstain":
            ok = status == "abstained" and prov == "abstained"
        by_gold[gold][0] += int(ok)
        # false-grounding: ANY non-engine answer presented as a PEN-STACK-computed result
        if prov == "pen-stack":
            false_grounding += 1

    answered = sum(by_gold[g][0] for g in ("general", "social"))
    answerable = sum(by_gold[g][1] for g in ("general", "social"))
    citation_coverage = (citation_hits / citation_total) if citation_total else 1.0
    return {
        "n_cases": len(cases),
        "citation_coverage": round(citation_coverage, 3),
        "unsupported_claims_through_guard": unsupported,
        "false_grounding_rate": round(false_grounding / len(cases), 3),
        "helpful_answer_rate": round(answered / answerable, 3) if answerable else 1.0,
        "abstention_on_specific_unsourceable": round(by_gold["abstain"][0] / by_gold["abstain"][1], 3) if by_gold["abstain"][1] else 1.0,
        "per_gold_pass": {g: f"{v[0]}/{v[1]}" for g, v in by_gold.items()},
        "retrieval": "lexical (CI); semantic in production",
        "gates": {
            "P-G3 citation_coverage == 1.0": citation_coverage >= 0.999,
            "P-G3 0 unsupported claims": unsupported == 0,
            "false_grounding == 0": false_grounding == 0,
            "general+social answered (no regression)": answered == answerable,
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
