"""The WriteSpec intent layer (v6.14, Stage A).

A typed, ontology-backed, machine-checkable representation of a genome-writing request (``WriteRequest``, an
SBOL3 profile), a grounded prose-to-spec extractor that labels every inference and never fabricates intent, and a
feasibility (satisfiability) check. This is the agentic front-end: one contract every downstream stage consumes.
"""
from __future__ import annotations

from pen_stack.spec.writespec import (
    CargoComponent,
    Constraints,
    Resolved,
    Target,
    WriteRequest,
    WRITE_TYPES,
)

__all__ = ["WriteRequest", "CargoComponent", "Target", "Constraints", "Resolved", "WRITE_TYPES"]
