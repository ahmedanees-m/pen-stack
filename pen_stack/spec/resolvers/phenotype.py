"""Phenotype / disease-goal resolver (A-WS2): free text -> MONDO. Ids verified against EBI OLS."""
from __future__ import annotations

from pen_stack.spec.writespec import Resolved

# (MONDO id, canonical label) - verified live before commit
_PHENO: dict[str, tuple[str, str]] = {
    "sickle cell disease": ("MONDO:0011382", "sickle cell disease"),
    "sickle cell": ("MONDO:0011382", "sickle cell disease"), "scd": ("MONDO:0011382", "sickle cell disease"),
    "beta thalassemia": ("MONDO:0019402", "beta thalassemia"),
    "beta-thalassemia": ("MONDO:0019402", "beta thalassemia"),
    "duchenne muscular dystrophy": ("MONDO:0010679", "Duchenne muscular dystrophy"),
    "duchenne": ("MONDO:0010679", "Duchenne muscular dystrophy"), "dmd": ("MONDO:0010679", "Duchenne muscular dystrophy"),
    "cystic fibrosis": ("MONDO:0009061", "cystic fibrosis"), "cf": ("MONDO:0009061", "cystic fibrosis"),
    "rett syndrome": ("MONDO:0010726", "Rett syndrome"), "rett": ("MONDO:0010726", "Rett syndrome"),
    "hemophilia b": ("MONDO:0010604", "hemophilia B"),
    "hemophilia a": ("MONDO:0010602", "hemophilia A"),
    "leber congenital amaurosis 10": ("MONDO:0012723", "Leber congenital amaurosis 10"),
    "lca10": ("MONDO:0012723", "Leber congenital amaurosis 10"),
}


def resolve_phenotype(text: str) -> Resolved:
    """Resolve a disease / phenotype goal to MONDO; unrecognized stays null (never invented)."""
    if not text:
        return Resolved(text=text, ontology="MONDO", note="empty")
    key = text.strip().lower()
    hit = _PHENO.get(key)
    if hit is None:
        for k, v in _PHENO.items():
            if k in key or key in k:
                hit = v
                break
    if hit is None:
        return Resolved(text=text, ontology="MONDO", confidence=None, note="unresolved phenotype term")
    mid, label = hit
    return Resolved(text=text, id=mid, label=label, ontology="MONDO", confidence=0.9)
