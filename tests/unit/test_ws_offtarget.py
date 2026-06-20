"""v6.10 PEN-OFFTGT, cross-family off-target NOMINATION (E-WS1..E-WS4).

CI-safe: the Off-Target-Bench fixture (real validated off-targets + cached CRISOT scores) and the derived
calibration/metrics are committed; the licensed CRISOT predictor runs only on the VM and is never redistributed.
Asserts: the real learned predictor beats the homology baseline (full-data headline); the nominator ranks
validated off-targets, abstains without inputs, and never claims a clearance; the integrase pseudo-attB scan uses
the real Bxb1 attB core; bridge delegates honestly; the assay recommender is grounded; provenance DOIs grounded.
"""
from __future__ import annotations

from benchmarks.offtarget.harness import run as bench_run
from pen_stack.agent.cite import citations_grounded
from pen_stack.wgenome.offtarget_assay import recommend_assay
from pen_stack.wgenome.offtarget_data import (
    ASSAY_PROVENANCE,
    BENCH_SUMMARY,
    bench_records,
    calibrated_active_fraction,
)
from pen_stack.wgenome.offtarget_predict import (
    nominate_nuclease,
    nominate_offtargets,
    pseudo_attb_sites,
)


# ---- E-WS1: dataset + bench --------------------------------------------------------------------
def test_bench_real_crisot_beats_homology_full_data():
    # the AUTHORITATIVE result (full real data, on-VM CRISOT vs homology): learned beats homology on ALL FOUR
    # unbiased assays (GUIDE/CIRCLE-seq canonical guides; CHANGE/SITE-seq independent broad panels), CI excludes 0
    for assay in ("guideseq", "circleseq", "changeseq", "siteseq"):
        s = BENCH_SUMMARY[assay]
        assert s["crisot_beats_homology"] is True
        assert s["crisot_auprc"] > s["homology_auprc"]
        assert s["gap_ci95"][0] > 0 # bootstrap CI on the gap excludes 0
    # CHANGE/SITE-seq are independent broad guide panels (cross-assay generalization for the assay-agnostic scorer)
    assert BENCH_SUMMARY["changeseq"]["guide_panel"] == "independent_broad"
    assert BENCH_SUMMARY["changeseq"]["n_guides"] >= 15


def test_bench_fixture_loads_and_is_real():
    rows = bench_records()
    assert len(rows) > 1000 and sum(r["active"] for r in rows) > 100
    assert {"assay", "guide", "On", "Off", "mismatch", "active", "crisot_score"} <= set(rows[0])
    b = bench_run()
    assert b["available"] is True and b["held_out"] == "guide"
    assert b["crisot_beats_homology"] is True


def test_provenance_dois_are_grounded():
    dois = [v["doi"] for v in ASSAY_PROVENANCE.values()]
    assert citations_grounded(dois)["all_grounded"] is True


# ---- E-WS2: nomination ------------------------------------------------------------------------
def test_risk_is_mismatch_calibrated_on_real_data():
    # grounded empirical risk: fewer mismatches -> higher validated-active fraction (real GUIDE-seq data)
    assert calibrated_active_fraction(0) == 1.0
    assert calibrated_active_fraction(2) > calibrated_active_fraction(4) > calibrated_active_fraction(6)
    assert calibrated_active_fraction(99) is None # outside calibrated range -> abstains, never extrapolates


def test_nuclease_nomination_ranks_validated_offtargets():
    rows = [r for r in bench_records() if r["guide"] == "EMX1" and r["assay"] == "guideseq"]
    on = rows[0]["On"]
    cands = [r["Off"] for r in rows[:10]]
    res = nominate_nuclease(on, cands, assay="guideseq", top=10)
    assert res["available"] is True and res["abstain"] is False
    assert all(n["output_kind"] == "candidate" for n in res["nominations"])
    # the perfect/low-mismatch match ranks at the top with a calibrated high-risk band + a real cached CRISOT score
    top = res["nominations"][0]
    assert top["n_mismatch"] <= 2 and top["risk_band"] == "high" and top["crisot_score"] is not None


def test_nuclease_abstains_without_candidates_no_fabrication():
    r = nominate_nuclease("GAGTCCGAGCAGAAGAAGAA", None)
    assert r["available"] is False and r["abstain"] is True and "fabricate" in r["note"].lower()


def test_chromatin_modifier_real_stage_b_or_honest_abstain():
    # the chromatin modifier reads the REAL Stage B accessibility track when present, else abstains (no fabrication);
    # a caller-supplied accessibility scalar is the documented fallback (Lazzarotto 2020)
    from pen_stack.wgenome.offtarget_predict import locus_accessibility
    # no chromatin feature store in CI/bare -> abstains (None), never invents a value
    assert locus_accessibility("chr1", 0, "k562") is None
    # caller-supplied accessibility -> documented modifier (bounded, qualitative), now VALIDATED (cell-type-matched)
    r = nominate_nuclease("GAGTCCGAGCAGAAGAAGAAGGG", ["GAGTTAGAGCAGAAGAAGAAGGG"], accessibility=[0.9])
    ch = r["nominations"][0]["chromatin"]
    assert ch and ch["raises_realized_risk"] is True and ch["source"] == "caller_supplied"
    assert ch["doi"] == "10.1038/s41587-020-0555-7"
    assert ch["validated"] is True and ch["effect_size"] == "moderate"


def test_chromatin_validation_matched_celltype_result():
    # v6.10.3: the cell-type-matched (HEK293T DNase) controlled test SETTLES it, accessibility predicts WT-Cas9
    # cell-based off-target activity (moderate). The cross-cell K562 proxy underperformed; the in-vitro control is null.
    from pen_stack.wgenome.offtarget_data import CHROMATIN_VALIDATION as cv
    assert cv["validated"] is True and cv["effect"] == "moderate"
    res = cv["auroc_accessibility_for_activity"]
    # cell-type matching LIFTED the canonical WT-Cas9 cell-based assay above its cross-cell proxy, CI excludes 0.5
    assert res["guideseq"]["auroc"] > res["guideseq"]["k562_cross_cell"]
    assert res["guideseq"]["ci95"][0] > 0.5
    # the in-vitro negative control stays ~0.5 even with the matched track (method has no spurious signal)
    assert abs(res["siteseq"]["auroc"] - 0.5) < 0.05 and res["siteseq"]["modality"] == "in_vitro_control"
    # v6.10.4: accessibility carries a small REAL conditional signal but does NOT improve held-out ranking over
    # CRISOT -> it is an annotation, NOT a re-ranker (the numeric risk score is unchanged)
    inc = cv["incremental_over_crisot"]
    assert inc["adds_conditional_signal"] is True and inc["conditional_acc_coef_ci95"][0] > 0 # signal is real
    assert inc["improves_ranking"] is False and inc["heldout_auprc_gap_ci95"][0] < 0 # but not for ranking
    assert cv["changes_numeric_risk_score"] is False


def test_integrase_pseudo_attb_scan_uses_real_core():
    from pen_stack.atlas.guide_design import _INTEGRASE_ATT
    attb = _INTEGRASE_ATT["Bxb1"]["attB"]
    seq = "AAAA" + attb + "TTTTTTTT" + attb[:25] + "CC" + attb[27:] + "GG" # 1 exact + 1 arm-mismatched
    ps = pseudo_attb_sites(seq, "Bxb1")
    assert ps["available"] is True and ps["att_core"] == "GCGGTCTC"
    assert ps["n_candidates"] >= 1 and ps["nominations"][0]["arm_mismatch"] == 0
    assert "Cryptic-seq" in ps["validating_assay"]


def test_dispatcher_bridge_delegates_and_nomination_not_clearance():
    d = nominate_offtargets("bridge_IS110")
    assert d["family"] == "bridge_IS110" and d["delegated_to"] == "pen_stack.bridge.offtarget"
    assert d["nomination_is_not_clearance"] is True
    # cas9 dispatch carries a recommended assay + the not-clearance flag
    rows = [r for r in bench_records() if r["guide"] == "FANCF" and r["assay"] == "guideseq"]
    d2 = nominate_offtargets("Cas9", guide=rows[0]["On"], candidate_sites=[r["Off"] for r in rows[:5]])
    assert d2["family"] == "nuclease" and d2["recommended_assay"]["available"] is True
    assert d2["nomination_is_not_clearance"] is True


# ---- E-WS3: assay recommendation --------------------------------------------------------------
def test_assay_recommender_grounded_and_honest_bridge_gap():
    nuc = recommend_assay("Cas9")
    assert nuc["available"] is True
    assert {a["assay"] for a in nuc["recommended"]} >= {"GUIDE-seq", "CHANGE-seq"}
    integ = recommend_assay("Bxb1")
    assert "Cryptic-seq" in integ["recommended"][0]["assay"]
    bridge = recommend_assay("bridge_IS110")
    # honest gap: no genome-wide unbiased off-target assay exists for bridge recombinases
    assert "no published genome-wide unbiased assay or predictor" in bridge["note"].lower() \
        or "unmodeled" in bridge["note"].lower()


# ---- E-WS4: Off-Target-Bench joins the Genome-Writing Challenge --------------------------------
def test_offtarget_task_in_challenge_and_reference_solves_it():
    from benchmarks.genome_writing_challenge.harness import (
        evaluate,
        reference_submission,
    )
    r = evaluate(reference_submission())
    assert "offtarget" in r["by_family"] # the off-target task is in the round
    assert r["by_family"]["offtarget"] == 1.0 # the validated reference nominates correctly
    assert r["aggregate"] == 1.0 and r["no_fabrication"] is True
    # a nonsense submission cannot match the held-out wet-lab label (non-circular)
    from benchmarks.genome_writing_challenge.harness import Submission
    junk = Submission(name="junk",
                      predict_fn=lambda pi: "ZZZZZZZZZZZZZZZZZZZZZZZ" if pi["family"] == "offtarget" else None)
    assert evaluate(junk)["by_family"].get("offtarget", 0.0) == 0.0
