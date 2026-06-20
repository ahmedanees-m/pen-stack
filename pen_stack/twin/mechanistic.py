"""Mechanistic simulation where computable (v5.9 + v6.5 WS-EXPRESS).

Computes the consequences MECHANISM allows, steady-state cassette expression in a chromatin context, and
nothing more. Physics where computable; explicitly NOT a phenotype, NOT in-vivo behaviour, NOT durability beyond
the steady state. Assumptions and scope flags travel with every output.

v6.5: the promoter palette is now a comprehensive, literature-cited table (configs/expression/promoters.yaml,
~25 constitutive + tissue-specific promoters) and the cassette carries an MODIFIER profile (WPRE, intron,
polyA, Kozak, codon-optimization, CpG-silencing, configs/expression/modifiers.yaml). Modifier effects are
transgene-dependent PRIORS, so they are reported as a bounded uplift RANGE with wide uncertainty, never folded
into the [0,1] base score as a point estimate. Absolute titer / % of normal stays a known-unknown.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource

# legacy default keys kept for backward compatibility (pre-v6.5 designs used these names directly).
_LEGACY_STRENGTH = {"ef1a": 1.0, "cag": 1.0, "cmv": 0.9, "pgk": 0.6, "ubc": 0.5,
                    "endogenous": 0.4, "minimal": 0.2}


@lru_cache(maxsize=1)
def _palette() -> dict:
    """Flatten the comprehensive promoter palette (constitutive + tissue-specific) to {name: entry}."""
    try:
        cfg = yaml.safe_load(resource("configs/expression/promoters.yaml").read_text(encoding="utf-8"))
    except Exception: # noqa: BLE001 - config absent (shouldn't happen) -> legacy table only
        return {}
    out: dict = {}
    for group in ("constitutive", "tissue_specific"):
        for name, e in (cfg.get(group) or {}).items():
            out[name] = e
    out["_default"] = cfg.get("default_strength", 0.5)
    return out


@lru_cache(maxsize=1)
def _modifiers() -> dict:
    try:
        return yaml.safe_load(resource("configs/expression/modifiers.yaml").read_text(encoding="utf-8"))
    except Exception: # noqa: BLE001
        return {"modifiers": {}, "composition": {"max_total_uplift": 4.0}}


def promoter_info(name: str) -> dict:
    """The cited palette entry for a promoter (strength + context + assay + citation), or a default."""
    pal = _palette()
    key = str(name or "").strip().lower()
    if key in pal:
        return pal[key]
    if key in _LEGACY_STRENGTH:
        return {"strength": _LEGACY_STRENGTH[key], "context": "ubiquitous", "confidence": "legacy"}
    return {"strength": pal.get("_default", 0.5), "context": "unknown", "confidence": "default"}


def _promoter_strength(design: dict) -> tuple[float, dict]:
    p = design.get("promoter")
    if isinstance(p, dict) and p.get("strength") is not None:
        return float(p["strength"]), {"context": p.get("context", "supplied"), "confidence": "supplied"}
    name = p if isinstance(p, str) else str(p or "")
    info = promoter_info(name)
    return float(info.get("strength", 0.5)), info


def _modifier_profile(design: dict) -> dict:
    """A bounded modifier uplift RANGE from the cassette's cis-elements. NOT a point multiplier and NOT
    folded into the [0,1] base, modifier effects are transgene/context-dependent priors with wide uncertainty."""
    mods = _modifiers().get("modifiers", {})
    cap = float(_modifiers().get("composition", {}).get("max_total_uplift", 4.0))
    applied, hi = [], 1.0 # lower bound stays 1.0: a modifier may do nothing for THIS transgene
    for key, present in (("wpre", design.get("wpre")), ("intron", design.get("intron"))):
        if present and key in mods:
            hi *= float(mods[key].get("present_fold", [1.0, 1.0])[1])
            applied.append(key)
    if design.get("codon_optimized") and "codon_optimization" in mods:
        hi *= float(mods["codon_optimization"].get("optimized_fold", [1.0, 1.0])[1])
        applied.append("codon_optimization")
    cpg_flag = bool(design.get("high_cpg") or (design.get("cpg_oe") is not None and float(design.get("cpg_oe")) > 0.6))
    if cpg_flag:
        applied.append("cpg_silencing(down)")
    lo, hi = 1.0, round(min(hi, cap), 2)
    return {
        "applied": applied,
        "estimated_uplift_range": [round(lo, 2), round(hi, 2)],
        "direction_note": ("net uplift expected (transgene-dependent)" if hi > 1.0 else "no modifier signal"),
        "cpg_silencing_risk": bool(cpg_flag),
        "caveat": "modifier effects are transgene/cell/construct-dependent PRIORS (e.g. an intron is ~20x for one "
                  "transgene, ~3x for another), a bounded range, not a measured multiplier for THIS construct.",
        "source": "configs/expression/modifiers.yaml (literature priors)",
    }


def cassette_expression(design: dict, chromatin_ctx: dict) -> dict:
    """Computable steady-state RELATIVE expression from an integrated cassette: promoter_strength x copy_number x
    accessibility (base, [0,1]-relative), PLUS an bounded modifier uplift range. NOT a phenotype, NOT an
    absolute titer."""
    p, pinfo = _promoter_strength(design)
    cn = float(design.get("copy_number", 1) or 1)
    acc = float(chromatin_ctx.get("accessibility", 1.0) if chromatin_ctx else 1.0)
    rel = p * cn * acc
    flags = ["episomal_durability_unknown", "phenotype_not_modeled"]
    # context scope: a promoter that silences (CMV, SFFV in stem cells) is flagged, not silently trusted.
    if str(pinfo.get("context", "")).startswith("variable") or "SILENCE" in str(pinfo.get("note", "")).upper():
        flags.append("promoter_context_variable_or_silencing")
    return {
        "relative_expression": round(rel, 4),
        "units": "relative (dimensionless)",
        "modifier_profile": _modifier_profile(design),
        "assumptions": ["steady-state", "no silencing dynamics modeled", "linear copy scaling",
                        "promoter strength is an ordinal literature prior (context-dependent)"],
        "scope_flags": flags,
        "provenance": {"promoter_strength": p, "promoter_context": pinfo.get("context"),
                       "promoter_citation": pinfo.get("citation"), "copy_number": cn, "accessibility": acc,
                       "source": "twin.mechanistic (closed-form steady state + literature promoter palette v6.5)"},
    }
