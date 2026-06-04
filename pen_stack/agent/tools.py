"""PEN-STACK agent tools (Phase 3, Step 3.9) - the validated capabilities the agent may call.

Each tool wraps a *validated* module function and returns a JSON-serialisable, provenance-tagged result.
The agent may obtain numbers ONLY by calling these - never by free-text generation (the no-fabrication
guarantee, enforced by the eval harness). Schemas are the Ollama/OpenAI tool-calling format.
"""
from __future__ import annotations

from typing import Any


def writability(gene: str, ct: str = "k562") -> dict:
    """Most-writable locus near a gene (safety x durability)."""
    from pen_stack.atlas.crosslink import loci_for_gene
    g = loci_for_gene(gene, ct)
    if g.empty:
        return {"gene": gene, "ct": ct, "found": False, "tool": "wgenome.writability"}
    top = g.sort_values("writability", ascending=False).iloc[0]
    return {"gene": gene, "ct": ct, "found": True,
            "max_writability": round(float(top["writability"]), 4),
            "safety": round(float(top["safety"]), 4),
            "p_durable": round(float(top["p_durable"]), 4),
            "n_bins": int(len(g)), "tool": "wgenome.writability"}


def reachable_writers(gene: str, ct: str = "k562") -> dict:
    """Writer families that can reach a gene's most-writable locus."""
    from pen_stack.atlas.crosslink import loci_for_gene, writers_for_locus
    g = loci_for_gene(gene, ct)
    if g.empty:
        return {"gene": gene, "found": False, "tool": "atlas.crosslink"}
    top = g.sort_values("writability", ascending=False).iloc[0]
    w = writers_for_locus(top["chrom"], int(top["bin"]), ct)
    return {"gene": gene, "ct": ct, "found": True,
            "families": sorted(set(w["family"])) if not w.empty else [],
            "tool": "atlas.crosslink"}


def writer_axes(family: str) -> dict:
    """Measured axes for a writer family (cargo, deliverability, reachability, readiness)."""
    import pandas as pd

    from pen_stack.rag.index import _ATLAS
    atlas = pd.read_parquet(_ATLAS)
    sub = atlas[atlas["family"] == family]
    if sub.empty:
        return {"family": family, "found": False, "tool": "atlas.score"}
    core = sub[sub["entry_kind"] == "curated_core"]
    r = core.iloc[0] if len(core) else sub.iloc[0]
    return {"family": family, "found": True, "n_systems": int(len(sub)),
            "reachability_tier": r.get("reachability_tier"),
            "cargo_capacity_bp": (int(r["cargo_capacity_bp"]) if pd.notna(r.get("cargo_capacity_bp")) else None),
            "deliv_class": r.get("deliv_class"), "tool": "atlas.score"}


def plan_write(gene: str, intent: str, cargo_bp: int = 2000, ct: str = "k562") -> dict:
    """Full Write Planner: goal + edit_intent -> top ranked, traceable plan."""
    from pen_stack.planner.optimize import EditIntent
    from pen_stack.planner.pipeline import plan_write as _pw
    plans = _pw(gene, EditIntent(intent), cargo_bp, ct, k=1)
    return (plans[0] if plans else {"gene": gene, "found": False}) | {"tool": "planner.pipeline"}


def ask_literature(q: str) -> dict:
    """Grounded, cited literature answer (numbers still from tools)."""
    from pen_stack.rag.qa import answer
    a = answer(q)
    return {"answer": a["answer"], "citations": a["citations"], "tool": "rag.qa"}


def multiplex_translocation_risk(edits: list[dict]) -> dict:
    """Translocation-risk SCREEN for a multi-edit (2-5) plan: pairwise DSB-join risk across edits.

    Each edit: {name, family, chrom, pos, optional offtargets:[{chrom,pos,risk}]}. DSB-free recombinase
    writers contribute zero risk. A screen, not a calibrated predictor (WS-G1)."""
    from pen_stack.planner.multiplex import translocation_risk
    return {**translocation_risk(edits), "tool": "planner.multiplex"}


REGISTRY = {
    "writability": writability,
    "reachable_writers": reachable_writers,
    "writer_axes": writer_axes,
    "plan_write": plan_write,
    "ask_literature": ask_literature,
    "multiplex_translocation_risk": multiplex_translocation_risk,
}

# Ollama/OpenAI tool-calling schemas
SCHEMAS = [
    {"type": "function", "function": {
        "name": "writability", "description": "Most-writable locus near a gene (safety x durability).",
        "parameters": {"type": "object", "properties": {
            "gene": {"type": "string"}, "ct": {"type": "string", "enum": ["k562", "hepg2", "hspc"]}},
            "required": ["gene"]}}},
    {"type": "function", "function": {
        "name": "reachable_writers", "description": "Writer families that can reach a gene's best locus.",
        "parameters": {"type": "object", "properties": {
            "gene": {"type": "string"}, "ct": {"type": "string"}}, "required": ["gene"]}}},
    {"type": "function", "function": {
        "name": "writer_axes", "description": "Measured axes for a writer family.",
        "parameters": {"type": "object", "properties": {"family": {"type": "string"}},
                       "required": ["family"]}}},
    {"type": "function", "function": {
        "name": "plan_write", "description": "Full Write Planner: gene + edit_intent -> ranked plan.",
        "parameters": {"type": "object", "properties": {
            "gene": {"type": "string"},
            "intent": {"type": "string", "enum": ["safe_harbour_insertion", "knock_in_with_disruption",
                       "high_durability_insertion", "regulatory_excision", "repeat_excision"]},
            "cargo_bp": {"type": "integer"}, "ct": {"type": "string"}},
            "required": ["gene", "intent"]}}},
    {"type": "function", "function": {
        "name": "ask_literature", "description": "Grounded, cited literature answer.",
        "parameters": {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}}},
    {"type": "function", "function": {
        "name": "multiplex_translocation_risk",
        "description": "Translocation-risk screen for a multi-edit plan (pairwise DSB-join risk).",
        "parameters": {"type": "object", "properties": {
            "edits": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "family": {"type": "string"},
                "chrom": {"type": "string"}, "pos": {"type": "integer"}}}}},
            "required": ["edits"]}}},
]


def dispatch(name: str, args: dict) -> Any:
    """Execute a validated tool by name. Raises KeyError for unknown tools (never fabricates)."""
    if name not in REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    return REGISTRY[name](**args)
