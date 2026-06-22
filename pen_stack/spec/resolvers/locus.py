"""Locus resolver (A-WS2): free text (gene / safe-harbour) -> GRCh38 chromosome, reusing the atlas resolver.

Wraps :func:`pen_stack.planner.optimize.gene_region` (with the safe-harbour-aware ``resolve_gene``). An
unresolvable term stays null. The coordinate granularity is the chromosome the gene body lies on (the full
base-range comes from the atlas when a downstream reachability query is run).
"""
from __future__ import annotations

from pen_stack.spec.writespec import Resolved


def resolve_locus(text: str) -> Resolved:
    """Resolve a gene / safe-harbour locus to its GRCh38 chromosome; unrecognized stays null."""
    if not text:
        return Resolved(text=text, ontology="GRCh38", note="empty")
    sym = text.strip().upper()
    reg = None
    try:
        from pen_stack.planner.optimize import gene_region, resolve_gene
        reg = gene_region(resolve_gene(sym))  # -> (chrom, start, end) | None
    except Exception: # noqa: BLE001
        reg = None
    if not reg:
        return Resolved(text=text, ontology="GRCh38", confidence=None, note="unresolved locus")
    chrom, start, end = reg
    chrom = chrom if str(chrom).startswith("chr") else f"chr{chrom}"
    cid = f"{chrom}:{int(start)}-{int(end)}"
    return Resolved(text=text, id=cid, label=cid, ontology="GRCh38", confidence=0.85,
                    note="GRCh38 gene-body region (+/- flank) from the atlas")
