"""Mechanistic simulation where computable (v5.9, WS-MECH).

Computes the consequences MECHANISM allows — steady-state cassette expression in a chromatin context — and
nothing more. Physics where computable; explicitly NOT a phenotype, NOT in-vivo behaviour, NOT durability beyond
the steady state. Assumptions and scope flags travel with every output.
"""
from __future__ import annotations

# documented relative promoter strengths (ordinal, dimensionless) — a curated default palette.
_PROMOTER_STRENGTH = {"ef1a": 1.0, "cag": 1.0, "cmv": 0.9, "pgk": 0.6, "ubc": 0.5,
                      "endogenous": 0.4, "minimal": 0.2}


def _promoter_strength(design: dict) -> float:
    p = design.get("promoter")
    if isinstance(p, dict) and p.get("strength") is not None:
        return float(p["strength"])
    if isinstance(p, str):
        return _PROMOTER_STRENGTH.get(p.strip().lower(), 0.5)
    return _PROMOTER_STRENGTH.get(str(p or "").strip().lower(), 0.5)


def cassette_expression(design: dict, chromatin_ctx: dict) -> dict:
    """Computable steady-state relative expression from an integrated cassette:
    promoter_strength x copy_number x accessibility. Physics where computable; NOT a phenotype."""
    p = _promoter_strength(design)
    cn = float(design.get("copy_number", 1) or 1)
    acc = float(chromatin_ctx.get("accessibility", 1.0) if chromatin_ctx else 1.0)
    rel = p * cn * acc
    return {
        "relative_expression": round(rel, 4),
        "units": "relative (dimensionless)",
        "assumptions": ["steady-state", "no silencing modeled", "linear copy scaling"],
        "scope_flags": ["episomal_durability_unknown", "phenotype_not_modeled"],
        "provenance": {"promoter_strength": p, "copy_number": cn, "accessibility": acc,
                       "source": "twin.mechanistic (closed-form steady state)"},
    }
