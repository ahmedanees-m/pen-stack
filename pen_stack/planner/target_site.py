"""Target-site / PAM / att-site availability filter (Phase 3.2, WS-MC / MC1).

A **sequence-computable hard filter** on reachability: for a candidate site sequence, does the writer family
carry the *targeting element* its mechanism physically requires? No usable element → the writer is unreachable
there and is REJECTED. This extends the WT-KB reachability tier with a sequence-level mechanistic check,
"the LLM may propose a writer, but if the physics says it cannot engage this site, the funnel rejects it."

Requirement per family (configs/target_sites.yaml):
  * ``pam``, a PAM motif must occur in the window (Cas9 NGG / Cas12a TTTV / CAST GTN).
  * ``core_dinuc``, a programmable bipartite recombinase needs its central core dinucleotide (bridge/seek CT).
  * ``att_site``, a serine integrase needs an attB/attP (pseudo-)att; a naive genomic window has none, so
                         it REJECTS unless a landing pad was pre-installed (the key mechanistic reject).
  * ``pe_installable``, a PE-integrase installs its own att, so the site is broadly reachable (available + note).

These are SCREENS, not activity guarantees (relaxed-PAM engineered variants especially); reported with a
confidence. The point is the hard *negative*: a physically impossible writer, site pairing is rejected.
"""
from __future__ import annotations

import re
from functools import lru_cache

import yaml

from pen_stack._resources import resource

# IUPAC nucleotide → regex character class (for PAM / att-core expansion).
_IUPAC = {"A": "A", "C": "C", "G": "G", "T": "T", "R": "[AG]", "Y": "[CT]", "S": "[GC]", "W": "[AT]",
          "K": "[GT]", "M": "[AC]", "B": "[CGT]", "D": "[AGT]", "H": "[ACT]", "V": "[ACG]", "N": "[ACGT]"}


@lru_cache(maxsize=1)
def _cfg() -> dict:
    return yaml.safe_load(resource("configs/target_sites.yaml").read_text(encoding="utf-8"))


def _clean(seq: str) -> str:
    return re.sub(r"[^ACGT]", "", (seq or "").upper())


def iupac_to_regex(motif: str) -> str:
    return "".join(_IUPAC.get(b, b) for b in motif.upper())


def find_motif(seq: str, motif: str) -> list[int]:
    """0-based start positions of an IUPAC motif (overlapping) in a cleaned sequence."""
    s = _clean(seq)
    pat = iupac_to_regex(motif)
    return [m.start() for m in re.finditer(f"(?=({pat}))", s)]


def target_site_available(family: str, seq: str, installed_att: bool = False) -> dict:
    """Is the writer family's required targeting element present in ``seq``? Returns a structured verdict.

    ``installed_att=True`` declares a pre-installed landing pad (so a serine/PE integrase becomes reachable
    deterministically). The result is a HARD filter input: ``available=False`` → reject the writer at this site.
    """
    fams = _cfg()["families"]
    fam = fams.get(family)
    s = _clean(seq)
    if fam is None:
        # unknown family: do not silently reject; report not-checkable (reachability falls back to WT-KB tier)
        return {"family": family, "available": True, "checked": False,
                "reason": "no target-site rule for this family; reachability deferred to WT-KB tier",
                "confidence": "none"}

    req = fam["requirement"]
    conf = fam.get("confidence", "inferred")

    if req == "pam":
        hits = find_motif(s, fam["pam"])
        ok = len(hits) > 0
        out = {"family": family, "requirement": "pam", "pam": fam["pam"], "n_pam_sites": len(hits),
               "available": ok, "checked": True, "confidence": conf,
               "reason": (f"{len(hits)} {fam['pam']} PAM site(s) present" if ok
                          else f"no {fam['pam']} PAM in the window, writer cannot target here (reject)")}
        if "insertion_offset_bp" in fam:
            out["insertion_offset_bp"] = fam["insertion_offset_bp"]
        return out

    if req == "core_dinuc":
        hits = find_motif(s, fam["core_dinuc"])
        ok = len(hits) > 0
        return {"family": family, "requirement": "core_dinuc", "core": fam["core_dinuc"],
                "n_core_sites": len(hits), "available": ok, "checked": True, "confidence": conf,
                "reason": (f"central {fam['core_dinuc']} core present ({len(hits)} site(s)); loops reprogrammable"
                           if ok else f"no {fam['core_dinuc']} core in the window, bipartite recombinase "
                           "has no recombination point (reject)")}

    if req == "att_site":
        if installed_att:
            return {"family": family, "requirement": "att_site", "available": True, "checked": True,
                    "confidence": conf, "installed_att": True,
                    "reason": "pre-installed att landing pad declared, integrase reachable deterministically"}
        present = [m for m in fam.get("att_motifs", []) if iupac_to_regex(m) and re.search(iupac_to_regex(m), s)]
        ok = bool(present)
        return {"family": family, "requirement": "att_site", "available": ok, "checked": True,
                "confidence": conf, "att_motifs_found": present,
                "reason": ("a native (pseudo-)att core is present" if ok else
                           "no attB/attP (pseudo-)att in the window, serine integrase needs a pre-installed "
                           "landing pad; unreachable at a naive site (reject)")}

    if req == "pe_installable":
        return {"family": family, "requirement": "pe_installable", "available": True, "checked": True,
                "confidence": conf,
                "reason": "PE installs the att beacon at the chosen site, broadly reachable (no native motif "
                          "required; the install step is PE-bounded, per the WT-KB reachability tier)"}

    return {"family": family, "available": True, "checked": False,
            "reason": f"unhandled requirement {req!r}; reachability deferred to WT-KB tier", "confidence": "none"}


def filter_reachable(families: list[str], seq: str, installed_att: bool = False) -> dict:
    """Split a candidate writer list into mechanistically reachable vs rejected at this site sequence."""
    verdicts = {f: target_site_available(f, seq, installed_att=installed_att) for f in families}
    reachable = [f for f, v in verdicts.items() if v["available"]]
    rejected = [{"family": f, "reason": v["reason"]} for f, v in verdicts.items() if not v["available"]]
    return {"reachable": reachable, "rejected": rejected, "verdicts": verdicts}
