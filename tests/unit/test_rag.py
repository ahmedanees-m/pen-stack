"""Phase 2, Step 2.8 — grounded, cited Q&A.

Pre-registered criteria: every quantitative answer traces to a tool call (no LLM-guessed numbers);
every factual claim carries a citation; out-of-scope/clinical-directive questions are refused.
"""
from __future__ import annotations

from pen_stack.agent.guardrails import enforce_grounded, out_of_scope
from pen_stack.rag.qa import answer


def test_refuses_clinical_directive():
    a = answer("Should I treat my patient with ISCro4?")
    assert a["refused"] is True
    assert out_of_scope("should I dose my patient") is not None
    assert out_of_scope("which writer reaches CCR5") is None


def test_family_answer_is_cited():
    a = answer("Tell me about the bridge IS110 recombinase family")
    assert a["refused"] is False
    assert a["citations"], "factual family answer must carry citations"
    assert any(p["tool"] == "atlas.query" for p in a["provenance"])


def test_numeric_claim_has_tool_provenance():
    a = answer("Where can I insert a cassette into CCR5?")
    # if a number was produced, it must be backed by a tool call
    import re
    if re.search(r"\d\.\d", a["answer"]):
        assert a["provenance"], "numeric writability must come from a tool call"
        assert any("loci_for_gene" in p["tool"] for p in a["provenance"])
        assert a["citations"], "tool-derived writability must be cited"


def test_enforce_grounded_suppresses_unbacked_numbers():
    bad = enforce_grounded({"answer": "the score is 0.99", "provenance": []})
    assert "suppressed" in bad["answer"]
