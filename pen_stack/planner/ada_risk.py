"""ADA-risk (v6.9 PEN-IMMUNE, G-WS2; v6.9.2 real-tool re-grounding).

A protein's MHC-II epitope load (presentation potential) is necessary but not sufficient for anti-drug antibodies
(ADA): **self** proteins carry MHC-II epitopes too, yet are tolerated (central tolerance deletes self-reactive T
cells). What drives ADA is **non-self** (foreign) presentable epitopes. So:

    ADA-risk = MHC-II epitope density (real, NetMHCIIpan-4.0) x foreignness

where **foreignness is the protein ORIGIN** (self vs bacterial/viral/phage), the authoritative, definitive
self/non-self signal (central tolerance), not a heuristic. The **real human-proteome 9-mer self-match** (computed
on the VM against the full UniProt human reference proteome) is reported as a cross-check. NO heuristic fallback:
when the MHC-II density is not cached (NetMHCIIpan not run) OR the origin is unknown, ADA-risk **abstains** (an
known-unknown) rather than guessing.

a population-level proxy, never a patient-specific ADA titer (a known-unknown). The calibration
against a public ADA-incidence set runs through the EXISTING calibrate_axis gate and stays at public-data power.
"""
from __future__ import annotations

from pen_stack.planner.immune_mhc2 import _real_cache, mhc2_epitope_load, writer_sequences

ADA_DOIS = ["10.1038/s41467-021-25414-9"] # Cas9 MHC-II CD4 immunogenicity (Simhadri 2021)
_FOREIGN = {"self": 0.0, "foreign": 1.0}


def real_self_match(name: str) -> dict | None:
    """The REAL human-proteome 9-mer self-match for a bundled antigen (cross-check; computed on the VM against the
    full UniProt human reference proteome). Foreign proteins ~0, human ~1. None if not in the cache."""
    rec = (_real_cache().get("self_match") or {}).get(name)
    if rec is None:
        return None
    return {"human_9mer_match_fraction": rec.get("fraction"), "n_9mers": rec.get("n"),
            "reference": (_real_cache().get("self_match_meta") or {}).get("reference",
                          "UniProt human reference proteome (full)")}


def ada_risk(seq: str, origin: str | None = None, name: str | None = None) -> dict:
    """ADA-risk = real MHC-II epitope density x foreignness(origin). Abstains (no proxy/heuristic) when the MHC-II
    density is uncached or the origin is unknown. Higher ada_risk_score = MORE ADA risk; ada_immune_score = 1 - it."""
    el = mhc2_epitope_load(seq, name)
    density = el.get("epitope_density")
    foreign = _FOREIGN.get(str(origin)) if origin is not None else None
    sm = real_self_match(name) if name else None
    base = {"epitope_density": density, "foreignness": foreign, "origin": origin,
            "self_match_human_proteome": sm, "dois": ADA_DOIS,
            "filter": "central tolerance: foreign (non-self) MHC-II epitopes drive ADA; self tolerated. Foreignness "
                      "= protein origin (authoritative); MHC-II density = NetMHCIIpan-4.0; real human-proteome "
                      "self-match reported as cross-check (no heuristic).",
            "status": "population-level; patient ADA titer / magnitude is a known-unknown"}
    if density is None or foreign is None:
        return {**base, "ada_risk_score": None, "ada_immune_score": None, "backend": "abstain",
                "note": ("abstains (no proxy): " + ("NetMHCIIpan-4.0 not run for this sequence" if density is None
                         else "protein origin unknown, foreignness is not guessed"))}
    risk = round(density * foreign, 4)
    return {**base, "ada_risk_score": risk, "ada_immune_score": round(1.0 - risk, 4), "backend": "real"}


def ada_risk_named(name: str) -> dict:
    """ADA-risk for a bundled writer/control protein by name (uses its declared origin + the real MHC-II cache)."""
    rec = writer_sequences().get(name)
    if not rec:
        return {"available": False, "note": f"no bundled sequence {name!r}"}
    return {"available": True, "name": name, "family": rec.get("family"),
            **ada_risk(rec["seq"], rec.get("origin"), name=name)}
