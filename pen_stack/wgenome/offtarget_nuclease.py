"""Nuclease off-target FINDER (PEN-OFFTGT v2, O-WS2): enumerate -> CRISOT -> risk -> chromatin.

Chains the genome-wide enumeration (O-WS1) into the existing, validated nuclease scorer, so a GUIDE returns a
genome-wide ranked off-target set (what CRISPOR/CHOPCHOP do) rather than a hand-supplied one. The scoring is
UNCHANGED from v6.10 — the real CRISOT-Score, the mismatch-calibrated risk band, and the chromatin annotation
(validated, not a re-ranker). v2 only adds the enumeration front end. Status: **validated** (CRISOT beats
homology on four unbiased assays; enumeration reproduces the documented off-target set, gate O-G1).

Enumeration runs on the VM; this surface replays the committed cache or abstains (so the finder works for the
cached guides and is honest for a novel one), exactly like the heavy oracles.
"""
from __future__ import annotations

from pen_stack.wgenome.offtarget_data import BENCH_SUMMARY, calibrated_active_fraction
from pen_stack.wgenome.offtarget_enumerate import enumerate_offtargets, resolve_enzyme
from pen_stack.wgenome.offtarget_predict import (
    _chromatin_modifier,
    _crisot_cache,
    _ham20,
    _risk_band,
    locus_accessibility,
)

_BIN = 1000  # Stage B accessibility bins are 1 kb (matches the off-target chromatin validation)


def find_nuclease_offtargets(guide: str, enzyme: str = "SpCas9", max_mismatch: int = 5, assay: str = "guideseq",
                             cell_type: str = "k562", top: int = 50) -> dict:
    """Genome-wide nuclease off-target FINDER. Enumerates every genomic site within ``max_mismatch`` for the guide
    (Cas-OFFinder over GRCh38, replayed from cache), scores each with the real CRISOT-Score + the mismatch-
    calibrated empirical risk band, and annotates chromatin accessibility (Stage B track when present). Returns
    the genome-wide ranked candidates with coordinates, or an honest abstention when the guide is not cached and no
    VM scan is available. Never fabricates sites."""
    enz = resolve_enzyme(enzyme) or "SpCas9"
    enum = enumerate_offtargets(guide, enz, max_mismatch)
    if enum.get("abstain"):
        return {"family": "nuclease", "enzyme": enz, "available": False, "abstain": True, "mode": "finder",
                "status": "validated", "note": enum["note"], "cached_guides": enum.get("cached_guides", []),
                "nomination_is_not_clearance": True}
    g20 = enum["guide"][:20]
    cache = _crisot_cache()
    noms = []
    for s in enum["sites"]:
        seq = s["sequence"].upper()
        nmm = int(s.get("n_mismatch", _ham20(g20, seq)))
        af = calibrated_active_fraction(nmm, assay)
        crisot = cache.get((g20, seq[:20]))
        locus_acc = locus_accessibility(s["chrom"], s["position"] // _BIN, cell_type)  # REAL Stage B (or None)
        noms.append({"chrom": s["chrom"], "position": s["position"], "strand": s["strand"], "site": seq,
                     "n_mismatch": nmm, "empirical_active_fraction": af, "risk_band": _risk_band(af),
                     "crisot_score": crisot,
                     "crisot_source": "cached_bench" if crisot is not None else "on-VM tool (not cached)",
                     "chromatin": _chromatin_modifier(None, locus_acc), "output_kind": "candidate"})
    # rank by the real CRISOT score where cached, else by empirical risk (descending), then fewer mismatches
    noms.sort(key=lambda n: (n["crisot_score"] if n["crisot_score"] is not None else -1.0,
                             n["empirical_active_fraction"] or 0.0, -n["n_mismatch"]), reverse=True)
    n_on = sum(1 for n in noms if n["n_mismatch"] == 0)
    return {"family": "nuclease", "enzyme": enz, "available": True, "abstain": False, "mode": "finder",
            "guide": g20, "pam": enum["pam"], "source": enum["source"], "max_mismatch": int(max_mismatch),
            "n_sites_genome_wide": enum["n_sites"], "n_on_target": n_on, "n_offtargets": len(noms) - n_on,
            "assay_calibration": assay, "nominations": noms[:top], "bench": BENCH_SUMMARY.get(assay),
            "status": "validated",
            "method": ("genome-wide Cas-OFFinder enumeration over GRCh38 -> real CRISOT-Score -> mismatch-"
                       "calibrated risk band -> chromatin annotation (validated, NOT a re-ranker)"),
            "honesty": "genome-wide CANDIDATES, NOT a clearance; confirm with the recommended empirical assay",
            "nomination_is_not_clearance": True}
