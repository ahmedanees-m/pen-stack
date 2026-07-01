"""Bridge-recombinase (IS110 / IS621) off-target path (PEN-OFFTGT v2, O-WS4).

Bridge recombinases are RNA-guided: the bridge RNA's target-binding loop base-pairs with a bipartite ~14-nt
genomic target (central CT). Off-target = genomic sites matching that target with tolerated mismatches. This
wraps the existing genome-wide scanner (`pen_stack.bridge.offtarget`), which seeds on the central core and scores
each pseudosite by the **measured Perry-2025 DMS specificity landscape** (which target mismatches the recombinase
tolerates) — a held-out ranking AUROC of 0.88 on that in-vitro DMS data.

**Status: mechanism_based_unvalidated (hard-locked).** Crucially, the DMS ranker being validated on *in-vitro
specificity* does NOT make the *genomic off-target predictions* validated: there is **no published genome-wide
unbiased CELLULAR off-target assay** for bridge recombinases (the technology is ~2024), so the genomic pseudosite
calls cannot be validated. The honest report is: a mechanism-based scan with a DMS-grounded mismatch-tolerance
model, labelled unvalidated, with the no-genome-wide-assay disclosure. Confirm by targeted amplicon /
integration-site sequencing. Never claims validation.
"""
from __future__ import annotations

_STATUS = "mechanism_based_unvalidated"
_DISCLOSURE = (
    "NO published genome-wide unbiased CELLULAR off-target assay exists for bridge recombinases (IS110/IS621; the "
    "technology is ~2024). The pseudosite RANKER is validated on the measured Perry-2025 in-vitro DMS specificity "
    "landscape (held-out ranking AUROC 0.88), but genomic recovery is NOT validated. Treat nominations as "
    "high-uncertainty, mechanism-based candidates — never a clearance."
)


def nominate_bridge(target_core: str | None = None, writer_family: str = "bridge_IS110",
                    fasta=None, chroms: list[str] | None = None, top: int = 20) -> dict:
    """Genome-wide bridge off-target scan for a bridge-RNA target core, via the DMS-scored engine. Returns the
    ranked pseudosites when a genome + target core are supplied (VM), else reports the engine is ready and how to
    run the scan. Always carries the hard-locked unvalidated status + the no-genome-wide-assay disclosure."""
    from pen_stack.bridge.offtarget import predict_offtargets
    fam = "seek_IS1111" if ("seek" in (writer_family or "").lower() or "is1111" in (writer_family or "").lower()) \
        else "bridge_IS110"
    res = predict_offtargets(fam, target_core=target_core, fasta=fasta, chroms=chroms, top=top)
    return {"family": "bridge", "writer_family": fam, "status": _STATUS,
            "ranker": "Perry-2025 DMS specificity landscape (measured; held-out ranking AUROC 0.88)",
            "no_ground_truth_disclosure": _DISCLOSURE,
            "confirm_assay": "targeted amplicon / integration-site sequencing at nominated pseudosites",
            "available": res.get("status") == "scanned",
            "abstain": not (res.get("status") == "scanned"),
            "engine": res,
            "method": ("seed on the central core (CT), verify the bipartite ~14-nt target with tolerated "
                       "mismatches, score by the measured DMS specificity (position + substitution identity)"),
            "honesty": ("mechanism-based CANDIDATES with a DMS-grounded mismatch-tolerance model; NOT a validated "
                        "genome-wide predictor (no cellular assay exists) and NOT a clearance."),
            "nomination_is_not_clearance": True}
