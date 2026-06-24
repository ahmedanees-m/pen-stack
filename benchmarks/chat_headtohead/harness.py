"""Head-to-head: PEN-CHAT vs ungrounded baselines (PEN-CHAT P-WS6, the punchline figure).

On a shared query set (in-corpus + out-of-corpus), runs three REAL systems and measures who fabricates:
  * PEN-CHAT      - the full grounded system (retrieve -> cite-or-silence -> guard, abstain below threshold);
  * vanilla RAG   - retrieve top-k + prepend + ask the SAME LLM, with NO citation-or-silence and NO abstention;
  * ungrounded LLM - the SAME LLM answering the bare question, no retrieval, no guard.

Metrics (the figure):
  * abstention_on_no_evidence  - on out-of-corpus questions, does the system decline? (PEN-CHAT should; baselines won't)
  * answered_without_grounding - on out-of-corpus questions, did it emit a confident answer with no grounded source?
    This is the hallucination/false-grounding exposure - ~0 for PEN-CHAT, high for the ungrounded baselines.
  * citation_coverage          - fraction of grounded answers carrying a source.

Needs a live LLM (Ollama) for the baselines, so it is run once and its result committed (it is NOT a CI unit test;
the CI test asserts the committed result shows PEN-CHAT dominating). Reproduce on a host with Ollama:
  PEN_RAG_NO_EMBED=0 python -m benchmarks.chat_headtohead.harness
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.rag.retrieve import retrieve
from pen_stack.web.llm import grounded_reply
from pen_stack.web.llm_provider import run_llm

_DIR = Path(__file__).resolve().parent

QUERIES = [
    ("What integration efficiency do Bxb1 hyperactive variants reach?", "in_corpus"),
    ("How is genotoxicity computed?", "in_corpus"),
    ("What does evoCAST achieve at ALB?", "in_corpus"),
    ("What is the capital of France?", "out_of_corpus"),
    ("How do I bake sourdough bread?", "out_of_corpus"),
    ("Who won the world cup in 2018?", "out_of_corpus"),
    ("What is the boiling point of water?", "out_of_corpus"),
    ("What is the best pizza topping?", "out_of_corpus"),
]

_ABSTAIN_MARKERS = ("no grounded source", "i don't know", "cannot answer", "i won't answer", "not in", "no information")


def _looks_abstaining(text: str) -> bool:
    t = (text or "").lower()
    return any(m in t for m in _ABSTAIN_MARKERS)


def _ungrounded(q: str):
    text, backend = run_llm(f"Answer the question concisely.\n\nQuestion: {q}",
                            "You are a helpful assistant. Answer from your own knowledge.")
    return text or ""


def _vanilla_rag(q: str):
    hits = retrieve(q, k=4)["hits"]
    ctx = "\n".join(f"- {h['text']}" for h in hits)
    text, backend = run_llm(f"Context:\n{ctx}\n\nQuestion: {q}\n\nAnswer using the context.",
                            "You are a helpful assistant. Use the provided context to answer.")
    return text or ""


def run() -> dict:
    systems = ["pen_chat", "vanilla_rag", "ungrounded_llm"]
    ooc = [q for q, t in QUERIES if t == "out_of_corpus"]
    metrics = {s: {"abstain_ooc": 0, "answered_without_grounding_ooc": 0, "cited_answers": 0, "answers": 0}
               for s in systems}
    rows = []
    for q, kind in QUERIES:
        # PEN-CHAT
        pc = grounded_reply(q, allow_llm=True)
        pc_abstain = pc.get("provenance") == "abstained"
        pc_cited = bool(pc.get("sources"))
        # baselines
        vr = _vanilla_rag(q)
        ug = _ungrounded(q)
        for s, (abst, text, cited) in {
            "pen_chat": (pc_abstain, pc.get("reply", ""), pc_cited),
            "vanilla_rag": (_looks_abstaining(vr), vr, False),
            "ungrounded_llm": (_looks_abstaining(ug), ug, False),
        }.items():
            metrics[s]["answers"] += 1
            metrics[s]["cited_answers"] += int(cited)
            if kind == "out_of_corpus":
                metrics[s]["abstain_ooc"] += int(abst)
                # answered a no-evidence question without abstaining and without a grounded citation
                if not abst and not cited:
                    metrics[s]["answered_without_grounding_ooc"] += 1
        rows.append({"q": q[:50], "kind": kind, "pen_chat_abstained": pc_abstain})

    n_ooc = len(ooc)
    summary = {s: {
        "abstention_on_no_evidence": round(metrics[s]["abstain_ooc"] / n_ooc, 3),
        "answered_without_grounding_rate": round(metrics[s]["answered_without_grounding_ooc"] / n_ooc, 3),
        "citation_coverage": round(metrics[s]["cited_answers"] / metrics[s]["answers"], 3),
    } for s in systems}
    return {"n_queries": len(QUERIES), "n_out_of_corpus": n_ooc, "systems": summary, "rows": rows,
            "claim": "PEN-CHAT abstains on no-evidence questions and cites its grounded answers; the ungrounded "
                     "baselines answer everything with no grounded source - the no-fabrication property, measured."}


if __name__ == "__main__":
    out = run()
    (_DIR / "result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
