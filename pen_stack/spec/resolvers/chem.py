"""Small-molecule resolver (A-WS2): free text (inducer / selection agent) -> ChEBI. Ids verified against EBI OLS."""
from __future__ import annotations

from pen_stack.spec.writespec import Resolved

# (ChEBI id, canonical label) - verified live before commit
_CHEM: dict[str, tuple[str, str]] = {
    "doxycycline": ("CHEBI:50845", "doxycycline"), "dox": ("CHEBI:50845", "doxycycline"),
    "tamoxifen": ("CHEBI:41774", "tamoxifen"),
    "4-hydroxytamoxifen": ("CHEBI:231618", "4-hydroxytamoxifen"), "4-oht": ("CHEBI:231618", "4-hydroxytamoxifen"),
    "afimoxifene": ("CHEBI:44616", "afimoxifene"),
    "rapamycin": ("CHEBI:9168", "sirolimus"), "sirolimus": ("CHEBI:9168", "sirolimus"),
    "puromycin": ("CHEBI:17939", "puromycin"),
    "blasticidin": ("CHEBI:15353", "blasticidin S"), "blasticidin s": ("CHEBI:15353", "blasticidin S"),
}


def resolve_chem(text: str) -> Resolved:
    """Resolve a small-molecule inducer / selection agent to ChEBI; unrecognized stays null."""
    if not text:
        return Resolved(text=text, ontology="ChEBI", note="empty")
    key = text.strip().lower()
    hit = _CHEM.get(key)
    if hit is None:
        for k, v in _CHEM.items():
            if k in key:
                hit = v
                break
    if hit is None:
        return Resolved(text=text, ontology="ChEBI", confidence=None, note="unresolved molecule term")
    cid, label = hit
    return Resolved(text=text, id=cid, label=label, ontology="ChEBI", confidence=0.9)
