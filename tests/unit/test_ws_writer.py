"""v6.8 PEN-WRITER, curated writer-efficiency dataset + bench + learned predictor + guide design + variant
critique (C-WS0..C-WS5).

CI-safe: the curated dataset is reproducible in-code (`writer_efficiency.records()`), the predictor evaluates on
it, and guide/variant logic is pure, no gitignored artifact required. The honest, pre-registered outcome (the
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


# ---- C-WS1: dataset provenance + no fabrication ------------------------------------------------
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


# ---- C-WS2: learned predictor + the honest gate ------------------------------------------------
def test_predictor_beats_baseline_on_locus_not_family_retains_kb():
    rep = wp.evaluate()
    # held-out LOCUS: the learned model beats the KB family-mean baseline (CI excludes 0)
    loc = rep["held_out_locus"]
    assert loc["mae_model"] < loc["mae_baseline_family_mean"]
    assert loc["delta"]["model_beats_baseline"] is True
    # held-out FAMILY: the honest NEGATIVE, not a both-axes win (CI includes 0), but it ranks better
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


# ---- C-WS3: guide / att design recovery --------------------------------------------------------
def test_bridge_rna_roundtrip_and_core_matching():
    assert gd.recover_bridge_rna("ACGTACGTACGTACGT", "ACGTACGTACGTACGT") is True # TBL revcomps to target
    assert gd.design_bridge_rna("ACGTAAGTACGT", "ACGTCCGTACGT").core_matched is False # mismatched core infeasible


def test_serine_att_core_and_orthogonality():
    d = gd.design_pegrna_attb("GGACTGACTGACTGACTGAC", "Bxb1")
    assert d.att_core == "GT" # documented Bxb1 central crossover
    # v6.9.2: the REAL documented Bxb1 minimal attB is written verbatim (FlyBase/Ghosh 2003), not a schematic
    assert d.written_att == "TCGGCCGGCTTGTCGACGACGGCGGTCTCCGTCGTCAGGATCATCCGGGC"
    assert "GCGGTCTC" in d.written_att and "GT" in d.written_att # 8-bp common core around the central GT
    assert gd.revcomp(d.pe_3prime_extension) == d.written_att # PE 3' extension is revcomp of the attB
    o = gd.select_orthogonal_att_pairs(3)
    assert o["orthogonal"] is True and o["selected_cores"][0] == "GT"


# ---- C-WS4: variant critique (hyperactive mutant recovery) -------------------------------------
def test_hyperactive_recovery_and_no_fabrication():
    rec = wv.hyperactive_recovery("Bxb1")["by_integrase"]["Bxb1"]
    assert rec["top"] == "Bxb1_c22" and rec["all_hyperactive_outrank_wt"] is True
    assert wv.hyperactive_recovery("PhiC31")["by_integrase"]["PhiC31"]["top"] == "PhiC31_P3-L1-2"
    # the LM-vs-conservation blind claim defers honestly (LM naturalness != hyperactivity), never fabricates
    assert wv.lm_recovery()["available"] is False
    # an unmeasured variant is NOT claimable
    s = {x.variant: x for x in wv.score_writer_variants("Bxb1", ["c22", "ZZ9Z"])}
    assert s["c22"].claimable is True and s["ZZ9Z"].claimable is False


# ---- C-WS1: bench sealed + SHA-locked ----------------------------------------------------------
def test_writer_bench_sealed_and_sha_locked():
    root = _ROOT / "benchmarks/writer_efficiency"
    sums = dict(line.split()[::-1] for line in (root / "SHA256SUMS").read_text(encoding="utf-8").split("\n") if line.strip())
    split_sha = hashlib.sha256((root / "split.json").read_bytes()).hexdigest()
    assert sums["split.json"] == split_sha # the split spec is frozen + checksummed
    spec = json.loads((root / "split.json").read_bytes())
    assert spec["axes"]["held_out_family"]["families"] == ["PE_integrase", "serine_integrase", "bridge_IS110", "CAST_VK"]
