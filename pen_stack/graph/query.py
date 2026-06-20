"""Multi-hop queries over the world-model graph (v4.5, WS-G / WS-BA).

An agent asks a design question as ONE grounded multi-hop traversal, "which writers reach locus L AND are
deliverable by a vehicle carrying their cargo form?", and every answer carries the **provenanced edges** it
traversed, so the result is grounded by construction (no-fabrication: the answer is the path, not free text).
The flat atlas/crosslink joins become graph *views* (`writers_for_locus`, `vehicles_for_writer`) for parity.
"""
from __future__ import annotations

from pen_stack.graph.build import build_graph
from pen_stack.graph.schema import Edge, Graph


def graph() -> Graph:
    return build_graph()


# ---- table-view parity queries (reproduce the v4.0 joins) --------------------------------------
def vehicles_for_writer(family: str, g: Graph | None = None) -> list[dict]:
    g = g or graph()
    wid = f"writer:{family}"
    return [{"vehicle": e.dst.split(":", 1)[1], "evidence": e.evidence, "scope": e.scope,
             "provenance": e.provenance} for e in g.out_edges(wid, "deliverable_by")]


def writers_for_locus(locus: str, g: Graph | None = None) -> list[dict]:
    g = g or graph()
    lid = f"locus:{locus}"
    out = []
    for w in g.nodes_of("writer"):
        for e in g.out_edges(w.id, "reaches"):
            if e.dst == lid:
                out.append({"writer": w.props["family"], "evidence": e.evidence, "scope": e.scope,
                            "provenance": e.provenance})
    return out


# ---- multi-hop design query (the headline graph capability) ------------------------------------
def writers_reaching_and_deliverable(locus: str, cargo_form: str | None = None,
                                     g: Graph | None = None) -> dict:
    """Multi-hop: writers that REACH `locus` AND are DELIVERABLE_BY a vehicle (optionally carrying
    `cargo_form`). Returns each answer with the full provenanced edge path (grounded answer)."""
    g = g or graph()
    lid = f"locus:{locus}"
    answers = []
    for w in g.nodes_of("writer"):
        # `cargo_form` selects writers whose OUTPUT form matches (e.g. a DNA-cargo writer); the
        # deliverable_by edges are already writer-form<->vehicle matched, so they give correct vehicles.
        if cargo_form is not None and w.props.get("output_form") != cargo_form:
            continue
        reach = [e for e in g.out_edges(w.id, "reaches") if e.dst == lid]
        if not reach:
            continue
        deliv = g.out_edges(w.id, "deliverable_by")
        if not deliv:
            continue
        path: list[Edge] = reach[:1] + deliv
        answers.append({
            "writer": w.props["family"], "output_form": w.props["output_form"],
            "vehicles": [e.dst.split(":", 1)[1] for e in deliv],
            "provenance_path": [{"src": e.src, "dst": e.dst, "etype": e.etype, "evidence": e.evidence,
                                 "scope": e.scope, "provenance": e.provenance} for e in path],
        })
    return {"locus": locus, "cargo_form": cargo_form, "n_answers": len(answers), "answers": answers,
            "grounded": all(a["provenance_path"] for a in answers),
            "no_fabrication": True, "note": "every answer is a provenanced multi-hop path over the graph"}


def outcomes_for_writer(family: str, g: Graph | None = None) -> list[dict]:
    """Documented (measured) writes performed by a writer family, the outcome edges."""
    g = g or graph()
    wid = f"writer:{family}"
    out = []
    for o in g.nodes_of("outcome"):
        for e in g.out_edges(o.id, "used_writer"):
            if e.dst == wid:
                out.append({"outcome": o.id.split(":", 1)[1], "cargo_bp": o.props["cargo_bp"],
                            "evidence": e.evidence, "doi": o.props["doi"]})
    return out
