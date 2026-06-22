"""Sequence-feature resolver (A-WS2): free text -> Sequence Ontology role. Ids verified against EBI OLS."""
from __future__ import annotations

from pen_stack.spec.writespec import Resolved

# (SO id, canonical label) - verified live before commit
_FEATURES: dict[str, tuple[str, str]] = {
    "promoter": ("SO:0000167", "promoter"),
    "cds": ("SO:0000316", "CDS"), "coding sequence": ("SO:0000316", "CDS"), "orf": ("SO:0000316", "CDS"),
    "polya": ("SO:0000551", "polyA_signal_sequence"), "poly-a": ("SO:0000551", "polyA_signal_sequence"),
    "polyadenylation signal": ("SO:0000551", "polyA_signal_sequence"), "pa": ("SO:0000551", "polyA_signal_sequence"),
    "insulator": ("SO:0000627", "insulator"),
    "enhancer": ("SO:0000165", "enhancer"),
    "terminator": ("SO:0000141", "terminator"),
    "5'utr": ("SO:0000204", "five_prime_UTR"), "5utr": ("SO:0000204", "five_prime_UTR"),
    "3'utr": ("SO:0000205", "three_prime_UTR"), "3utr": ("SO:0000205", "three_prime_UTR"),
    "ires": ("SO:0000139", "ribosome_entry_site"), "ribosome entry site": ("SO:0000139", "ribosome_entry_site"),
    "gene": ("SO:0000704", "gene"),
}


def resolve_feature(text: str) -> Resolved:
    """Resolve a sequence-feature term to a Sequence-Ontology role; unrecognized stays null."""
    if not text:
        return Resolved(text=text, ontology="SO", note="empty")
    key = text.strip().lower()
    hit = _FEATURES.get(key)
    if hit is None:
        for k, v in _FEATURES.items():
            if k in key:
                hit = v
                break
    if hit is None:
        return Resolved(text=text, ontology="SO", confidence=None, note="unresolved feature term")
    sid, label = hit
    return Resolved(text=text, id=sid, label=label, ontology="SO", confidence=0.9)
