"""Multi-hop queries over the world-model graph.

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


# common safe-harbour aliases not captured by the GSH name or its anchor gene (case-insensitive).
_LOCUS_ALIASES = {"rosa26": "hrosa26", "rosa-26": "hrosa26", "hipp11": "h11", "hipp-11": "h11"}


def _resolve_gsh_locus(query: str, g: Graph) -> str | None:
    """Resolve a user's locus query to a curated GSH node id, matching (case-insensitively) the GSH NAME, its
    ANCHOR GENE, or a common alias, so AAVS1, its anchor PPP1R12C, and ROSA26 (the curated node is hRosa26)
    all reach the same node. Returns the node id (``locus:<name>``) or None if it is not a curated safe harbour."""
    q = str(query or "").strip().lower()
    if not q:
        return None
    q = _LOCUS_ALIASES.get(q, q)
    for n in g.nodes_of("locus"):
        name = n.id.split(":", 1)[1]
        anchor = str(n.props.get("anchor_gene") or "")
        if q in {name.lower(), anchor.lower()}:
            return n.id
    return None


def _answer(w, reach_edges: list[Edge], deliv: list[Edge]) -> dict:
    path: list[Edge] = reach_edges[:1] + deliv
    return {
        "writer": w.props["family"], "output_form": w.props["output_form"],
        "vehicles": [e.dst.split(":", 1)[1] for e in deliv],
        "provenance_path": [{"src": e.src, "dst": e.dst, "etype": e.etype, "evidence": e.evidence,
                             "scope": e.scope, "provenance": e.provenance} for e in path],
    }


# ---- multi-hop design query (the headline graph capability) ------------------------------------
def writers_reaching_and_deliverable(locus: str, cargo_form: str | None = None,
                                     g: Graph | None = None) -> dict:
    """Multi-hop: writers that REACH `locus` AND are DELIVERABLE_BY a vehicle (optionally carrying
    `cargo_form`). Returns each answer with the full provenanced edge path (grounded answer).

    Locus resolution (v7.3.21, the graph only materialised curated safe-harbour nodes, so anything but their
    exact name returned nothing): a query is first resolved to a curated GSH node by name / anchor gene / alias.
    Failing that, if it resolves to a REAL gene, the answer is the tier-1 reprogrammable writers, which reach
    ANY locus at the locus level (the documented crosslink property), with a scope flag saying so and that it is
    NOT a curated safe harbour. A query that is neither returns a clean, explained empty result, never an error."""
    g = g or graph()
    gsh_id = _resolve_gsh_locus(locus, g)

    if gsh_id is not None:  # curated safe harbour: the existing grounded traversal
        resolved = gsh_id.split(":", 1)[1]
        answers = []
        for w in g.nodes_of("writer"):
            if cargo_form is not None and w.props.get("output_form") != cargo_form:
                continue
            reach = [e for e in g.out_edges(w.id, "reaches") if e.dst == gsh_id]
            deliv = g.out_edges(w.id, "deliverable_by")
            if reach and deliv:
                answers.append(_answer(w, reach, deliv))
        note = ("every answer is a provenanced multi-hop path over the graph"
                + (f"; '{locus}' resolved to curated safe harbour '{resolved}'" if resolved.lower() != str(locus).strip().lower() else ""))
        return {"locus": locus, "resolved_locus": resolved, "is_curated_safe_harbour": True,
                "cargo_form": cargo_form, "n_answers": len(answers), "answers": answers,
                "grounded": all(a["provenance_path"] for a in answers), "no_fabrication": True, "note": note}

    # not a curated GSH: does it resolve to a real gene? -> tier-1 reprogrammable writers reach ANY locus.
    resolved_gene = None
    try:
        from pen_stack.planner.optimize import gene_region, resolve_gene
        rg = resolve_gene(str(locus))
        resolved_gene = rg if gene_region(rg) else None
    except Exception:  # noqa: BLE001 - gene-coords absent (CI/offline) -> no fallback, clean empty
        resolved_gene = None

    if resolved_gene is None:
        return {"locus": locus, "resolved_locus": None, "is_curated_safe_harbour": False,
                "cargo_form": cargo_form, "n_answers": 0, "answers": [], "grounded": True, "no_fabrication": True,
                "note": (f"'{locus}' is neither a curated safe-harbour locus nor a resolvable gene symbol, no "
                         "grounded writer→locus→vehicle path (a clean empty result, not an error).")}

    # tier-1 = the writers the graph gives locus-level `reaches` edges (near-universal reprogrammable reach).
    tier1 = {e.src for e in g.edges if e.etype == "reaches"}
    answers = []
    for w in g.nodes_of("writer"):
        if w.id not in tier1:
            continue
        if cargo_form is not None and w.props.get("output_form") != cargo_form:
            continue
        deliv = g.out_edges(w.id, "deliverable_by")
        if not deliv:
            continue
        synth = Edge(w.id, f"locus:{resolved_gene}", "reaches", "predicted",
                     scope="locus-level reachability (per-site element check is Planner work); NOT a curated "
                           "safe-harbour node, tier-1 reprogrammable near-universal reach",
                     provenance={"source": "crosslink reachability_tier (tier-1 reprogrammable); locus resolved "
                                           "to a real gene, not a curated GSH, treat as a candidate, verify per-site"})
        answers.append(_answer(w, [synth], deliv))
    return {"locus": locus, "resolved_locus": resolved_gene, "is_curated_safe_harbour": False,
            "cargo_form": cargo_form, "n_answers": len(answers), "answers": answers,
            "grounded": all(a["provenance_path"] for a in answers), "no_fabrication": True,
            "note": (f"'{resolved_gene}' is not a curated safe harbour; these are the tier-1 reprogrammable writers, "
                     "which reach any locus at the locus level (a candidate, not a validated safe-harbour path, "
                     "per-site reachability + safety are the Planner / Guardian's job).")}


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
