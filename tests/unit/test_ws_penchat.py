"""PEN-CHAT (v7.1) - P-WS1: the grounded General lane (PEN-RAG).

Runs with the deterministic LEXICAL retriever (PEN_RAG_NO_EMBED=1) so it is reproducible in CI without Ollama;
the committed corpus + embeddings still ship for the live semantic path. Asserts the gate-P-G1 properties:
the General lane grounds in-corpus queries with cited sources, ABSTAINS on out-of-corpus queries (never answers
from unsourced priors), and the grounded deterministic reply has full citation coverage.
"""
import os

os.environ["PEN_RAG_NO_EMBED"] = "1"  # force the lexical fallback: deterministic, no embedder, CI-safe

import pytest  # noqa: E402

from pen_stack.rag.corpus import load_corpus  # noqa: E402
from pen_stack.rag.ground import ground_general  # noqa: E402
from pen_stack.rag.retrieve import retrieve  # noqa: E402

_IN_CORPUS = [
    "What integration efficiency do Bxb1 hyperactive variants reach?",
    "What is eePASSIGE efficiency at AAVS1?",
    "How is genotoxicity computed?",
]
_OUT_OF_CORPUS = [
    "What is the capital of France?",
    "How do I bake sourdough bread?",
    "Who won the world cup in 2018?",
]


def test_corpus_is_provenance_tagged():
    df = load_corpus()
    assert len(df) > 50
    for col in ("chunk_id", "text", "source_id", "doi", "access_grade", "type", "scope_status"):
        assert col in df.columns
    assert df["source_id"].notna().all()
    # every measured efficiency chunk carries a DOI (real, cited provenance)
    eff = df[df["type"] == "efficiency_measurement"]
    assert len(eff) > 0 and (eff["doi"].str.len() > 0).all()


def test_retrieve_is_deterministic_and_returns_sources():
    r = retrieve(_IN_CORPUS[0], k=4)
    assert r["method"].startswith("lexical")  # CI path
    assert r["hits"] and all("source_id" in h and "doi" in h for h in r["hits"])


@pytest.mark.parametrize("q", _IN_CORPUS)
def test_general_lane_grounds_in_corpus_with_citations(q):
    g = ground_general(q, allow_llm=False)
    assert g["status"] == "grounded"
    assert g["provenance"] == "literature-cited"
    assert g["grounded"] is True
    assert g["sources"], "a grounded answer must carry its sources"
    # citation coverage = 1.0 on the deterministic path: every content line is source-tagged
    content_lines = [ln for ln in g["reply"].splitlines() if ln.strip().startswith("- ")]
    assert content_lines and all("[" in ln and "]" in ln for ln in content_lines)


@pytest.mark.parametrize("q", _OUT_OF_CORPUS)
def test_general_lane_abstains_out_of_corpus(q):
    g = ground_general(q, allow_llm=False)
    assert g["status"] == "abstained"
    assert g["grounded"] is False
    assert g["provenance"] == "abstained"
    assert not g["sources"]  # nothing fabricated, nothing cited


def test_chat_general_lane_is_grounded_or_abstains_never_unsourced():
    """Through the web chat: a general query is either literature-cited or an honest abstention - never the old
    'trained knowledge' provenance, and never grounded=True without sources."""
    from pen_stack.web.llm import grounded_reply
    out = grounded_reply("Tell me about Bxb1 integrase efficiency", allow_llm=False)
    assert out["mode"] == "general"
    assert out["provenance"] in ("literature-cited", "abstained")
    if out["grounded"]:
        assert out.get("sources")
