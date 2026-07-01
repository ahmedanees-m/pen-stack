"""CAST (CRISPR-associated transposase) off-target path (PEN-OFFTGT v2, O-WS5) — NEW.

CAST off-target is two mechanisms, and their balance is system-dependent:
  * **guide-directed** — integration at genomic sites matching the crRNA spacer (a sequence-match scan; the
    transposon inserts a fixed distance downstream of the protospacer). Enumerated genome-wide on the VM (or
    replayed from cache); abstains for a novel spacer.
  * **guide-INDEPENDENT untargeted transposition** — the Tn7-like machinery (TnsB/TnsC/TniQ) inserting without the
    CRISPR effector. This is the DISTINCTIVE, dominant off-target mode for **Type V-K** (ShCAST) and is largely
    absent in **Type I-F** (VchCAST). It is reported as a per-system documented property (`cast_systems.yaml`),
    with DOIs — NOT a genome-wide prediction.

Status: **mechanism_based_unvalidated** (no genome-wide unbiased CELLULAR off-target assay exists for CAST). The
confirming assay is transposon insertion-site sequencing. Never fabricates a validated metric.
"""
from __future__ import annotations

from functools import lru_cache

from pen_stack.wgenome.offtarget_enumerate import DEFAULT_MAX_MISMATCH, enumerate_motif

_STATUS = "mechanism_based_unvalidated"
_ALIAS = {"shcast": "ShCAST", "vchcast": "VchCAST", "evocast": "evoCAST",
          "cast": "ShCAST", "cast_vk": "ShCAST", "cast_v-k": "ShCAST", "cast_if": "VchCAST",
          "type_v-k": "ShCAST", "type_i-f": "VchCAST", "cas12k": "ShCAST"}


@lru_cache(maxsize=1)
def cast_systems() -> dict:
    """The curated CAST system table (per-system untargeted-transposition properties + DOIs), or {} when absent."""
    try:
        import yaml

        from pen_stack._resources import resource
        return yaml.safe_load(resource("data/curated/cast_systems.yaml").read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def resolve_cast_system(name: str) -> str | None:
    sysd = cast_systems().get("systems", {})
    n = (name or "").strip()
    if n in sysd:
        return n
    return _ALIAS.get(n.lower())


def nominate_cast(system: str = "ShCAST", spacer: str | None = None,
                  max_mismatch: int = DEFAULT_MAX_MISMATCH) -> dict:
    """CAST off-target nomination: the guide-independent untargeted-transposition background (per-system documented
    property) PLUS guide-directed enumeration for a supplied spacer (genome-wide, replayed/abstained). Never
    fabricates sites or a validated metric; status is mechanism_based_unvalidated."""
    tbl = cast_systems()
    key = resolve_cast_system(system) or "ShCAST"
    rec = (tbl.get("systems") or {}).get(key, {})
    if not rec:
        return {"family": "cast", "available": False, "abstain": True, "status": _STATUS,
                "note": f"no curated CAST system {system!r}; known: {sorted((tbl.get('systems') or {}))}"}

    untargeted = {
        "mode": "guide-independent untargeted transposition (TnsB/TnsC/TniQ, no CRISPR effector)",
        "tier": rec.get("untargeted_transposition"),
        "guide_independent": rec.get("guide_independent"),
        "at_biased": rec.get("at_biased_untargeted"),
        "cast_type": rec.get("cast_type"),
        "fidelity_note": rec.get("on_target_fidelity_note"),
        "dois": rec.get("dois", []),
        "note": ("the DISTINCTIVE CAST off-target mode: Type V-K (ShCAST) shows HIGH guide-independent, AT-biased "
                 "untargeted transposition; Type I-F (VchCAST) is high-fidelity (low untargeted). A documented "
                 "per-system property, NOT a genome-wide prediction."),
    }

    # guide-directed: a spacer-match genome scan (enumerated on the VM; replayed from cache or abstains).
    guided = None
    if spacer:
        enum = enumerate_motif(f"CAST_{key}_{spacer.upper()}")
        if enum.get("available"):
            sites = enum["sites"]
            n_on = sum(1 for s in sites if s["n_mismatch"] == 0)
            guided = {"mode": "guide-directed (crRNA spacer match)", "available": True,
                      "n_sites_genome_wide": len(sites), "n_on_target": n_on,
                      "n_offtargets": len(sites) - n_on, "source": enum["source"],
                      "sites": sorted(sites, key=lambda s: s["n_mismatch"])[:50],
                      "note": "genomic sites matching the crRNA spacer; the transposon inserts a fixed distance "
                              "downstream. Ranked by mismatch (no CRISOT — that is a Cas9-nuclease model)."}
        else:
            guided = {"mode": "guide-directed (crRNA spacer match)", "available": False, "abstain": True,
                      "note": enum["note"], "cached_motifs": enum.get("cached_motifs", [])}

    return {"family": "cast", "system": key, "cast_type": rec.get("cast_type"), "available": True, "abstain": False,
            "status": _STATUS, "untargeted_background": untargeted, "guide_directed": guided,
            "confirm_assay": tbl.get("confirm_assay"),
            "method": ("CAST off-target = guide-directed spacer-match enumeration (genome-wide, VM) + the "
                       "guide-independent untargeted-transposition background (documented per-system property). "
                       "No genome-wide unbiased cellular assay exists -> mechanism-based, unvalidated."),
            "honesty": "CANDIDATES + a documented untargeted-transposition risk; NOT a clearance and NOT a "
                       "validated genome-wide predictor. Confirm by transposon insertion-site sequencing.",
            "nomination_is_not_clearance": True}
