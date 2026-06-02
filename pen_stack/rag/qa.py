"""Grounded, cited Q&A over the PEN-STACK platform (Phase 2, Step 2.8).

The front door for non-expert users. Contract (enforced by pen_stack.agent.guardrails):
  * clinical-directive questions are refused;
  * every *quantitative* claim is produced by a validated tool call (writability / atlas / cross-link),
    never guessed by the LLM — the answer's ``provenance`` block names the tool;
  * every factual claim carries a citation (DOIs from the curated atlas/WT-KB).

An optional LLM (Ollama/Qwen via litellm) only *phrases* the grounded facts; it is never the source of a
number or a citation. With no LLM available the deterministic tool+retrieval path still satisfies the
contract — that is the whole point.
"""
from __future__ import annotations

import re

from pen_stack.agent.guardrails import DISCLAIMER, enforce_grounded, out_of_scope
from pen_stack.rag.index import build_cards, retrieve

_GENE_RE = re.compile(r"\b([A-Z][A-Z0-9]{2,9})\b")          # crude gene-symbol cue (TRAC, CCR5, ...)
_FAMILY_HINTS = {
    "bridge": "bridge_IS110", "is110": "bridge_IS110", "iscro4": "bridge_IS110",
    "seek": "seek_IS1111", "is1111": "seek_IS1111", "cast": "CAST_VK",
    "integrase": "serine_integrase", "bxb1": "serine_integrase", "paste": "PE_integrase",
    "prime": "PE_integrase", "cas9": "Cas9", "cas12a": "Cas12a", "tnpb": "TnpB_Fanzor",
    "fanzor": "TnpB_Fanzor",
}
_WRITABLE_CUES = ("where", "writable", "safe harbour", "safe harbor", "insert", "insertion site", "locus")
# Standing citation for tool-derived writability claims: the Phase-1 Writable Genome atlas
# (TRIP durability supervision + clinical-CIS safety supervision).
_WRITABILITY_CITATIONS = ["10.1016/j.cell.2013.07.018"]   # Akhtar 2013 (TRIP) — durability supervision


def _family_in(question: str) -> str | None:
    q = question.lower()
    for cue, fam in _FAMILY_HINTS.items():
        if cue in q:
            return fam
    return None


def answer(question: str, ct: str = "k562") -> dict:
    refusal = out_of_scope(question)
    if refusal:
        return {"refused": True, "answer": refusal, "citations": [], "provenance": [],
                "disclaimer": DISCLAIMER}

    cards = build_cards()
    retrieved = retrieve(question, cards, k=3)
    citations = sorted({d for c in retrieved for d in c.citations})
    provenance: list[dict] = []
    parts: list[str] = []

    # --- numeric route 1: "where can I write / writable loci for GENE" -> writability tool ---
    if any(cue in question.lower() for cue in _WRITABLE_CUES):
        genes = [g for g in _GENE_RE.findall(question) if g not in {"PEN", "STACK", "DNA", "RNA"}]
        if genes:
            try:
                from pen_stack.atlas.crosslink import loci_for_gene
                g = loci_for_gene(genes[0], ct)
                if not g.empty:
                    w = float(g["writability"].max())
                    provenance.append({"tool": "crosslink.loci_for_gene",
                                       "args": {"gene": genes[0], "ct": ct},
                                       "result": {"max_writability": round(w, 3), "n_bins": int(len(g))}})
                    parts.append(f"For {genes[0]} in {ct}, the most writable bin scores "
                                 f"{w:.3f} (writability = safety x durability), across {len(g)} bins.")
                    citations = sorted(set(citations) | set(_WRITABILITY_CITATIONS))
            except FileNotFoundError:
                parts.append("(Writable-genome atlas not loaded; numeric writability unavailable.)")

    # --- numeric route 2: "which writer / tell me about FAMILY" -> atlas tool ---
    fam = _family_in(question)
    if fam:
        import pandas as pd

        from pen_stack.rag.index import _ATLAS
        adf = pd.read_parquet(_ATLAS)
        sub = adf[adf["family"] == fam]
        rep = sub[sub["entry_kind"] == "curated_core"]
        rep = rep.iloc[0] if len(rep) else sub.iloc[0]
        provenance.append({"tool": "atlas.query", "args": {"family": fam},
                           "result": {"n_systems": int(len(sub)),
                                      "reachability_tier": rep.get("reachability_tier"),
                                      "deliv_class": rep.get("deliv_class")}})
        parts.append(f"{fam}: {len(sub):,} catalogued systems; reachability {rep.get('reachability_tier')}; "
                     f"deliverability {rep.get('deliv_class')}; representative {rep['representative_system']}.")

    # --- factual route: retrieval-grounded summary (always cited) ---
    if retrieved:
        parts.append("Relevant atlas facts: " + " | ".join(c.text for c in retrieved[:2]))

    if not parts:
        parts.append("No grounded match in the atlas. Try naming a writer family or a target gene.")

    out = {"refused": False, "answer": " ".join(parts), "citations": citations,
           "provenance": provenance, "disclaimer": DISCLAIMER}
    return enforce_grounded(out)
