"""Metric interpretation + PEN-STACK capability facts (v6.3, the explain/meta lanes).

Two grounded sources the hybrid co-scientist narrates over WITHOUT fabricating:
  * `metric_guide()` — curated interpretation cards (configs/metric_guide.yaml): what each engine number means,
    its scale/direction, reference bands, how it is computed, validation status. Used to EXPLAIN a value.
  * `pen_stack_facts()` — capability facts assembled from LIVE engine data (writer atlas coverage, the delivery
    palette, the immune axes, the known-unknowns) — so "how many enzymes / vectors / axes, how accurate" is
    answered from the system itself, not invented.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource


@lru_cache(maxsize=1)
def metric_guide() -> dict:
    return yaml.safe_load(resource("configs/metric_guide.yaml").read_text(encoding="utf-8"))


def guide_for(metric: str) -> dict | None:
    """The interpretation card for a metric name (immune axis / verdict field)."""
    return (metric_guide().get("metrics") or {}).get(metric)


def enrich_axes(axes: dict) -> dict:
    """Attach the interpretation card (meaning/scale/bands/computed/validation/reference) to each immune axis."""
    out = {}
    for name, a in (axes or {}).items():
        g = guide_for(name)
        out[name] = {**a, "guide": g} if g else a
    return out


@lru_cache(maxsize=1)
def pen_stack_facts() -> dict:
    """GROUNDED facts about what PEN-STACK covers + how it computes — assembled from live engine data, never
    hand-typed counts. Answers the 'meta' lane ('how many enzymes/vectors/axes, how is X computed, how accurate')."""
    facts: dict = {"disclaimer": (metric_guide() or {}).get("disclaimer")}

    # writer atlas coverage (enzymes / families) — from the committed atlas
    try:
        import pandas as pd

        from pen_stack import __file__ as _pkg
        from pathlib import Path
        atlas = pd.read_parquet(Path(_pkg).resolve().parents[0] / "atlas" / "atlas.parquet")
        facts["writers"] = {
            "systems": int(len(atlas)),
            "families": sorted(atlas["family"].astype(str).unique().tolist()),
            "n_families": int(atlas["family"].nunique()),
            "measured": int((atlas["confidence"] == "measured").sum()) if "confidence" in atlas.columns else None,
            "note": "writer = genome-writing enzyme system (integrases, recombinases, nucleases, transposases) on "
                    "common measured axes (cargo capacity, programmability, DSB-freeness, human-cell activity, "
                    "deliverability).",
        }
    except Exception:
        facts["writers"] = {"note": "writer atlas requires the committed atlas.parquet"}

    # delivery palette (vectors)
    try:
        from pen_stack.planner.delivery_vehicles import names as _vnames
        from pen_stack.planner.delivery_vehicles import vehicle as _veh
        vs = _vnames()
        viral = [v for v in vs if (_veh(v) or {}).get("class", "").lower().startswith("vir")
                 or any(k in v.lower() for k in ("aav", "lenti", "adeno", "hsv", "virus"))]
        facts["delivery"] = {
            "n_vehicles": len(vs), "vehicles": list(vs),
            "viral_like": viral, "nonviral_like": [v for v in vs if v not in viral],
            "note": "each vehicle carries documented cargo capacity, integration status, cargo-form compatibility "
                    "(DNA/mRNA/RNP) and an ordinal immune/safety prior; the planner picks compatible vehicles.",
        }
    except Exception:
        facts["delivery"] = {"note": "delivery palette in configs/delivery_vehicles.yaml"}

    # immune-risk axes (how immunogenicity is computed) + their guides
    axes = ["genotoxicity", "cd8_epitope", "innate", "preexisting_nab", "anti_peg"]
    facts["immunogenicity"] = {
        "n_axes": len(axes), "axes": axes,
        "never_collapsed": "the per-axis profile is never fused into one score (collapsed_score is None) — the "
                           "axes measure different mechanisms on different evidence.",
        "how": {a: (guide_for(a) or {}).get("computed") for a in axes},
        "validation": {a: (guide_for(a) or {}).get("validation") for a in axes},
    }

    # accuracy / honesty posture + the known-unknowns
    try:
        from pen_stack.agent.scope import load_registry
        kus = [{"id": e["id"], "title": e["title"]} for e in load_registry()]
    except Exception:
        kus = []
    facts["accuracy"] = {
        "posture": "every number is a tool-computed proxy with a stated scope; proxies are labelled "
                   "'mechanistic/population proxy — NOT outcome-validated'; the engine ABSTAINS or flags "
                   "out-of-scope rather than guess; nothing is fabricated.",
        "known_unknowns": kus,
        "what_is_NOT_predicted": "functional titer / % of normal, in-vivo response magnitude, long-term clinical "
                                 "durability, phenotype — these are measured clinical endpoints, never predicted.",
    }

    # v6.4 — live foundation-model oracles (which execute live + their latency class)
    try:
        from pen_stack.oracles.status import summary as _orsum
        facts["foundation_models"] = _orsum()
    except Exception:
        facts["foundation_models"] = {"note": "oracle execution map in configs/oracles/execution.yaml"}
    return facts
