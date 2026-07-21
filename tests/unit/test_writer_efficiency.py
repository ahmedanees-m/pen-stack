"""Curated writer-efficiency dataset + bench + learned predictor + guide design + variant
critique.

CI-safe: the curated dataset is reproducible in-code (`writer_efficiency.records()`), the predictor evaluates on
it, and guide/variant logic is pure, no gitignored artifact required. The pre-registered outcome (the
learned model wins on held-out LOCUS but not held-out FAMILY at N=42/4-families -> retain the KB ranking) is
asserted, including the negative.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pen_stack.atlas import guide_design as gd
from pen_stack.atlas import writer_efficiency as we
from pen_stack.atlas import writer_predict as wp
from pen_stack.design import writer_variants as wv

_ROOT = Path(__file__).resolve().parents[2]


# ---- dataset provenance + no fabrication ------------------------------------------------
def test_dataset_every_row_has_doi_quote_and_provenance():
    df = we.records()
    assert len(df) >= 40 and df["family"].nunique() == 4
    assert df["doi"].str.len().gt(0).all() # every row carries a DOI
    assert df["quote"].str.len().gt(5).all() # ...and a verbatim source quote
    assert set(df["source_access"]) <= {"pmc_verbatim", "abstract", "secondary"}
    assert (df["efficiency_pct"].between(0, 100)).all() # real efficiencies, no out-of-range fabrication
    # the majority are open-access verbatim (highest confidence)
    assert (df["source_access"] == "pmc_verbatim").sum() >= 30


def test_strict_subset_drops_secondary_sources():
    strict = we.human_cell(strict=True)
    assert (strict["source_access"] != "secondary").all()
    assert len(we.human_cell(strict=False)) > len(strict) # secondary rows exist and are droppable


# ---- learned predictor + the gate ------------------------------------------------
def test_predictor_beats_baseline_on_locus_not_family_retains_kb():
    rep = wp.evaluate()
    # held-out LOCUS: the learned model beats the KB family-mean baseline (CI excludes 0)
    loc = rep["held_out_locus"]
    assert loc["mae_model"] < loc["mae_baseline_family_mean"]
    assert loc["delta"]["model_beats_baseline"] is True
    # held-out FAMILY: the NEGATIVE result, not a both-axes win (CI includes 0), but it ranks better
    fam = rep["held_out_family"]
    assert fam["spearman_model"] > fam["spearman_baseline"] # learned ranks families better
    # gate: retain the KB ranking (do not manufacture a both-axes win)
    assert rep["gate_C_G2"]["ship_learned_model"] is False
    assert "RETAIN the KB ranking" in rep["gate_C_G2"]["verdict"]


def test_predictor_never_extrapolates_efficiency_to_unseen_family():
    from pen_stack.atlas.writer_recommend import recommend_writers
    r = recommend_writers({"cargo_bp": 5000, "cell_type": "HEK293T"}, top_k=8)
    seen = set(wp.WriterEfficiencyModel().fit().meta["families"])
    for rec in r["recommendations"]:
        if rec["family"] not in seen:
            assert "predicted_efficiency_pct" not in rec # KB-only for unseen families, no fabrication
    assert r["no_fabrication"] is True


def test_write_type_reweights_ranking_by_mechanism():
    # write_type now shapes the ranking by MECHANISM (a grounded tier, not an efficacy claim): an insertion
    # favours a cargo-carrying writer; an excision favours a programmable cutter. The selector is no longer inert.
    from pen_stack.atlas.writer_recommend import recommend_writers
    ins = recommend_writers({"write_type": "insertion", "cargo_bp": 2000}, top_k=8)
    exc = recommend_writers({"write_type": "repeat_excision"}, top_k=8)
    assert ins["recommendations"][0]["cargo_capacity_bp"]              # insertion -> a cargo carrier tops
    assert exc["recommendations"][0]["cargo_capacity_bp"] is None      # excision -> a programmable cutter tops
    assert ins["recommendations"][0]["family"] != exc["recommendations"][0]["family"]
    assert exc["write_type_note"] and "excision" in exc["write_type_note"]
    # inversion is NOT a no-op alias for "everything suitable": only site-specific recombinases invert cleanly, so
    # a recombinase tops while the CAST transposase and the DSB nucleases are flagged tier-0 with a note.
    inv = recommend_writers({"write_type": "inversion"}, top_k=8)
    assert inv["recommendations"][0]["family"] in {"serine_integrase", "PE_integrase", "bridge_IS110", "seek_IS1111"}
    assert inv["write_type_note"] and "inversion" in inv["write_type_note"]
    suit = {r["family"]: r["write_type_suitability"] for r in inv["recommendations"]}
    assert suit.get("CAST_VK") == 0 and suit.get("Cas9") == 0        # transposase + nuclease are not the mechanism
    assert suit.get("serine_integrase") == 1 and suit.get("bridge_IS110") == 1
    assert any(v == 0 for v in suit.values()) and any(v == 1 for v in suit.values())  # genuine reweight, not all-1


def test_variants_panel_honours_integrase_filter():
    # the /writer/variants `panel` field must respect the integrase filter (was: always the full Bxb1+PhiC31 panel).
    from pen_stack.design import writer_variants as wv
    full = wv.hyperactive_panel()
    bxb1 = wv.hyperactive_panel("Bxb1")
    assert {v["integrase"] for v in bxb1.values()} == {"Bxb1"} and len(bxb1) < len(full)
    assert all(v["integrase"] == "PhiC31" for v in wv.hyperactive_panel("PhiC31").values())


def test_cargo_capacity_warning_when_nothing_fits():
    # Finding D: a cargo larger than EVERY writer's capacity must not let a nuclease read as a silent #1 pick --
    # the response carries an explicit warning. A cargo that some writer can hold carries no warning.
    from pen_stack.atlas.writer_recommend import recommend_writers
    huge = recommend_writers({"cargo_bp": 500000, "cell_type": "HEK293T"}, top_k=8)
    assert huge["cargo_capacity_warning"] and "carries" in huge["cargo_capacity_warning"]
    ok = recommend_writers({"cargo_bp": 3000, "cell_type": "HEK293T"}, top_k=8)
    assert ok["cargo_capacity_warning"] is None


# ---- guide / att design recovery --------------------------------------------------------
def test_bridge_rna_roundtrip_and_core_matching():
    assert gd.recover_bridge_rna("ACGTACGTACGTACGT", "ACGTACGTACGTACGT") is True # TBL revcomps to target
    assert gd.design_bridge_rna("ACGTAAGTACGT", "ACGTCCGTACGT").core_matched is False # mismatched core infeasible


def test_serine_att_core_and_orthogonality():
    d = gd.design_pegrna_attb("GGACTGACTGACTGACTGAC", "Bxb1")
    assert d.att_core == "GT" # documented Bxb1 central crossover
    # the REAL documented Bxb1 minimal attB is written verbatim (FlyBase/Ghosh 2003), not a schematic
    assert d.written_att == "TCGGCCGGCTTGTCGACGACGGCGGTCTCCGTCGTCAGGATCATCCGGGC"
    assert "GCGGTCTC" in d.written_att and "GT" in d.written_att # 8-bp common core around the central GT
    assert gd.revcomp(d.pe_3prime_extension) == d.written_att # PE 3' extension is revcomp of the attB
    o = gd.select_orthogonal_att_pairs(3)
    assert o["orthogonal"] is True and o["selected_cores"][0] == "GT"


def test_guide_design_surfaces_sequences_and_real_feasibility():
    # Level-1 fix: the designer must SURFACE the designed sequences (not a bare flag) and a real per-input
    # feasibility. Bxb1 + a >=20 nt target writes the documented attB (feasible); PhiC31 has no bundled attB
    # so it is NOT feasible (a site is never fabricated); a bridge family surfaces both loops.
    from pen_stack.atlas.guide_design import design_guide_for_writer
    ok = design_guide_for_writer("serine_integrase", "ACGTACGTACGTACGTACGTAC", integrase="Bxb1")
    assert ok["available"] and ok["design_type"] == "pegrna_attb" and ok["feasible"] is True
    assert "GCGGTCTC" in ok["design"]["written_att"]                 # the real documented attB is surfaced
    assert ok["design"]["pegrna_spacer"] and ok["design"]["pe_3prime_extension"]
    phi = design_guide_for_writer("serine_integrase", "ACGTACGTACGTACGTACGTAC", integrase="PhiC31")
    assert phi["has_full_att"] is False and phi["feasible"] is False  # no bundled attB -> infeasible
    br = design_guide_for_writer("bridge_IS110", "ACGTACGTACGTACGT", "ACGTACGTACGTACGT")
    assert br["design"]["target_binding_loop"] and br["feasible"] is True  # matched cores -> feasible


# ---- variant critique (hyperactive mutant recovery) -------------------------------------
def test_hyperactive_recovery_and_no_fabrication():
    rec = wv.hyperactive_recovery("Bxb1")["by_integrase"]["Bxb1"]
    assert rec["top"] == "Bxb1_c22" and rec["all_hyperactive_outrank_wt"] is True
    assert wv.hyperactive_recovery("PhiC31")["by_integrase"]["PhiC31"]["top"] == "PhiC31_P3-L1-2"
    # the LM-vs-conservation blind claim defers (LM naturalness != hyperactivity), never fabricates
    assert wv.lm_recovery()["available"] is False
    # an unmeasured variant is NOT claimable
    s = {x.variant: x for x in wv.score_writer_variants("Bxb1", ["c22", "ZZ9Z"])}
    assert s["c22"].claimable is True and s["ZZ9Z"].claimable is False


# ---- bench sealed + SHA-locked ----------------------------------------------------------
def test_writer_bench_sealed_and_sha_locked():
    root = _ROOT / "benchmarks/writer_efficiency"
    sums = dict(line.split()[::-1] for line in (root / "SHA256SUMS").read_text(encoding="utf-8").split("\n") if line.strip())
    split_sha = hashlib.sha256((root / "split.json").read_bytes()).hexdigest()
    assert sums["split.json"] == split_sha # the split spec is frozen + checksummed
    spec = json.loads((root / "split.json").read_bytes())
    assert spec["axes"]["held_out_family"]["families"] == ["PE_integrase", "serine_integrase", "bridge_IS110", "CAST_VK"]
