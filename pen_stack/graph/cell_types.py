"""Cell-type coverage cards + cross-type OOD labelling + graceful degradation (v4.5, WS-CT).

Each cell type is a graph node carrying a **coverage card** (which data tracks exist). A score is only as
trustworthy as its coverage: a partial-coverage cell type **degrades gracefully** (its confidence is capped),
and a score computed in one cell type but *queried* for another is **OOD-labelled**, the v3.2 finding that
chromatin marks are conserved, so cross-cell-type context is intrinsically weak/heuristic, not a guarantee.
Tier-B cell types are a documented roadmap, never silently extrapolated.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource

# graceful-degradation policy: the maximum trustworthy confidence a cell type's coverage supports.
_MAX_CONF = {"full": 1.0, "partial": 0.6, "none": 0.0}


@lru_cache(maxsize=1)
def _cfg() -> dict:
    return yaml.safe_load(resource("configs/cell_types.yaml").read_text(encoding="utf-8"))


def coverage_card(cell_type: str) -> dict | None:
    return _cfg()["cell_types"].get(cell_type)


def cell_types() -> list[str]:
    return list(_cfg()["cell_types"])


def tier_b_roadmap() -> list[dict]:
    return list(_cfg().get("tier_b_roadmap", []))


def degrade(raw_confidence: float, cell_type: str) -> dict:
    """Cap a confidence by the cell type's coverage (graceful degradation). Returns the degraded value +
    whether degradation was applied + the coverage label, never silently inflates."""
    card = coverage_card(cell_type) or {}
    cov = card.get("coverage", "none")
    cap = _MAX_CONF.get(cov, 0.0)
    degraded = min(float(raw_confidence), cap)
    return {"cell_type": cell_type, "coverage": cov, "raw_confidence": round(float(raw_confidence), 4),
            "confidence": round(degraded, 4), "degraded": degraded < float(raw_confidence),
            "cap": cap, "tracks": card.get("tracks", [])}


def cross_cell_type_ood(query_cell_type: str, scored_in_cell_type: str) -> dict:
    """Label a cross-cell-type query as OOD/extrapolating (v3.2: cross-type signal is weak, heuristic).
    Same cell type = in-distribution; different = extrapolating."""
    ood = query_cell_type != scored_in_cell_type
    return {"query_cell_type": query_cell_type, "scored_in_cell_type": scored_in_cell_type,
            "ood": ood,
            "label": "extrapolating (cross-cell-type; v3.2: chromatin conserved -> weak heuristic)"
                     if ood else "in-distribution",
            "note": "cross-cell-type transfer is a heuristic signal, not a guarantee; reported, not hidden"}
