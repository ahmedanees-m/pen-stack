"""Vocabulary resolvers (v6.14, Stage A, A-WS2): free text -> canonical ontology id.

Each resolver returns a :class:`pen_stack.spec.writespec.Resolved` with a canonical id + confidence + (when
ambiguous) a ranked candidate set, or a result with ``id=None`` for an unresolved term. Unresolved stays null:
a resolver never invents an id. All curated ids were verified against the live ontology services (Cellosaurus,
EBI OLS for SO / MONDO / CL / ChEBI) before they were committed.
"""
from __future__ import annotations

from pen_stack.spec.resolvers.cell import resolve_cell
from pen_stack.spec.resolvers.chem import resolve_chem
from pen_stack.spec.resolvers.feature import resolve_feature
from pen_stack.spec.resolvers.gene import resolve_gene
from pen_stack.spec.resolvers.locus import resolve_locus
from pen_stack.spec.resolvers.phenotype import resolve_phenotype

__all__ = ["resolve_gene", "resolve_cell", "resolve_feature", "resolve_phenotype", "resolve_chem", "resolve_locus"]
