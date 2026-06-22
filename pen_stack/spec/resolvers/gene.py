"""Gene resolver (A-WS2): free text -> HGNC symbol, grounded against the writable-genome atlas.

Wraps :func:`pen_stack.planner.optimize.resolve_gene` (which maps safe-harbour nicknames such as AAVS1 ->
PPP1R12C) and validates against the atlas gene-coordinate table: a symbol the atlas knows is high-confidence; an
unknown but plausible symbol is a low-confidence, explicitly-unvalidated pass-through; a jargon / non-gene token
stays unresolved (id=None). Nothing is invented.
"""
from __future__ import annotations

import re

from pen_stack.spec.writespec import Resolved

_SYMBOL = re.compile(r"^[A-Z][A-Z0-9-]{1,9}$")
# tokens that look like a gene symbol but are not one (vehicle / form / jargon abbreviations + a few stop words)
_STOP = {"DNA", "RNA", "MRNA", "AAV", "LNP", "HSV", "CAR", "RNP", "PCR", "WT", "KO", "KI", "ITR", "PAM", "GFP",
         "RFP", "YFP", "BFP", "THE", "AND", "FOR", "WITH", "INTO", "GENE", "CELL", "CELLS", "DOX", "USA"}
_NICKNAMES = {"AAVS1", "CCR5", "ROSA26", "CLYBL", "HPRT1"}


def resolve_gene(text: str) -> Resolved:
    """Resolve a gene symbol or safe-harbour nickname to its canonical HGNC symbol, grounded against the atlas."""
    if not text:
        return Resolved(text=text, ontology="HGNC", note="empty")
    sym = text.strip().upper()
    if sym in _STOP:
        return Resolved(text=text, ontology="HGNC", confidence=None, note="not a gene (jargon / stop token)")
    canon = sym
    in_atlas = False
    try:
        from pen_stack.planner.optimize import gene_region, resolve_gene as _rg
        canon = (_rg(sym) or sym).upper()
        in_atlas = gene_region(canon) is not None
    except Exception: # noqa: BLE001
        canon = sym
    if not _SYMBOL.match(canon):
        return Resolved(text=text, ontology="HGNC", confidence=None, note="unresolved (not a gene-symbol token)")
    if in_atlas:
        note = f"safe-harbour nickname -> {canon}" if (sym in _NICKNAMES and canon != sym) else "in writable-genome atlas"
        return Resolved(text=text, id=canon, label=canon, ontology="HGNC", confidence=0.95, note=note)
    # plausible but unknown to the atlas: a low-confidence pass-through, explicitly flagged unvalidated
    return Resolved(text=text, id=canon, label=canon, ontology="HGNC", confidence=0.4,
                    note="symbol not confirmed against the writable-genome atlas; unvalidated (reachability checked downstream)")
