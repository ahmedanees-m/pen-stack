"""Nuclease off-target FINDER: enumerate -> CRISOT -> risk -> chromatin.

Chains the genome-wide enumeration into the existing, validated nuclease scorer, so a GUIDE returns a
genome-wide ranked off-target set rather than a hand-supplied one. The scoring is
UNCHANGED from v6.10, the real CRISOT-Score, the mismatch-calibrated risk band, and the chromatin annotation
(validated, not a re-ranker). v2 only adds the enumeration front end. Status: **validated** (CRISOT beats
homology on four unbiased assays; enumeration reproduces the documented off-target set).

Enumeration runs on the VM; this surface replays the committed cache or abstains (so the finder works for the
cached guides and abstains for a novel one), exactly like the heavy oracles.
"""
from __future__ import annotations

from pen_stack.wgenome.offtarget_data import BENCH_SUMMARY, CHROMATIN_VALIDATION, calibrated_active_fraction
from pen_stack.wgenome.offtarget_enumerate import enumerate_offtargets, resolve_enzyme
from pen_stack.wgenome.offtarget_predict import (
    _chromatin_modifier,
    _crisot_cache,
    _ham20,
    _risk_band,
    locus_accessibility,
)

_BIN = 1000  # accessibility track bins are 1 kb (matches the off-target chromatin validation)
_CAS12A = {"AsCas12a", "LbCas12a"}  # enumeration-supported, but the CRISOT scorer + risk calibration are SpCas9-only


def find_nuclease_offtargets(guide: str, enzyme: str = "SpCas9", max_mismatch: int = 5, assay: str = "guideseq",
                             cell_type: str = "k562", top: int = 50) -> dict:
    """Genome-wide nuclease off-target FINDER. Enumerates every genomic site within ``max_mismatch`` for the guide
    (Cas-OFFinder over GRCh38, replayed from cache), scores each with the real CRISOT-Score + the mismatch-
    calibrated empirical risk band, and annotates chromatin accessibility (from the accessibility track when present). Returns
    the genome-wide ranked candidates with coordinates, or an abstention when the guide is not cached and no
    VM scan is available. Never fabricates sites."""
    enz = resolve_enzyme(enzyme) or "SpCas9"
    if enz in _CAS12A or "cas12" in (enzyme or "").lower():
        # ABSTAIN (never mis-score): genome-wide enumeration supports Cas12a (Cas-OFFinder, TTTV 5' PAM),
        # but the validated CRISOT-Score and the mismatch-calibrated risk band are BOTH SpCas9-specific. Rather than
        # silently applying a SpCas9 model to Cas12a sites, the finder declines and says why.
        return {"family": "nuclease", "enzyme": enz, "available": False, "abstain": True, "mode": "finder",
                "status": "unvalidated", "cached_guides": [], "nomination_is_not_clearance": True,
                "note": ("Cas12a genome-wide enumeration IS supported (Cas-OFFinder, TTTV 5' PAM), but the "
                         "validated off-target scorer (CRISOT-Score) and the mismatch-calibrated empirical risk "
                         "band are SpCas9-specific, there is no validated Cas12a off-target model mounted, so this "
                         "finder does NOT fabricate a Cas12a ranking (a SpCas9 scorer would mis-rank Cas12a sites). "
                         "AsCas12a is listed as a Tier-1 nuclease in the Writer Atlas; a validated Cas12a off-target "
                         "scorer is future work.")}
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
        locus_acc = locus_accessibility(s["chrom"], s["position"] // _BIN, cell_type)  # REAL accessibility track (or None)
        noms.append({"chrom": s["chrom"], "position": s["position"], "strand": s["strand"], "site": seq,
                     "n_mismatch": nmm, "empirical_active_fraction": af, "risk_band": _risk_band(af),
                     "crisot_score": crisot,
                     "crisot_source": "cached_bench" if crisot is not None else "on-VM tool (not cached)",
                     "chromatin": _chromatin_modifier(None, locus_acc), "output_kind": "candidate"})
    # rank by the real CRISOT score where cached, else by empirical risk (descending), then fewer mismatches
    noms.sort(key=lambda n: (n["crisot_score"] if n["crisot_score"] is not None else -1.0,
                             n["empirical_active_fraction"] or 0.0, -n["n_mismatch"]), reverse=True)
    n_on = sum(1 for n in noms if n["n_mismatch"] == 0)
    # chromatin is a REAL accessibility annotation, populated per-site only when the accessibility track is mounted.
    # Be explicit instead of silently returning null everywhere (which reads as if the layer were delivered).
    chromatin_available = any(n.get("chromatin") is not None for n in noms)
    _cv = CHROMATIN_VALIDATION["auroc_accessibility_for_activity"]["guideseq"]
    chromatin_note = (
        "Chromatin accessibility is a VALIDATED standalone annotation (open chromatin predicts cell-based "
        "off-target activity: GUIDE-seq AUROC 0.671, cell-type-matched HEK293T DNase) but is ANNOTATION-ONLY, it "
        "does NOT change the CRISOT-driven ranking. It is populated per-site only when the accessibility "
        "track (chromatin_{ct}.parquet) is mounted; that track is not present on this deployment, so the per-site "
        "column is omitted (ranking unaffected)." if not chromatin_available else
        "Per-site chromatin accessibility from the mounted track, annotation-only, does not change the "
        "CRISOT-driven ranking.")
    return {"family": "nuclease", "enzyme": enz, "available": True, "abstain": False, "mode": "finder",
            "guide": g20, "pam": enum["pam"], "source": enum["source"], "max_mismatch": int(max_mismatch),
            "n_sites_genome_wide": enum["n_sites"], "n_on_target": n_on, "n_offtargets": len(noms) - n_on,
            "assay_calibration": assay, "nominations": noms[:top], "bench": BENCH_SUMMARY.get(assay),
            "status": "validated",
            "chromatin_available": chromatin_available, "chromatin_note": chromatin_note,
            "chromatin_validation": {"verdict": CHROMATIN_VALIDATION["verdict"], "guideseq_auroc": _cv["auroc"],
                                     "ci95": _cv["ci95"], "matched_track": CHROMATIN_VALIDATION["matched_track"],
                                     "is_reranker": False},
            "method": ("genome-wide Cas-OFFinder enumeration over GRCh38 -> real CRISOT-Score -> mismatch-"
                       "calibrated risk band" + (" -> chromatin accessibility annotation (validated, annotation-"
                       "only, NOT a re-ranker)" if chromatin_available else
                       "; chromatin accessibility is a validated annotation surfaced when the accessibility track is "
                       "mounted (annotation-only, not a re-ranker)")),
            "honesty": "genome-wide CANDIDATES, NOT a clearance; confirm with the recommended empirical assay",
            "nomination_is_not_clearance": True}
