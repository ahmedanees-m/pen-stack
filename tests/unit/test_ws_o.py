"""WS-O unit tests (Phase 4.0) - the oracle mesh contract + adapters. Pure-logic / contract-level, CI-safe
(heavy oracle backends absent -> adapters defer; the contract + guards are what is tested here)."""
from __future__ import annotations

import pytest

from pen_stack.oracles import build_result, consensus
from pen_stack.oracles import genome, protein_design, rna, structure
from pen_stack.oracles.cache import cache_key, load_scope_cards
from pen_stack.oracles.schema import OracleResult, Provenance


def test_scope_cards_cover_every_wrapped_model():
    cards = load_scope_cards()
    for m in ("alphagenome", "evo2", "alphafold3", "boltz-2", "chai-1", "protenix",
              "esm3", "rfdiffusion", "proteinmpnn", "viennarna", "bridge_energetics"):
        assert m in cards, m
        assert cards[m]["output_kind"] in ("claim", "candidate", "baseline")
        assert "valid_for" in cards[m] and "not_valid_for" in cards[m]


def test_cache_key_is_deterministic_and_version_pinned():
    k1 = cache_key("structure", "boltz-2", "2.0-2025", {"seq": "ACGT"})
    k2 = cache_key("structure", "boltz-2", "2.0-2025", {"seq": "ACGT"})
    k3 = cache_key("structure", "boltz-2", "9.9", {"seq": "ACGT"})        # version change -> new key
    assert k1 == k2 and k1 != k3


def test_generative_output_is_candidate_and_cannot_become_a_claim():
    # the encoded pen-assemble lesson: generated outputs cannot enter a claim path unverified
    for r in (genome.generate_dna("ATG", 1),
              protein_design.generate_backbone({"len": 200}),
              protein_design.design_sequence({"bb": 1}),
              protein_design.esm3_design({"prompt": "x"})):
        assert r.is_candidate and r.output_kind == "candidate"
        with pytest.raises(ValueError):
            r.as_claim()


def test_claim_scope_oracle_passes_as_claim():
    r = build_result("genome", "alphagenome", value=0.5)          # claim-scope by its card
    assert r.as_claim() is r


def test_alphagenome_is_ood_gated():
    out_of_dist = genome.variant_effect("chr1:1A>T", "novel_locus", in_distribution=False)
    in_dist = genome.variant_effect("chr1:1A>T", "AAVS1", in_distribution=True)
    assert out_of_dist.extrapolating and not out_of_dist.in_scope
    assert in_dist.in_scope and not in_dist.extrapolating


def test_cross_oracle_disagreement_widens_interval():
    agree = [OracleResult(oracle="structure", value=0.90, provenance=Provenance(model="boltz-2", version="2"),
                          native_uncertainty=0.10),
             OracleResult(oracle="structure", value=0.92, provenance=Provenance(model="chai-1", version="1"),
                          native_uncertainty=0.10)]
    disagree = [OracleResult(oracle="structure", value=0.90, provenance=Provenance(model="boltz-2", version="2"),
                             native_uncertainty=0.10),
                OracleResult(oracle="structure", value=0.50, provenance=Provenance(model="chai-1", version="1"),
                             native_uncertainty=0.10)]
    assert consensus(disagree).native_uncertainty > consensus(agree).native_uncertainty


def test_rna_fold_is_real_or_deferred_never_fabricated():
    r = rna.fold("GGGAAACCCUUUGGGAAACCCUUU")
    assert r.oracle == "rna" and r.provenance.model == "viennarna"
    if r.available:
        assert r.value and "structure" in r.value and r.native_uncertainty is not None
    else:
        assert r.value is None                                    # deferred, not fabricated


def test_structure_consistency_defers_cleanly_without_backends():
    r = structure.consistency("MKT" * 20)
    assert r.oracle == "structure"
    # no backends + no cache -> not available, but the contract still returns a typed result
    assert isinstance(r, OracleResult)


def test_energetics_gate_defers_without_perry_data():
    from pen_stack.oracles import energetics
    r = energetics.gate()
    assert r.oracle == "energetics" and r.provenance.model == "bridge_energetics"
    # off the VM the Perry tables are absent -> deferred (not a fabricated AUROC)
    assert r.available in (True, False)
    if r.available:
        assert r.value["held_out_auroc"] is None or r.value["beats_0_77"] in (True, False)
