"""PEN-RAG grounding for the chat's General lane (v7.1).

Replaces "trained knowledge + a label" with **retrieve -> cite-or-silence -> guard**:
  * retrieve the top chunks from the provenance-tagged corpus;
  * if the top retrieval confidence is below threshold -> ABSTAIN ("no grounded source"), never answer from priors;
  * otherwise ground the answer in the retrieved, cited chunks. The deterministic path returns the chunks verbatim
    with their [source . DOI] tags (citation coverage = 1.0 by construction). If the LLM is allowed it only narrates
    over those same sources under a citation-or-silence system prompt, and the number guard strips any value not in
    the sources.
General answers are always labelled "literature-cited", never presented as a PEN-STACK-computed result.
"""
from __future__ import annotations

import os

from pen_stack.rag.embed import tokenize
from pen_stack.rag.retrieve import retrieve

# nomic-embed-text compresses cosines into a narrow high band, so an absolute cosine alone cannot separate a valid
# in-corpus query from an off-topic one. We use a HYBRID gate: a moderate cosine floor for ranking PLUS a lexical
# content-overlap check (a genuinely off-topic query shares no content word with the top chunk), with a high-cosine
# escape for true paraphrases. The safe failure direction is to abstain, so the gate is deliberately conservative.
THRESHOLD = float(os.getenv("PEN_RAG_THRESHOLD", "0.50"))          # semantic cosine floor
_SEM_HIGH = float(os.getenv("PEN_RAG_THRESHOLD_HIGH", "0.72"))     # cosine high enough to ground without lexical overlap
_LEX_THRESHOLD = float(os.getenv("PEN_RAG_LEX_THRESHOLD", "0.05")) # jaccard floor for the fallback retriever


def _is_grounded(query: str, hits: list[dict], method: str) -> bool:
    """Is the corpus a real source for this query (vs. abstain)?"""
    if not hits:
        return False
    top = hits[0]
    if not method.startswith("semantic"):
        return top["score"] >= _LEX_THRESHOLD
    lexical_overlap = bool(tokenize(query) & tokenize(top["text"]))
    return top["score"] >= THRESHOLD and (lexical_overlap or top["score"] >= _SEM_HIGH)
_LABEL = "Literature-cited (PEN-CHAT corpus) - not a PEN-STACK-computed result:"
_ABSTAIN = ("I have no grounded source in the PEN-CHAT corpus for that, so I won't answer it from unsourced general "
            "knowledge. The corpus covers PEN-STACK's writers, metrics, scope, and curated genome-writing "
            "literature - ask within that, or let the engine compute a specific, grounded answer.")


def _dedup_sources(hits: list[dict]) -> list[dict]:
    seen, out = set(), []
    for h in hits:
        sid = h["source_id"]
        if sid in seen:
            continue
        seen.add(sid)
        out.append({"source_id": sid, "doi": h.get("doi") or None, "type": h["type"],
                    "score": round(h["score"], 3)})
    return out


def ground_general(message: str, *, allow_llm: bool = True) -> dict:
    """Return the chat envelope for a grounded (or abstained) General-lane answer."""
    r = retrieve(message, k=4)
    if not _is_grounded(message, r["hits"], r["method"]):
        return {"status": "abstained", "reply": _ABSTAIN, "sources": [], "provenance": "abstained",
                "grounded": False, "backend": "deterministic", "retrieval": r["method"], "top_score": r["top_score"]}
    floor = THRESHOLD if r["method"].startswith("semantic") else _LEX_THRESHOLD
    grounded_hits = [h for h in r["hits"] if h["score"] >= floor] or r["hits"][:2]

    sources = _dedup_sources(grounded_hits)
    deterministic = _LABEL + "\n\n" + "\n\n".join(
        f"- {h['text']}  [{h['source_id']}{(' · ' + h['doi']) if h.get('doi') else ''}]" for h in grounded_hits)

    if allow_llm:
        from pen_stack.web.llm import _enforce_grounding, _run_llm
        from pen_stack.web.tools import extract_grounded_numbers
        ctx = "\n\n".join(
            f"[{i + 1}] ({h['source_id']}{(' DOI ' + h['doi']) if h.get('doi') else ''}) {h['text']}"
            for i, h in enumerate(grounded_hits))
        system = ("You answer ONLY from the SOURCES provided. After each claim, cite the bracketed [n] it came from. "
                  "If the sources do not cover the question, say exactly that. Never add a fact, number, name, or "
                  "vehicle that is not in the sources. Never present anything as a PEN-STACK-computed result.")
        prompt = f"SOURCES:\n{ctx}\n\nQUESTION: {message}\n\nAnswer concisely, citing [n] after each claim."
        text, backend = _run_llm(prompt, system)
        if text:
            allow = extract_grounded_numbers({"hits": [h["text"] for h in grounded_hits]})
            cleaned = _enforce_grounding(text.strip(), allow)
            return {"status": "grounded", "reply": _LABEL + "\n\n" + cleaned, "sources": sources,
                    "provenance": "literature-cited", "grounded": True, "backend": backend,
                    "retrieval": r["method"], "top_score": r["top_score"]}

    return {"status": "grounded", "reply": deterministic, "sources": sources, "provenance": "literature-cited",
            "grounded": True, "backend": "deterministic", "retrieval": r["method"], "top_score": r["top_score"]}
