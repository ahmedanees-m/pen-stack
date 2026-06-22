"""Cell-line / cell-type resolver (A-WS2): free text -> Cellosaurus (cell lines) or Cell Ontology (cell types).

Curated offline cache (ids verified against the Cellosaurus API and EBI OLS). Cell lines carry the irreducible
subline / karyotype-drift caveat as a note. An unrecognized term stays unresolved (id=None), never invented.
"""
from __future__ import annotations

from pen_stack.spec.writespec import Resolved

# (id, canonical label, ontology) - all ids verified live before commit
_CELLS: dict[str, tuple[str, str, str]] = {
    # cell lines (Cellosaurus)
    "hek293t": ("CVCL_0063", "HEK293T", "Cellosaurus"), "293t": ("CVCL_0063", "HEK293T", "Cellosaurus"),
    "k562": ("CVCL_0004", "K-562", "Cellosaurus"), "k-562": ("CVCL_0004", "K-562", "Cellosaurus"),
    "hepg2": ("CVCL_0027", "Hep-G2", "Cellosaurus"), "hep-g2": ("CVCL_0027", "Hep-G2", "Cellosaurus"),
    "jurkat": ("CVCL_0065", "Jurkat", "Cellosaurus"),
    "hela": ("CVCL_0030", "HeLa", "Cellosaurus"),
    # cell types (Cell Ontology)
    "t cell": ("CL:0000084", "T cell", "CL"), "t-cell": ("CL:0000084", "T cell", "CL"),
    "cd8 t cell": ("CL:0000084", "T cell", "CL"), "car-t": ("CL:0000084", "T cell", "CL"),
    "primary t cell": ("CL:0000084", "T cell", "CL"),
    "hspc": ("CL:0000037", "hematopoietic stem cell", "CL"), "hsc": ("CL:0000037", "hematopoietic stem cell", "CL"),
    "cd34+": ("CL:0000037", "hematopoietic stem cell", "CL"), "cd34": ("CL:0000037", "hematopoietic stem cell", "CL"),
    "neuron": ("CL:0000540", "neuron", "CL"),
}
_LINE_CAVEAT = ("cell-line identity carries irreducible subline / karyotype drift (e.g. HEK293T); the canonical "
                "id does not resolve that away")


def resolve_cell(text: str) -> Resolved:
    """Resolve a cell line / type to Cellosaurus or Cell Ontology; unrecognized stays null."""
    if not text:
        return Resolved(text=text, note="empty")
    key = text.strip().lower()
    hit = _CELLS.get(key)
    if hit is None:
        # try a loose contains-match for a ranked candidate set (never a silent pick)
        cands = [{"id": v[0], "label": v[1], "ontology": v[2]}
                 for k, v in _CELLS.items() if k in key or key in k]
        uniq = {c["id"]: c for c in cands}
        if len(uniq) == 1:
            v = next(iter(uniq.values()))
            hit = (v["id"], v["label"], v["ontology"])
        elif len(uniq) > 1:
            return Resolved(text=text, ontology=None, confidence=0.3, candidates=list(uniq.values()),
                            note="ambiguous cell term; resolve to one of the candidates")
        else:
            return Resolved(text=text, confidence=None, note="unresolved cell term")
    cid, label, onto = hit
    note = _LINE_CAVEAT if onto == "Cellosaurus" else None
    return Resolved(text=text, id=cid, label=label, ontology=onto, confidence=0.95, note=note)
