"""Off-target ground-truth + provenance for the cross-family nomination engine (v6.10 PEN-OFFTGT, E-WS1).

The ground truth is harmonized, PUBLISHED, unbiased genome-wide off-target assays over canonical Cas9 guides;
the derived risk calibration and the Off-Target-Bench headline (the REAL CRISOT predictor vs the homology
baseline) are embedded in-code so the axis is available everywhere (CI / bare install / live app), while the
full sealed fixture + per-guide metrics live under ``benchmarks/offtarget/`` for the bench harness.

LICENSING / SCOPE: the CRISOT predictor (Chen et al., Nat Commun 2023) is CC-BY-NC and runs ONLY on the VM,
its binaries/weights are NEVER redistributed; only DERIVED scores are cached (exactly like the licensed MHC
tools). Off-target SITE sequences are facts from the public assay supplements (cited below). A nominated
off-target is a CANDIDATE, never a claim.
"""
from __future__ import annotations

from functools import lru_cache

# ---- validated assay provenance (independently verified 2026-06-19) -----------------------------
ASSAY_PROVENANCE = {
    "guideseq": {"name": "GUIDE-seq", "kind": "cell-based, unbiased, genome-wide",
                 "citation": "Tsai et al., Nat Biotechnol 2015", "doi": "10.1038/nbt.3117"},
    "circleseq": {"name": "CIRCLE-seq", "kind": "in vitro (cell-free), unbiased, genome-wide",
                  "citation": "Tsai et al., Nat Methods 2017", "doi": "10.1038/nmeth.4278"},
    "changeseq": {"name": "CHANGE-seq", "kind": "in vitro, unbiased, high-throughput (110 sgRNAs)",
                  "citation": "Lazzarotto et al., Nat Biotechnol 2020", "doi": "10.1038/s41587-020-0555-7"},
    "siteseq": {"name": "SITE-seq", "kind": "in vitro biochemical, unbiased",
                "citation": "Cameron et al., Nat Methods 2017", "doi": "10.1038/nmeth.4284"},
}
PREDICTOR_PROVENANCE = {
    "crisot": {"name": "CRISOT-Score", "approach": "XGBoost RNA-DNA interaction fingerprint",
               "citation": "Chen et al., Nat Commun 2023", "doi": "10.1038/s41467-023-42695-4",
               "license": "CC-BY-NC (run on the VM; only derived scores cached, weights never redistributed)"},
}
# integrase off-target assays (large serine integrases), for the assay recommender; data-thin, preprints
INTEGRASE_ASSAY_PROVENANCE = {
    "cryptic_seq": {"name": "Cryptic-seq / HIDE-seq", "kind": "unbiased LSI off-target discovery",
                    "citation": "Hazelbaker et al. (Tome Biosciences), bioRxiv 2024",
                    "doi": "10.1101/2024.08.23.609471"},
    "intquery": {"name": "IntQuery", "kind": "LSI off-target deep-learning predictor (paper-only, no public weights)",
                 "citation": "Bakalar et al. (Tome Biosciences), bioRxiv 2024", "doi": "10.1101/2024.10.10.617699"},
}

# canonical Cas9 guides present in the bench (20-nt protospacers; Tsai 2015/2017)
CANONICAL_GUIDES = {
    "EMX1": "GAGTCCGAGCAGAAGAAGAA", "VEGFA_site1": "GGGTGGGGGGAGTTTGCTCC",
    "VEGFA_site2": "GACCCCCTCCACCCCGCCTC", "VEGFA_site3": "GGTGAGTGAGTGTGTGCGTG",
    "FANCF": "GGAATCCCTTCTGCAGCACC", "HEK293_site2": "GAACACAAAGCATAGACTGC",
    "HEK293_site3": "GGCCCAGACTGAGCACGTGA", "HEK293_site4": "GGCACTGCGGCTGGAGGTGG",
}

# ---- DERIVED, real-data risk calibration: empirical active fraction by mismatch count -----------
# (computed on the VM over ALL candidates per assay; the off-target nomination risk band is grounded in how often a
# candidate at k mismatches was actually validated-active, not a guessed curve. Missing k -> abstain, not extrapolate.)
MISMATCH_ACTIVE_FRACTION = {
    "guideseq": {0: 1.0, 1: 1.0, 2: 0.76471, 3: 0.23129, 4: 0.033, 5: 0.00276, 6: 0.00014},
    "circleseq": {0: 1.0, 1: 1.0, 2: 1.0, 3: 0.67146, 4: 0.26566, 5: 0.05924, 6: 0.00985},
    "changeseq": {0: 0.95, 2: 0.80851, 3: 0.56625, 4: 0.231, 5: 0.05505, 6: 0.00751},
    "siteseq": {0: 1.0, 1: 1.0, 2: 1.0, 3: 0.67188, 4: 0.2491, 5: 0.03554, 6: 0.00478},
}

# ---- chromatin-accessibility validation: a CONTROLLED test of whether accessibility predicts off-target activity
# (Lazzarotto 2020). v6.10.2 used a CROSS-CELL K562 proxy (weak/inconsistent); v6.10.3 used a CELL-TYPE-MATCHED
# ENCODE HEK293T DNase track and SETTLED it. VERDICT: VALIDATED (moderate, cell-type-matched) for WT-Cas9 cell-based
# off-target activity, GUIDE-seq AUROC rises 0.58 (cross-cell) -> 0.671 (matched), in-vitro control null (method
# sound). Moderate effect (sequence/CRISOT still dominates); TTISS is the expected outlier (a Cas9-VARIANT assay).
# Full result: benchmarks/offtarget/chromatin_validation.json.
CHROMATIN_VALIDATION = {
    "verdict": "validated (moderate, cell-type-matched) for WT-Cas9 cell-based off-target activity",
    "validated": True,
    "effect": "moderate",
    "auroc_accessibility_for_activity": {
        # cell-type-MATCHED HEK293T DNase (ENCFF529BOG); k562 = the earlier cross-cell proxy
        "guideseq": {"modality": "cell-based (WT Cas9)", "auroc": 0.671, "k562_cross_cell": 0.58, "ci95": [0.642, 0.701]},
        "ttiss": {"modality": "cell-based (Cas9 variants, outlier)", "auroc": 0.383, "k562_cross_cell": 0.346,
                  "ci95": [0.362, 0.405]},
        "siteseq": {"modality": "in_vitro_control", "auroc": 0.494, "k562_cross_cell": 0.469, "ci95": [0.475, 0.514]},
    },
    "matched_track": "ENCODE HEK293T DNase-seq (ENCFF529BOG, GRCh38)",
    # v6.10.4, does accessibility add INCREMENTAL value over the CRISOT sequence score? Tested at two imbalances:
    # a small REAL conditional signal (logreg acc coef ~0.35, CI excludes 0) but NO held-out ranking improvement
    # (CRISOT+acc AUPRC gap CI includes 0). DECISION: annotation, NOT a re-ranker. Full result:
    # benchmarks/offtarget/chromatin_incremental.json.
    "incremental_over_crisot": {
        "conditional_acc_coef": 0.351, "conditional_acc_coef_ci95": [0.2385, 0.5584], "adds_conditional_signal": True,
        "heldout_auprc_gap": 0.0027, "heldout_auprc_gap_ci95": [-0.014, 0.0214], "improves_ranking": False,
        "decision": "annotation only, accessibility carries a small real conditional signal but does NOT improve "
                    "held-out nomination ranking over the CRISOT sequence score (at realistic imbalance); a "
                    "re-ranking combiner is NOT wired in (no demonstrated benefit).",
    },
    "changes_numeric_risk_score": False,
    "note": "cell-type-matched accessibility predicts WT-Cas9 cell-based off-target activity (GUIDE-seq AUROC "
            "0.58 cross-cell -> 0.671 matched; in-vitro control null -> method sound). MODERATE effect (the "
            "sequence/CRISOT score dominates nomination) and CELL-TYPE-SPECIFIC. Does NOT transfer to the "
            "Cas9-VARIANT assay TTISS (0.383, the expected outlier). v6.10.4 tested the incremental value over "
            "CRISOT: a small real conditional signal but NO held-out ranking improvement -> chromatin is surfaced "
            "as a VALIDATED ANNOTATION and does NOT change the numeric risk score (CRISOT captures the ranking).",
}

# ---- Off-Target-Bench headline (REAL full-data result; per-guide AUPRC, held-out-guide bootstrap CI) -----
# CRISOT-Score is the MD-physics, assay-AGNOSTIC scorer (not fit on these labels) -> a leakage-clean held-out
# evaluation on every assay. GUIDE/CIRCLE-seq use canonical guides; CHANGE/SITE-seq use INDEPENDENT broad guide
# panels (cross-assay generalization). CRISOT beats the homology baseline on ALL FOUR (per-guide bootstrap CI > 0).
BENCH_SUMMARY = {
    "guideseq": {"n_guides": 8, "guide_panel": "canonical", "crisot_auprc": 0.6458, "homology_auprc": 0.4668,
                 "auprc_gap": 0.179, "gap_ci95": [0.0136, 0.3292], "crisot_beats_homology": True},
    "circleseq": {"n_guides": 8, "guide_panel": "canonical", "crisot_auprc": 0.5197, "homology_auprc": 0.2664,
                  "auprc_gap": 0.2533, "gap_ci95": [0.1463, 0.3704], "crisot_beats_homology": True},
    "changeseq": {"n_guides": 20, "guide_panel": "independent_broad", "crisot_auprc": 0.541, "homology_auprc": 0.2486,
                  "auprc_gap": 0.2924, "gap_ci95": [0.2349, 0.3477], "crisot_beats_homology": True},
    "siteseq": {"n_guides": 11, "guide_panel": "independent_broad", "crisot_auprc": 0.5207, "homology_auprc": 0.2332,
                "auprc_gap": 0.2874, "gap_ci95": [0.2388, 0.3354], "crisot_beats_homology": True},
    "metric": "per-guide AUPRC; baseline = ascending mismatch count; learned = real CRISOT-Score (assay-agnostic, "
              "VM, cached); CRISOT beats homology on all 4 assays (bootstrap CI excludes 0)",
}


def assay_provenance() -> dict:
    """Validated provenance for every assay + predictor the off-target engine is grounded on."""
    return {"nuclease_assays": ASSAY_PROVENANCE, "nuclease_predictor": PREDICTOR_PROVENANCE,
            "integrase_assays": INTEGRASE_ASSAY_PROVENANCE}


@lru_cache(maxsize=1)
def bench_records() -> list[dict]:
    """The committed Off-Target-Bench fixture (real validated off-targets + cached CRISOT scores) as a list of
    dicts, or [] when the data tree is absent (bare wheel). Columns: assay, guide, On, Off, mismatch, active,
    crisot_score."""
    try:
        import csv

        from pen_stack._resources import resource
        path = resource("benchmarks/offtarget/offtarget_bench_fixture.csv")
        with open(path, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            r["mismatch"] = int(r["mismatch"])
            r["active"] = int(r["active"])
            r["crisot_score"] = float(r["crisot_score"])
        return rows
    except Exception: # noqa: BLE001 (bare wheel / no data tree -> the bench harness is checkout-only)
        return []


def calibrated_active_fraction(n_mismatch: int, assay: str = "guideseq") -> float | None:
    """The empirical fraction of candidate sites at ``n_mismatch`` mismatches that were validated-active in the
    named assay (grounded risk). None if the mismatch count is outside the calibrated range (then the axis
    abstains rather than extrapolating)."""
    table = MISMATCH_ACTIVE_FRACTION.get(assay, MISMATCH_ACTIVE_FRACTION["guideseq"])
    return table.get(int(n_mismatch))
