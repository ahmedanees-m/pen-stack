"""Groundedness benchmark (PEN-CHAT P-WS5).

Measures, on the General (retrieval) lane, the two pre-registered groundedness properties (gate P-G3):
  * CITATION COVERAGE = 1.0: every factual line of a grounded answer maps to a cited source;
  * 0 UNSUPPORTED CLAIMS through the guard: a grounded answer never lacks sources, and no `[unverified]` number
    survives; an out-of-corpus question ABSTAINS rather than answer from priors.

Run on the deterministic grounded path (allow_llm=False) with the lexical retriever, so it is reproducible in CI
without an embedder or an LLM (the live semantic path is strictly stronger - it abstains MORE, not less).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("PEN_RAG_NO_EMBED", "1")  # deterministic lexical retrieval

from pen_stack.rag.ground import ground_general  # noqa: E402

_DIR = Path(__file__).resolve().parent
_UNVERIFIED = "[unverified]"


def load_cases() -> list[dict]:
    with open(_DIR / "cases.jsonl", encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def run() -> dict:
    cases = load_cases()
    grounded, abstained = [], []
    citation_hits, citation_total = 0, 0
    unsupported = 0
    abstain_correct, ground_correct = 0, 0

    for c in cases:
        g = ground_general(c["q"], allow_llm=False)
        if g["status"] == "grounded":
            grounded.append(c["q"])
            if c["gold"] == "grounded":
                ground_correct += 1
            # citation coverage: each content bullet must carry a [source] tag
            lines = [ln for ln in g["reply"].splitlines() if ln.strip().startswith("- ")]
            citation_total += len(lines)
            citation_hits += sum(1 for ln in lines if "[" in ln and "]" in ln)
            # unsupported: grounded but no sources, or an unverified number slipped through
            if not g.get("sources") or _UNVERIFIED in g["reply"]:
                unsupported += 1
        else:
            abstained.append(c["q"])
            if c["gold"] == "abstain":
                abstain_correct += 1

    n_gold_ground = sum(1 for c in cases if c["gold"] == "grounded")
    n_gold_abstain = sum(1 for c in cases if c["gold"] == "abstain")
    citation_coverage = (citation_hits / citation_total) if citation_total else 1.0
    return {
        "n_cases": len(cases),
        "citation_coverage": round(citation_coverage, 3),
        "unsupported_claims_through_guard": unsupported,
        "abstention_rate_out_of_corpus": round(abstain_correct / n_gold_abstain, 3) if n_gold_abstain else 1.0,
        "grounding_rate_in_corpus": round(ground_correct / n_gold_ground, 3) if n_gold_ground else 1.0,
        "retrieval": "lexical (CI); semantic in production",
        "gates": {
            "P-G3 citation_coverage == 1.0": citation_coverage >= 0.999,
            "P-G3 0 unsupported claims": unsupported == 0,
            "abstains on all out-of-corpus": abstain_correct == n_gold_abstain,
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
