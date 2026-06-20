"""Build the world-model knowledge graph from the v4.0 curated tables (v4.5, WS-G).

Parity-first (v4.5 risk register): the graph is assembled from the SAME validated sources the v4.0 code joins
, the WT-KB writer families, the delivery-vehicle palette, the write-type taxonomy, the DOI-validated GSH
loci, the documented writer panel, and the cell-type coverage cards, so its edges reproduce the existing
table joins (asserted by the parity test) before any multi-hop extension. Every edge is typed by evidence
kind and carries provenance + scope. Nothing here calls a network or a model; it is deterministic + CI-safe.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource
from pen_stack.graph.schema import Edge, Graph, Node

# writer output form (DNA cargo / RNP) per family, the same map the rule evaluators use (parity).
_WRITER_FORM = {"bridge_IS110": "DNA", "seek_IS1111": "DNA", "CAST_VK": "DNA", "serine_integrase": "DNA",
                "PE_integrase": "DNA", "Cas9": "RNP", "Cas12a": "RNP", "TnpB_Fanzor": "RNP"}
# tier-1 reprogrammable families are near-universal at the locus level (crosslink scope: locus-level reach).
_TIER1 = {"bridge_IS110", "seek_IS1111", "Cas9", "Cas12a"}


def _yaml(path: str) -> dict:
    return yaml.safe_load(resource(path).read_text(encoding="utf-8"))


def _lst(v) -> list:
    """Coerce a possibly-numpy-array / None cell to a plain list (avoids ambiguous-truthiness)."""
    if v is None:
        return []
    try:
        return [x for x in v]
    except TypeError:
        return [v]


@lru_cache(maxsize=1)
def build_graph() -> Graph:
    g = Graph()
    import pandas as pd

    # ---- writer nodes (WT-KB families) ---------------------------------------------------------
    wtkb = pd.read_parquet(resource("pen_stack/atlas/wtkb.parquet"))
    for _, w in wtkb.iterrows():
        fam = str(w["family"])
        g.add_node(Node(id=f"writer:{fam}", type="writer", props={
            "family": fam, "mechanism_bucket": w.get("mechanism_bucket"),
            "output_form": _WRITER_FORM.get(fam), "cargo_capacity_bp": int(w["cargo_capacity_bp"])
            if pd.notna(w.get("cargo_capacity_bp")) else None,
            "reachability_tier": w.get("reachability_tier"), "dsb_free": bool(w.get("dsb_free")),
            "confidence": w.get("confidence"), "dois": _lst(w.get("key_dois"))}))

    # ---- vehicle + cargo-form nodes (delivery palette) -----------------------------------------
    veh = _yaml("configs/delivery_vehicles.yaml")["vehicles"]
    for form in ("DNA", "mRNA", "RNP"):
        g.add_node(Node(id=f"cargo:{form}", type="cargo", props={"form": form}))
    for name, v in veh.items():
        g.add_node(Node(id=f"vehicle:{name}", type="vehicle", props={
            "cargo_capacity_bp": v.get("cargo_capacity_bp"), "integrating": v.get("integrating"),
            "compatible_cargo_form": v.get("compatible_cargo_form", []), "dois": v.get("dois", [])}))
        for form in v.get("compatible_cargo_form", []):
            g.add_edge(Edge(f"vehicle:{name}", f"cargo:{form}", "carries", "curated",
                            scope="documented vehicle cargo-form", provenance={"source": "delivery_vehicles.yaml",
                            "doi": v.get("dois", [])}))

    # ---- write-type nodes ----------------------------------------------------------------------
    wts = _yaml("configs/write_types.yaml")["write_types"]
    for wt, spec in wts.items():
        g.add_node(Node(id=f"write_type:{wt}", type="write_type",
                        props={"status": spec.get("status"), "writer_classes": spec.get("writer_classes", [])}))

    # ---- cell-type nodes (coverage cards) ------------------------------------------------------
    cts = _yaml("configs/cell_types.yaml")["cell_types"]
    for ct, card in cts.items():
        g.add_node(Node(id=f"cell_type:{ct}", type="cell_type", props={
            "tier": card.get("tier"), "ontology": card.get("efo") or card.get("ontology"),
            "coverage": card.get("coverage"), "tracks": card.get("tracks", []), "note": card.get("note")}))

    # ---- locus nodes (DOI-validated GSH) -------------------------------------------------------
    gsh = _yaml("configs/gsh_validated_heldout.yaml")["gsh"]
    for loc in gsh:
        g.add_node(Node(id=f"locus:{loc['name']}", type="locus", props={
            "tier": loc.get("tier"), "anchor_gene": loc.get("anchor_gene") or loc.get("anchor_gene_note"),
            "doi": loc.get("doi")}))

    # ---- outcome nodes (documented writes) -----------------------------------------------------
    panel = pd.read_csv(resource("data/writer_panel.csv"))

    # ---- EDGES ---------------------------------------------------------------------------------
    writers = [f"writer:{f}" for f in wtkb["family"].astype(str)]
    # writer -deliverable_by-> vehicle (cargo-form compatible) - PARITY with the v3.3 delivery rule
    for wid in writers:
        form = g.nodes[wid].props["output_form"]
        for name, v in veh.items():
            if form in v.get("compatible_cargo_form", []):
                g.add_edge(Edge(wid, f"vehicle:{name}", "deliverable_by", "curated",
                                scope="cargo-form compatibility (not tropism)",
                                provenance={"source": "delivery rule cargo_form_compatible"}))
    # writer -performs-> write_type (writer_classes membership)
    _CLASS = {"bridge_IS110": "bridge", "seek_IS1111": "bridge", "CAST_VK": "cast",
              "serine_integrase": "serine_integrase", "PE_integrase": "pe_integrase"}
    for wid in writers:
        fam = g.nodes[wid].props["family"]
        for wt, spec in wts.items():
            classes = spec.get("writer_classes", [])
            if "any" in classes or _CLASS.get(fam) in classes:
                g.add_edge(Edge(wid, f"write_type:{wt}", "performs", "curated",
                                scope=spec.get("status"), provenance={"source": "write_types.yaml"}))
    # writer -reaches-> locus (locus-level reachability; tier-1 near-universal) - predicted, scope-flagged
    for wid in writers:
        fam = g.nodes[wid].props["family"]
        if fam in _TIER1:
            for loc in gsh:
                g.add_edge(Edge(wid, f"locus:{loc['name']}", "reaches", "predicted", confidence=None,
                                scope="locus-level reachability (per-site element check is Planner work)",
                                provenance={"source": "crosslink reachability_tier (tier-1 reprogrammable)"}))
    # outcome -used_writer-> writer; outcome -observed_at-> locus (when the panel name maps to a GSH locus)
    gsh_names = {loc["name"] for loc in gsh}
    for _, r in panel.iterrows():
        oid = f"outcome:{r['name']}"
        g.add_node(Node(id=oid, type="outcome", props={"writer_family": str(r["family"]),
                    "cargo_bp": int(r["cargo_bp"]), "doi": str(r["doi"]), "note": str(r.get("note", ""))}))
        wid = f"writer:{r['family']}"
        if wid in g.nodes:
            g.add_edge(Edge(oid, wid, "used_writer", "measured", confidence=1.0,
                            scope="documented experimental write", provenance={"doi": str(r["doi"])}))
        for ln in gsh_names:
            if ln.lower() in str(r["name"]).lower():
                g.add_edge(Edge(oid, f"locus:{ln}", "observed_at", "measured",
                                scope="documented locus of the write", provenance={"doi": str(r["doi"])}))
    return g
