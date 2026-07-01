"""PEN-OFFTGT v2 (v7.2, O-WS1/O-WS2): genome-wide enumeration + the nuclease FINDER.

The committed GRCh38 Cas-OFFinder coordinate cache (data/offtarget/enumerated_cache.parquet) makes the finder
work in CI/offline for the canonical guides (replay), so these tests run without a genome scan. Tests that need
the cache skip gracefully on a bare wheel.
"""
import pytest

from pen_stack.wgenome.offtarget_enumerate import (
    build_casoffinder_input,
    enumerate_offtargets,
    enumerated_guides,
    parse_casoffinder_output,
    resolve_enzyme,
)
from pen_stack.wgenome.offtarget_nuclease import find_nuclease_offtargets
from pen_stack.wgenome.offtarget_predict import nominate_offtargets

EMX1 = "GAGTCCGAGCAGAAGAAGAAGGG"  # protospacer + NGG PAM (Tsai 2015 GUIDE-seq)
_have_cache = bool(enumerated_guides())


def test_casoffinder_input_builder_handles_3prime_and_5prime_pam():
    inp = build_casoffinder_input(EMX1, "SpCas9", "/g/GRCh38.fa", 5).splitlines()
    assert inp[0] == "/g/GRCh38.fa"
    assert inp[1] == "N" * 20 + "NGG"                 # 20 guide N + NGG PAM (3')
    assert inp[2] == "GAGTCCGAGCAGAAGAAGAA" + "NNN 5"  # guide + PAM placeholder + mismatches
    cas12a = build_casoffinder_input("A" * 23, "AsCas12a", "/g/GRCh38.fa", 4).splitlines()
    assert cas12a[1].startswith("TTTV")               # Cas12a PAM is 5' of the protospacer


def test_casoffinder_parser_extracts_coords_from_verbose_header():
    # GRCh38 FASTA headers are verbose; the contig name is the first token of the tab-delimited chrom field
    line = "\t".join(["GAGTCCGAGCAGAAGAAGAANNN", "chr2  AC:CM000664.2  AS:GRCh38", "72933852",
                      "GAGTCCGAGCAGAAGAAGAAGGG", "+", "0"])
    recs = parse_casoffinder_output(line, "SpCas9")
    assert recs == [{"guide": "GAGTCCGAGCAGAAGAAGAA", "chrom": "chr2", "position": 72933852,
                     "strand": "+", "sequence": "GAGTCCGAGCAGAAGAAGAAGGG", "n_mismatch": 0}]
    # a bulge/gap row (matched DNA contains '-') is skipped (v2 enumerates substitutions only)
    gap = "\t".join(["GAGTCCGAGCAGAAGAAGAANNN", "chr2", "1", "GAGTCCGAGCAGAAGAAGA-GGG", "+", "1"])
    assert parse_casoffinder_output(gap, "SpCas9") == []


def test_resolve_enzyme_aliases():
    assert resolve_enzyme("cas9") == "SpCas9" and resolve_enzyme("SpCas9") == "SpCas9"
    assert resolve_enzyme("cas12a") == "AsCas12a"
    assert resolve_enzyme("bridge_IS110") is None  # not a nuclease


def test_finder_abstains_honestly_on_a_novel_guide():
    r = enumerate_offtargets("ACGTACGTACGTACGTACGTAGG", "SpCas9")
    assert r["abstain"] and r["source"] == "none"
    assert "runs on the VM" in r["note"]  # honest VM/cache pointer, no fabricated sites


@pytest.mark.skipif(not _have_cache, reason="enumeration cache absent (bare wheel)")
def test_enumeration_cache_replays_emx1_with_on_target():
    e = enumerate_offtargets(EMX1, "SpCas9")
    assert e["available"] and e["source"] == "cache" and e["n_sites"] > 100
    on = [s for s in e["sites"] if s["n_mismatch"] == 0]
    assert on and on[0]["chrom"] == "chr2"  # EMX1 on-target locus


@pytest.mark.skipif(not _have_cache, reason="enumeration cache absent")
def test_nuclease_finder_returns_genome_wide_ranked_with_coordinates():
    r = find_nuclease_offtargets(EMX1, "SpCas9", top=5)
    assert r["mode"] == "finder" and r["status"] == "validated" and not r["abstain"]
    assert r["n_on_target"] == 1 and r["n_offtargets"] > 100
    top = r["nominations"][0]
    assert top["n_mismatch"] == 0 and top["chrom"] == "chr2" and "position" in top  # on-target ranked first


@pytest.mark.skipif(not _have_cache, reason="enumeration cache absent")
def test_dispatcher_is_finder_by_default_and_scorer_when_candidates_supplied():
    fnd = nominate_offtargets("Cas9", guide=EMX1)
    assert fnd["mode"] == "finder" and fnd["recommended_assay"]["available"]
    assert fnd["nomination_is_not_clearance"] is True
    scr = nominate_offtargets("Cas9", guide=EMX1, candidate_sites=[EMX1])
    assert scr["available"] and "mode" not in scr  # backward-compatible v6.10 scorer path


def test_cast_untargeted_background_per_system():
    # O-WS5: CAST off-target = guide-independent untargeted transposition (per-system) + guide-directed. Type V-K
    # (ShCAST) is HIGH untargeted; Type I-F (VchCAST) is LOW. All documented, DOI-tagged, mechanism-unvalidated.
    from pen_stack.wgenome.offtarget_cast import nominate_cast
    sh = nominate_cast("ShCAST")
    vch = nominate_cast("VchCAST")
    assert sh["status"] == "mechanism_based_unvalidated" and vch["status"] == "mechanism_based_unvalidated"
    assert sh["untargeted_background"]["tier"] == "high" and sh["untargeted_background"]["guide_independent"] is True
    assert vch["untargeted_background"]["tier"] == "low"
    assert sh["cast_type"] == "V-K" and vch["cast_type"] == "I-F"
    assert sh["untargeted_background"]["dois"] and sh["confirm_assay"]  # cited + a confirm assay
    assert sh["nomination_is_not_clearance"] is True


def test_bridge_hard_locked_unvalidated_with_disclosure():
    # O-WS4: bridge is hard-locked mechanism_based_unvalidated (no genome-wide cellular assay), but the ranker is
    # DMS-validated (held-out AUROC 0.88) — the disclosure states exactly that distinction.
    from pen_stack.wgenome.offtarget_bridge import nominate_bridge
    r = nominate_bridge()  # no fasta/target -> engine-ready abstain, but the status + disclosure are always present
    assert r["status"] == "mechanism_based_unvalidated"
    assert "no published genome-wide unbiased CELLULAR off-target assay" in r["no_ground_truth_disclosure"].lower() \
        or "no published genome-wide unbiased cellular off-target assay" in r["no_ground_truth_disclosure"].lower()
    assert "0.88" in r["ranker"] and r["nomination_is_not_clearance"] is True


def test_integrase_phic31_is_a_disclosed_data_gap():
    # O-WS3: PhiC31's att/pseudo-attP is a DISCLOSED data gap (not verifiable from an open source in this build) —
    # it abstains with the disclosure + DOI, never fabricates a sequence or a pseudosite coordinate.
    from pen_stack.wgenome.offtarget_integrase import nominate_integrase
    phic31 = nominate_integrase("PhiC31")
    assert phic31["abstain"] and phic31["status"] == "semi_validated" and "disclosure" in phic31
    assert phic31["disclosure"].get("doi")


@pytest.mark.skipif(
    __import__("pen_stack.wgenome.offtarget_enumerate", fromlist=["_motif_cache_df"])._motif_cache_df() is None,
    reason="integrase motif cache absent (bare wheel)")
def test_integrase_bxb1_pseudo_attp_finder_reflects_high_specificity():
    # O-WS3 / O-G2: the Bxb1 genome-wide pseudo-attP scan replays the VM cache. Bxb1 is highly specific, so the
    # scan honestly returns very few candidates (the validated property) — each with a coordinate + att similarity.
    from pen_stack.wgenome.offtarget_integrase import nominate_integrase
    r = nominate_integrase("Bxb1")
    assert r["available"] and r["status"] == "semi_validated" and r["mode"] == "finder"
    assert r["att_core"] == "GCGGTCTC" and r["n_sites_genome_wide"] >= 1
    assert r["specificity_note"] and "position" in r["nominations"][0] and "arm_similarity" in r["nominations"][0]


def test_paste_composes_nuclease_and_integrase_components():
    # O-WS6: PASTE = compose(nuclease nickase, integrase att). Both components returned, each with its own status.
    from pen_stack.wgenome.offtarget_paste import nominate_paste
    r = nominate_paste(guide=EMX1)
    assert r["status"] == "composite"
    assert r["component_statuses"]["nuclease_component"] == "validated"
    assert r["component_statuses"]["integrase_component"] == "semi_validated"
    assert set(r["confirm_assay"]) >= {"nuclease", "integrase"}  # dual confirm assay


def test_dispatcher_routes_all_five_writer_classes():
    from pen_stack.wgenome.offtarget_predict import nominate_offtargets
    cases = {"Cas9": "nuclease", "Bxb1": "serine_integrase", "bridge_IS110": "bridge",
             "ShCAST": "cast", "PASTE": "paste"}
    for fam, expect in cases.items():
        r = nominate_offtargets(fam, guide=EMX1 if fam in ("Cas9", "PASTE") else None)
        assert r["family"] == expect, f"{fam} routed to {r['family']} not {expect}"
        assert r["recommended_assay"]  # every class gets a confirm-assay recommendation
        assert r["nomination_is_not_clearance"] is True


def test_assay_recommender_covers_cast_and_paste():
    from pen_stack.wgenome.offtarget_assay import recommend_assay
    cast = recommend_assay("ShCAST")
    assert cast["available"] and "transposase" in cast["writer_class"].lower()
    paste = recommend_assay("PASTE")
    assert paste["available"] and "prime-editing integrase" in paste["writer_class"].lower()
    assert len(paste["recommended"]) == 2  # dual: nuclease + integrase assay


@pytest.mark.skipif(not _have_cache, reason="enumeration cache absent")
def test_o_g1_enumeration_recovers_documented_emx1_offtargets():
    # O-G1 gate: enumeration reproduces the documented Cas9 off-target set (CRISPOR-like search step).
    from pen_stack.wgenome.offtarget_data import bench_records
    recs = bench_records()
    if not recs:
        pytest.skip("bench fixture not present (bare wheel)")
    docs = {r["Off"].upper() for r in recs
            if r["guide"] == "EMX1" and r["assay"] == "guideseq" and r["active"] == 1 and r["mismatch"] <= 5}
    enumerated = {s["sequence"].upper() for s in enumerate_offtargets(EMX1, "SpCas9")["sites"]}
    recall = len(docs & enumerated) / len(docs)
    assert recall >= 0.90, f"O-G1 recall {recall:.3f} < 0.90"  # observed 1.000
