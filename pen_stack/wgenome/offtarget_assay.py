"""Validation-assay recommender for off-target nomination (v6.10 PEN-OFFTGT, E-WS3).

Nomination is NOT a clearance, it ships with the empirical assay that would CONFIRM the candidates. This maps a
writer family to the appropriate unbiased genome-wide assay(s) + their documented applicability, grounded in the
validated assay literature. For families with no published genome-wide off-target assay (bridge recombinases) it
says so and recommends targeted confirmation, never implying a clearance exists.
"""
from __future__ import annotations

# assay applicability by writer family (validated citations in offtarget_data.ASSAY_PROVENANCE)
_NUCLEASE_ASSAYS = [
    {"assay": "GUIDE-seq", "setting": "cell-based (in cellulo)", "doi": "10.1038/nbt.3117",
     "use": "captures off-targets in the actual chromatin/cell context (dsODN tag at DSBs)"},
    {"assay": "CHANGE-seq", "setting": "in vitro, high-throughput", "doi": "10.1038/s41587-020-0555-7",
     "use": "most sensitive genome-wide nomination; pair with a cell-based assay to filter chromatin-masked sites"},
    {"assay": "CIRCLE-seq", "setting": "in vitro (cell-free)", "doi": "10.1038/nmeth.4278",
     "use": "highly sensitive in vitro confirmation; over-nominates vs cell context"},
]


def recommend_assay(writer_family: str) -> dict:
    """Recommend the empirical validation assay(s) for a writer family + the documented expected sensitivity, or
    an explicit 'no genome-wide assay exists' for data-thin families. Always frames nomination as not a clearance."""
    fam = (writer_family or "").lower()
    if "cas9" in fam or "nuclease" in fam or fam in {"spcas9", "sacas9", "cas12a", "ascas12a", "nickase"}:
        return {"family": writer_family, "writer_class": "RNA-guided nuclease (DSB)",
                "recommended": _NUCLEASE_ASSAYS,
                "strategy": "nominate in vitro (CHANGE-/CIRCLE-seq, high sensitivity) THEN confirm the survivors "
                            "in the target cell type (GUIDE-seq), chromatin masks a fraction of in vitro sites",
                "available": True,
                "note": "nomination ranks CANDIDATES; an empirical assay is required for clearance."}
    if ("integrase" in fam or "bxb1" in fam or "phic31" in fam) and "paste" not in fam and "passige" not in fam:
        return {"family": writer_family, "writer_class": "large serine integrase",
                "recommended": [{"assay": "Cryptic-seq / HIDE-seq", "setting": "unbiased LSI off-target discovery",
                                 "doi": "10.1101/2024.08.23.609471",
                                 "use": "the genome-wide unbiased assay for serine-integrase cryptic attB sites "
                                        "(Tome Biosciences, 2024 preprint)"}],
                "strategy": "scan cryptic pseudo-attB (this engine) THEN confirm by Cryptic-seq/HIDE-seq; "
                            "quantitative prediction (IntQuery) is paper-only (no public weights)",
                "available": True,
                "note": "LSI off-target assays are recent preprints; coverage is single-company / largely Bxb1."}
    if "paste" in fam or "passige" in fam:
        return {"family": writer_family, "writer_class": "prime-editing integrase (PASTE / PASSIGE)",
                "recommended": [
                    {"assay": "GUIDE-seq / CHANGE-seq", "setting": "nuclease (nickase) off-target", "doi": "10.1038/nbt.3117",
                     "use": "confirm the Cas9-nickase off-targets of the pegRNA spacer"},
                    {"assay": "Cryptic-seq / HIDE-seq", "setting": "integrase off-target", "doi": "10.1101/2024.08.23.609471",
                     "use": "confirm the integrase pseudo-attP sites of the installed att"}],
                "strategy": "PASTE off-target is composite — run BOTH a nuclease assay (for the nickase) AND an "
                            "integrase assay (for the installed att); the two components are independent.",
                "available": True,
                "note": "two independent off-target mechanisms; neither assay alone clears a PASTE design."}
    if "cast" in fam or "cas12k" in fam or "shcast" in fam or "vchcast" in fam or "evocast" in fam:
        return {"family": writer_family, "writer_class": "CRISPR-associated transposase (CAST)",
                "recommended": [{"assay": "transposon insertion-site sequencing", "setting": "unbiased integration mapping",
                                 "doi": "10.1126/science.aax9181",
                                 "use": "map genome-wide integration sites, including guide-INDEPENDENT untargeted "
                                        "transposition (the dominant off-target mode for Type V-K, e.g. ShCAST)"}],
                "strategy": "sequence integration sites to capture BOTH guide-directed off-targets and the "
                            "guide-independent untargeted-transposition background (Type V-K high; Type I-F low)",
                "available": True,
                "note": "KNOWN GAP: no genome-wide unbiased CELLULAR off-target assay is standardised for human-cell "
                        "CAST; untargeted-transposition rates are characterised in bacteria/biochemically. "
                        "Mechanism-based, unvalidated."}
    if "bridge" in fam or "is110" in fam or "is621" in fam or "seek" in fam or "iscro4" in fam:
        return {"family": writer_family, "writer_class": "bridge recombinase (IS110/IS621 RNA-guided)",
                "recommended": [{"assay": "targeted amplicon / capture sequencing at nominated pseudosites",
                                 "setting": "targeted", "doi": None,
                                 "use": "confirm individual nominated pseudosites (no genome-wide unbiased "
                                        "off-target assay exists for bridge recombinases yet)"}],
                "strategy": "nominate pseudosites with the Perry-DMS engine THEN confirm by targeted sequencing; "
                            "an unbiased genome-wide bridge off-target assay is an open need",
                "available": True,
                "note": "KNOWN GAP: bridge-recombinase off-target is essentially unmodeled, there is NO "
                        "published genome-wide unbiased assay or predictor (verified). Treat nominations as "
                        "high-uncertainty / extrapolative; do not read as clearance."}
    return {"family": writer_family, "available": False,
            "note": f"no off-target assay applicability rule for family {writer_family!r}"}
