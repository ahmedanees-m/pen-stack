"""PEN-RAG grounding for the chat's General lane (v7.1.1).

Retrieval is ADDITIVE, not a gate. The General lane ANSWERS general and social questions by default (restoring the
WS-HYBRID behaviour), clearly LABELLED as general knowledge - a labelled general answer is honest, not a
fabrication, because it is never presented as a PEN-STACK result. Corpus retrieval, when it finds a relevant chunk,
UPGRADES the answer to 'literature-cited' (with its sources). Abstention is the rare exception: it fires only for a
SPECIFIC, unsourceable empirical / quantitative genome-writing claim the corpus does not cover and the engine is
not computing - the genuine citation-or-silence case - so the model cannot dress a fabricated statistic as fact.

Branches:
  social    -> a friendly answer + a pointer to what the engine can compute (no retrieval, no abstention).
  cited     -> a relevant corpus chunk was retrieved -> cite-or-silence answer, provenance 'literature-cited'.
  general   -> background / textbook knowledge -> answer from the LLM, labelled (provenance 'general').
  abstained -> a specific unsourceable empirical claim -> decline + redirect to the engine (provenance 'abstained').
"""
from __future__ import annotations

import os
import re

from pen_stack.rag.embed import tokenize
from pen_stack.rag.retrieve import retrieve

# nomic-embed-text compresses cosines into a narrow high band, so an absolute cosine alone cannot separate a valid
# in-corpus query from an off-topic one. The hybrid gate (cosine floor + lexical content-overlap, with a high-cosine
# escape) decides only whether the corpus is a relevant SOURCE to cite - NOT whether to answer at all.
THRESHOLD = float(os.getenv("PEN_RAG_THRESHOLD", "0.50"))
_SEM_HIGH = float(os.getenv("PEN_RAG_THRESHOLD_HIGH", "0.72"))
_LEX_THRESHOLD = float(os.getenv("PEN_RAG_LEX_THRESHOLD", "0.05"))

# A social / conversational opener: answered naturally, never gated on the corpus.
_SOCIAL = re.compile(r"^\s*(hi|hii+|hey+|hello+|yo|hola|sup|greetings|good (morning|afternoon|evening|day)|"
                     r"thanks?|thank you|cheers|ok(ay)?|cool|nice|great|awesome|who are you|what are you|"
                     r"how are you|what'?s up|introduce yourself|help)\b", re.I)

# A SPECIFIC genome-writing QUANTITATIVE / empirical claim (not definitional / mechanistic background). When the
# corpus has no source for it and it is in the general lane (so the engine is not computing it), we abstain +
# redirect rather than let the model invent a statistic dressed up as fact.
_SPECIFIC_EMPIRICAL = re.compile(
    r"\b(efficienc\w*|integration rate|specificit\w*|on-?target rate|off-?target rate|knock-?in rate|titer|titre|"
    r"affinit\w*|\bkd\b|ic50|fold[- ]improvement|expression level|copy number|"
    r"percent\w* (of )?(integration|editing|knock|insertion))\b", re.I)

_SOCIAL_REPLY = ("Hi - I'm PEN-STACK's genome-writing co-scientist. Ask a genome-writing question (where to insert, "
                 "which writer, delivery, immune risk, off-targets, safety) and the engine computes a grounded, "
                 "traceable answer. I can also answer general background questions, clearly labelled as such.")
_GENERAL_NO_LLM = ("I can answer general background questions when the language model is enabled. Meanwhile, "
                   "PEN-STACK's engine can compute grounded, specific answers for your case.")
_LABEL = "Literature-cited (PEN-CHAT corpus) - not a PEN-STACK-computed result:"
_ABSTAIN_SPECIFIC = ("I don't have a grounded source for that specific value and I won't invent one. PEN-STACK's "
                     "engine can compute it from a concrete design - give me the gene, cell type, and cargo (or "
                     "the writer/guide) and I'll run the site, writer-efficiency, or off-target tools.")


def _is_grounded(query: str, hits: list[dict], method: str) -> bool:
    """Is the corpus a relevant SOURCE to cite for this query?"""
    if not hits:
        return False
    top = hits[0]
    if not method.startswith("semantic"):
        return top["score"] >= _LEX_THRESHOLD
    lexical_overlap = bool(tokenize(query) & tokenize(top["text"]))
    return top["score"] >= THRESHOLD and (lexical_overlap or top["score"] >= _SEM_HIGH)


def _dedup_sources(hits: list[dict]) -> list[dict]:
    seen, out = set(), []
    for h in hits:
        sid = h["source_id"]
        if sid in seen:
            continue
        seen.add(sid)
        out.append({"source_id": sid, "doi": h.get("doi") or None, "type": h["type"], "score": round(h["score"], 3)})
    return out


def _cited_answer(message: str, r: dict, allow_llm: bool) -> dict:
    floor = THRESHOLD if r["method"].startswith("semantic") else _LEX_THRESHOLD
    grounded_hits = [h for h in r["hits"] if h["score"] >= floor] or r["hits"][:2]
    sources = _dedup_sources(grounded_hits)
    deterministic = _LABEL + "\n\n" + "\n\n".join(
        f"- {h['text']}  [{h['source_id']}{(' · ' + h['doi']) if h.get('doi') else ''}]" for h in grounded_hits)
    base = {"status": "grounded", "sources": sources, "provenance": "literature-cited", "grounded": True,
            "retrieval": r["method"], "top_score": r["top_score"]}
    if allow_llm:
        from pen_stack.web.llm import _enforce_grounding, _run_llm
        from pen_stack.web.tools import extract_grounded_numbers
        ctx = "\n\n".join(f"[{i + 1}] ({h['source_id']}{(' DOI ' + h['doi']) if h.get('doi') else ''}) {h['text']}"
                          for i, h in enumerate(grounded_hits))
        system = ("You answer ONLY from the SOURCES provided. After each claim, cite the bracketed [n] it came from. "
                  "If the sources do not cover the question, say so. Never add a number, name, or vehicle that is "
                  "not in the sources. Never present anything as a PEN-STACK-computed result.")
        text, backend = _run_llm(f"SOURCES:\n{ctx}\n\nQUESTION: {message}\n\nAnswer concisely, citing [n].", system)
        if text:
            allow = extract_grounded_numbers({"hits": [h["text"] for h in grounded_hits]})
            return {**base, "reply": _LABEL + "\n\n" + _enforce_grounding(text.strip(), allow), "backend": backend}
    return {**base, "reply": deterministic, "backend": "deterministic"}


def ground_general(message: str, *, allow_llm: bool = True) -> dict:
    """Return the chat envelope for the General lane: answer (social / general / cited) by default; abstain only on a
    specific unsourceable empirical claim."""
    msg = (message or "").strip()
    if _SOCIAL.match(msg):
        return {"status": "social", "reply": _SOCIAL_REPLY, "sources": [], "provenance": "general",
                "grounded": False, "backend": "deterministic", "retrieval": "none", "top_score": 0.0}

    r = retrieve(msg, k=4)
    if _is_grounded(msg, r["hits"], r["method"]):
        return _cited_answer(msg, r, allow_llm)

    # no corpus source. A specific empirical genome-writing claim -> abstain + redirect to the engine.
    if _SPECIFIC_EMPIRICAL.search(msg):
        return {"status": "abstained", "reply": _ABSTAIN_SPECIFIC, "sources": [], "provenance": "abstained",
                "grounded": False, "backend": "deterministic", "retrieval": r["method"], "top_score": r["top_score"]}

    # general / background knowledge -> ANSWER, clearly labelled as general (never a PEN-STACK result).
    if allow_llm:
        from pen_stack.web.llm import SYSTEM_GENERAL, _GENERAL_LABEL, _run_llm
        text, backend = _run_llm(
            f"USER: {msg}\n\nAnswer from general knowledge, clearly and at a graduate level. Do not present anything "
            f"as a PEN-STACK result.", SYSTEM_GENERAL)
        if text:
            return {"status": "general", "reply": _GENERAL_LABEL + "\n\n" + text.strip(), "sources": [],
                    "provenance": "general", "grounded": False, "backend": backend, "retrieval": r["method"],
                    "top_score": r["top_score"]}
    from pen_stack.web.llm import _GENERAL_LABEL
    return {"status": "general", "reply": _GENERAL_LABEL + "\n\n" + _GENERAL_NO_LLM, "sources": [],
            "provenance": "general", "grounded": False, "backend": "deterministic", "retrieval": r["method"],
            "top_score": r["top_score"]}
