"""Delivery safety<->efficacy balance over DOCUMENTED immune priors (v5.1, WS-IMMUNE).

Motivation (user, v5.1): "we should be able to give a good balance between safety and efficacy. AAV is
safe but neutralizing antibodies / pre-existing immunity will be there; lentivirus is highly efficacious at
integrating but its safety is bad." This module turns the per-vehicle ``immune_safety`` block in
configs/delivery_vehicles.yaml into a transparent, user-weightable ranking of the delivery palette.

THE HONESTY INVARIANT (unchanged across the program): the immune MAGNITUDE — how strongly a given patient or
construct will react in vivo — is a declared known-unknown (configs/known_unknowns.yaml: ``in_vivo_immunogenicity``)
and is NEVER predicted here. What this module exposes is strictly:

  * the DOCUMENTED, CITED, ORDINAL (low/moderate/high) literature priors per vehicle, and
  * a transparent ranking that combines those ordinal tiers under a USER-SUPPLIED safety<->efficacy weight.

The composite scores are an explicit, reproducible function of the documented tiers and the user's weight — not
a learned or predicted immunogenicity. Every profile carries the scope flag that the magnitude is out of scope,
plus the curated DOIs so the prior is auditable.
"""
from __future__ import annotations

from functools import lru_cache

from pen_stack.planner.delivery_vehicles import load_vehicles, names, vehicle

# Ordinal map for the documented qualitative tiers. Higher = more of the named property.
# For the BURDEN axes (immunity / NAb / innate / adaptive / genotoxicity) higher = worse (less safe);
# for the EFFICACY axis higher = better.
_TIER = {"low": 0.0, "moderate": 1.0, "high": 2.0}
# Two DISTINCT safety sub-axes are kept separate, never collapsed into one mean, because they are different
# KINDS of risk: immunogenicity is (largely) reversible and bears on eligibility/re-dosing, whereas
# genotoxicity (insertional mutagenesis) is a permanent, potentially oncogenic risk. This is exactly the
# tradeoff the v5.1 request is about ("AAV is safe but NAbs; LV is highly efficacious at integrating but its
# safety is bad") — so genotoxicity must be a first-class, separately-visible axis, not 1/5 of an average.
_IMMUNE_AXES = ("preexisting_immunity", "neutralizing_antibody", "innate_immune", "adaptive_immune")
_GENOTOX_AXIS = "genotoxicity"
# magnitude is NEVER predicted; this is the known-unknown the profile points back to.
_MAGNITUDE_SCOPE_ID = "in_vivo_immunogenicity"


def _tier(val) -> float | None:
    if val is None:
        return None
    return _TIER.get(str(val).strip().lower())


def safety_efficacy_profile(name: str) -> dict | None:
    """Documented safety<->efficacy profile for one vehicle, derived ONLY from its ``immune_safety`` block.

    Reports the ordinal tiers verbatim and THREE normalised sub-scores (1 = best):
      * ``immune_score``   = 1 - mean(immune-burden axes)/2  (1 = least immunogenic)
      * ``genotox_score``  = 1 - genotoxicity/2              (1 = least insertional/oncogenic risk)
      * ``efficacy_score`` = efficacy/2                       (1 = most efficacious)
    plus a headline ``safety_score = min(immune_score, genotox_score)`` — a precautionary worst-axis aggregation
    so a vehicle is only as "safe" as its WORST safety dimension (a non-immunogenic but genotoxic vector is not
    called safe). Also returns the documented tradeoff sentence, curated DOIs, and the standing scope flag that
    the immune MAGNITUDE is not predicted. Returns ``None`` for an unknown vehicle; invents no number."""
    rec = vehicle(name)
    if rec is None:
        return None
    imm = rec.get("immune_safety") or {}
    immune_present = [t for ax in _IMMUNE_AXES if (t := _tier(imm.get(ax))) is not None]
    immune_score = (1.0 - (sum(immune_present) / len(immune_present)) / 2.0) if immune_present else None
    gtox = _tier(imm.get(_GENOTOX_AXIS))
    genotox_score = (1.0 - gtox / 2.0) if gtox is not None else None
    sub = [s for s in (immune_score, genotox_score) if s is not None]
    safety_score = min(sub) if sub else None       # worst-axis; abstain if neither documented
    eff = _tier(imm.get("efficacy"))
    efficacy_score = (eff / 2.0) if eff is not None else None
    _r = lambda x: None if x is None else round(x, 3)  # noqa: E731
    return {
        "vehicle": name,
        "tiers": {ax: imm.get(ax) for ax in (*_IMMUNE_AXES, _GENOTOX_AXIS)} | {"efficacy": imm.get("efficacy")},
        "immune_score": _r(immune_score),
        "genotox_score": _r(genotox_score),
        "safety_score": _r(safety_score),
        "efficacy_score": _r(efficacy_score),
        "re_dosable": imm.get("re_dosable", rec.get("re_dosable")),
        "integrating": rec.get("integrating"),
        "tradeoff": imm.get("tradeoff"),
        "immune_dois": list(imm.get("immune_dois", []) or []),
        "magnitude_scope_flag": {
            "kind": "known_unknown", "id": _MAGNITUDE_SCOPE_ID,
            "reason": "the in-vivo immune MAGNITUDE (patient/construct-specific response) is a known-unknown; "
                      "only documented ordinal priors are surfaced, never a predicted magnitude"},
        "note": "safety_score = min(immune_score, genotox_score) over DOCUMENTED ordinal tiers — a precautionary "
                "worst-axis aggregation, not a predicted immunogenicity.",
    }


@lru_cache(maxsize=1)
def all_profiles() -> tuple:
    """All vehicle profiles (tuple so it is hashable/cacheable)."""
    return tuple(p for n in names() if (p := safety_efficacy_profile(n)) is not None)


def _balance(profile: dict, safety_weight: float) -> float | None:
    """Composite = safety_weight * safety_score + (1 - safety_weight) * efficacy_score. None if either axis is
    undocumented (abstain rather than impute)."""
    s, e = profile["safety_score"], profile["efficacy_score"]
    if s is None or e is None:
        return None
    w = min(max(float(safety_weight), 0.0), 1.0)
    return round(w * s + (1.0 - w) * e, 4)


def recommend_delivery(cargo_form: str, cargo_bp: int | None = None, *, safety_weight: float = 0.5,
                       in_vivo: bool | None = None) -> dict:
    """Rank the delivery palette for a cargo by a USER-WEIGHTED safety<->efficacy balance over documented priors.

    Args:
        cargo_form: required cargo form (DNA / mRNA / RNP) — only vehicles compatible with it are considered.
        cargo_bp: if given, vehicles whose ``cargo_capacity_bp`` is smaller are excluded (hard packaging limit).
        safety_weight: in [0, 1]. 1.0 = rank purely on documented safety; 0.0 = purely on efficacy; 0.5 = balance.
        in_vivo: if True, exclude ex-vivo-only vehicles (and vice-versa) when the field is documented.

    Returns a dict with the eligible vehicles ranked best-first by the composite, each carrying its documented
    tiers, tradeoff, and curated DOIs, plus the standing magnitude scope flag. No magnitude is predicted; the
    composite is an explicit function of the documented ordinal tiers and the caller's weight."""
    form = (cargo_form or "").strip()
    veh = load_vehicles()
    eligible: list[dict] = []
    excluded: list[dict] = []
    for n, rec in veh.items():
        forms = rec.get("compatible_cargo_form", []) or []
        if form and form not in forms:
            continue
        if cargo_bp is not None and rec.get("cargo_capacity_bp") is not None \
                and int(cargo_bp) > int(rec["cargo_capacity_bp"]):
            excluded.append({"vehicle": n, "reason": f"cargo {cargo_bp} bp exceeds capacity "
                                                     f"{rec['cargo_capacity_bp']} bp"})
            continue
        if in_vivo is True and rec.get("ex_vivo") and not rec.get("in_vivo"):
            excluded.append({"vehicle": n, "reason": "ex-vivo-only; an in-vivo route was required"})
            continue
        if in_vivo is False and rec.get("in_vivo") and not rec.get("ex_vivo"):
            excluded.append({"vehicle": n, "reason": "in-vivo-only; an ex-vivo route was required"})
            continue
        prof = safety_efficacy_profile(n)
        if prof is None:
            continue
        prof = dict(prof)
        prof["balance"] = _balance(prof, safety_weight)
        eligible.append(prof)

    # rank: documented balance first (None last); tie-break by efficacy then safety.
    eligible.sort(key=lambda p: (p["balance"] is None, -(p["balance"] or 0.0),
                                 -(p["efficacy_score"] or 0.0), -(p["safety_score"] or 0.0)))
    return {
        "cargo_form": form, "cargo_bp": cargo_bp, "safety_weight": min(max(float(safety_weight), 0.0), 1.0),
        "in_vivo": in_vivo,
        "ranked": eligible,
        "recommended": eligible[0]["vehicle"] if eligible else None,
        "excluded": excluded,
        "scope_flags": [{"kind": "known_unknown", "id": _MAGNITUDE_SCOPE_ID,
                         "reason": "ranking is over DOCUMENTED ordinal immune priors; the patient/construct-"
                                   "specific immune MAGNITUDE is a known-unknown and is not predicted"}],
        "no_fabrication": True,
        "note": "balance = safety_weight*safety + (1-safety_weight)*efficacy over documented low/moderate/high "
                "tiers; change safety_weight to move along the safety<->efficacy frontier.",
    }
