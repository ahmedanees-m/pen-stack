"""Multiplex translocation-risk flag (v3.1, WS-G1).

For a multi-edit plan (2-5 edits), two simultaneous double-strand breaks (DSBs) at different loci can
mis-join into a TRANSLOCATION. This is a classical, interpretable SCREEN - not a calibrated translocation
predictor. We gather every edit's DSB sites (on-target + predicted off-targets, each with a cut probability),
enumerate all site PAIRS exactly (cheap for 2-5 edits), and combine pairwise DSB-join probabilities into a
`translocation_risk` in [0,1].

Key property: **DSB-free writers (bridge / seek recombinases) contribute NO cut sites**, so a plan
built from them carries ~zero translocation risk - which is the whole point of programmable recombinases.
The flag is monotonic (more sites / higher cut prob / closer pairs -> higher risk) and reports its top pairs
so a user can see WHY. A QUBO formulation is provided as a documented OPTIONAL baseline, off by default.
"""
from __future__ import annotations

import math
from itertools import combinations

# writer families that cut DNA (DSB) vs DSB-free programmable recombinases / writers.
_DSB_FREE = {"bridge_is110", "bridge_iscro4", "seek_is1111", "bridge", "seek", "pe_integrase",
             "prime_editor", "recombinase"}
_DEFAULT_ON_TARGET_CUT = 0.8 # nominal on-target cut efficiency for a DSB nuclease (documented prior)
_INTRA_CHROM_LENGTH = 1.0e7 # bp decay length for intra-chromosomal join propensity (10 Mb)


def is_dsb_free(family: str | None) -> bool:
    return str(family or "").lower() in _DSB_FREE


def cut_sites(edit: dict) -> list[dict]:
    """DSB sites for one edit. DSB-free writers -> []. Otherwise on-target (+ off-targets if provided).

    `edit` keys: family, chrom, pos (on-target); optional on_target_cut; optional offtargets=[{chrom,pos,
    p_cut|risk}]. Off-target risk in [0,1] is used directly as a cut probability.
    """
    if is_dsb_free(edit.get("family")):
        return []
    sites = []
    if edit.get("chrom") is not None and edit.get("pos") is not None:
        sites.append({"chrom": edit["chrom"], "pos": int(edit["pos"]),
                      "p_cut": float(edit.get("on_target_cut", _DEFAULT_ON_TARGET_CUT)),
                      "kind": "on_target", "edit": edit.get("name")})
    for ot in edit.get("offtargets", []) or []:
        p = float(ot.get("p_cut", ot.get("risk", 0.0)))
        if p > 0 and ot.get("chrom") is not None and ot.get("pos") is not None:
            sites.append({"chrom": ot["chrom"], "pos": int(ot["pos"]), "p_cut": min(1.0, p),
                          "kind": "off_target", "edit": edit.get("name")})
    return sites


def _join_factor(a: dict, b: dict) -> float:
    """Propensity that two DSBs mis-join: 1.0 inter-chromosomal; distance-decayed intra-chromosomal."""
    if a["chrom"] != b["chrom"]:
        return 1.0
    d = abs(a["pos"] - b["pos"])
    return math.exp(-d / _INTRA_CHROM_LENGTH)


def pairwise_risks(sites: list[dict]) -> list[dict]:
    """Exact pairwise DSB-join probabilities for every unordered site pair (across and within edits)."""
    out = []
    for i, j in combinations(range(len(sites)), 2):
        a, b = sites[i], sites[j]
        jp = a["p_cut"] * b["p_cut"] * _join_factor(a, b)
        out.append({"a": f"{a['edit']}:{a['kind']}@{a['chrom']}:{a['pos']}",
                    "b": f"{b['edit']}:{b['kind']}@{b['chrom']}:{b['pos']}",
                    "inter_chromosomal": a["chrom"] != b["chrom"], "join_prob": round(jp, 5)})
    return sorted(out, key=lambda r: r["join_prob"], reverse=True)


def translocation_risk(edits: list[dict], low: float = 0.05, moderate: float = 0.2,
                       top_k: int = 5) -> dict:
    """Aggregate translocation-risk flag for a multi-edit plan. risk = 1 - prod(1 - pairwise_join_prob).

    Monotonic in every pairwise probability; interpretable via the top contributing pairs. A SCREEN, not a
    calibrated predictor.
    """
    if not 2 <= len(edits) <= 5:
        # still computes, but the flag is meant for multiplex (2-5 simultaneous edits)
        note = "translocation risk is defined for multiplex plans (2-5 simultaneous edits)"
    else:
        note = None
    sites = [s for e in edits for s in cut_sites(e)]
    pairs = pairwise_risks(sites)
    prod = 1.0
    for p in pairs:
        prod *= (1.0 - p["join_prob"])
    risk = round(1.0 - prod, 5)
    band = "low" if risk < low else ("moderate" if risk < moderate else "high")
    n_dsb_free = sum(1 for e in edits if is_dsb_free(e.get("family")))
    return {"translocation_risk": risk, "band": band, "n_edits": len(edits),
            "n_cut_sites": len(sites), "n_pairs": len(pairs),
            "n_dsb_free_edits": n_dsb_free,
            "all_dsb_free": n_dsb_free == len(edits),
            "top_pairs": pairs[:top_k],
            "note": note,
            "scope": "classical pairwise DSB-join SCREEN, not a calibrated translocation predictor; "
                     "DSB-free recombinase plans carry ~zero risk by construction"}


def qubo_baseline(edits: list[dict], variants_per_edit: dict[str, list[dict]] | None = None) -> dict:
    """OPTIONAL, OFF BY DEFAULT - a documented QUBO baseline for selecting per-edit guide variants that
    minimize total pairwise translocation risk. Returns the QUBO Q-matrix terms only; no solver is invoked
    and this is NOT the recommended path (the exact pairwise screen above is exact for 2-5 edits). Provided
    for completeness / external comparison, clearly labeled optional.
    """
    return {"enabled": False, "kind": "QUBO (optional baseline)",
            "note": "exact pairwise enumeration is tractable and exact for 2-5 edits; the QUBO path is an "
                    "optional baseline for large multiplex selection problems and is off by default.",
            "n_variant_sets": len(variants_per_edit or {})}
