"""v3.1 WS-D - Cargo Polish. Pure-logic, no network/atlas; runs always (ViennaRNA optional, degrades)."""
from __future__ import annotations

from pen_stack.planner.cargo_polish import cpg_islands, scan_cargo
from pen_stack.validate.cargo_directionality import run as directionality


def test_directionality_and_every_flag_has_a_suggestion():
    r = directionality()
    assert r["directionality_ok"] is True # high-CpG > CpG-depleted/insulated
    assert r["risk"]["bacterial_high_cpg"] > r["risk"]["mammalian_cpg_depleted"]
    assert r["all_flags_have_suggestions"] is True # actionability bar


def test_cpg_island_detected_in_dense_cpg_and_absent_in_depleted():
    assert cpg_islands("GCGCGGCGGCGCGCGGCGG" * 20) # dense CpG -> island(s)
    assert cpg_islands("GACAAGCTGGAAGAACTGAAG" * 20) == [] # CG-free -> none


def test_scan_is_bounded_and_self_describing():
    s = scan_cargo("GCGCGGCGGCGCGCGGCGG" * 20)
    assert 0.0 <= s["cargo_durability_risk"] <= 1.0
    assert s["band"] in {"low", "moderate", "high"}
    assert all(set(f) >= {"category", "detail", "suggestion"} for f in s["flags"])
    assert "not a supervised" in s["scope"]


def test_empty_and_nonsense_sequence_safe():
    assert scan_cargo("")["cargo_durability_risk"] == 0.0
    assert scan_cargo("NNNNNNNNNN")["length_bp"] == 0 # non-ACGT stripped


def test_design_cargo_attaches_polish_when_seq_given():
    from pen_stack.planner.cargo import design_cargo
    wr = {"family": "PE_integrase", "cargo_capacity_bp": 36000, "deliv_class": "AAV"}
    base = design_cargo(2000, wr, ("chr1", 1000), "k562")
    assert "cargo_polish" not in base # opt-in
    withseq = design_cargo(2000, wr, ("chr1", 1000), "k562", payload_seq="GCGCGGCGG" * 30)
    assert "cargo_polish" in withseq and withseq["cargo_polish"]["n_flags"] >= 1
