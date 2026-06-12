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


def test_evo2_generate_is_deferred_offline_and_never_fabricates(monkeypatch):
    # with the live oracle network OFF (CI default), Evo2 generation defers: a CANDIDATE with no fabricated value
    monkeypatch.delenv("PEN_STACK_ORACLE_NET", raising=False)
    r = genome.generate_dna("ACGTACGTACGT", n=8)
    assert r.is_candidate and r.value is None and r.available is False


def test_evo2_live_path_parses_hosted_response_into_a_candidate(monkeypatch, tmp_path):
    # the LIVE wiring (PEN_STACK_ORACLE_NET=1): a hosted Evo2-40B response is parsed into a CANDIDATE with the
    # generated DNA + per-token-probability-derived uncertainty, cached, and STILL guarded (as_claim raises).
    monkeypatch.setenv("PEN_STACK_ORACLE_NET", "1")
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(genome, "cache_put", lambda *a, **k: None)      # don't touch disk in CI
    monkeypatch.setattr(genome, "_call_evo2_generate",
                        lambda seed, n: {"sequence": "CAGGCAT", "sampled_probs": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3],
                                         "elapsed_ms": 42})
    r = genome.generate_dna("ATGGCG", n=7)
    assert r.available and r.provenance.source == "hosted_api" and r.provenance.model == "evo2"
    assert r.is_candidate and r.value["generated"] == "CAGGCAT" and r.value["seed"] == "ATGGCG"
    assert r.value["full"] == "ATGGCGCAGGCAT" and r.value["n_tokens"] == 7
    assert abs(r.native_uncertainty - (1 - 0.6)) < 1e-6        # 1 - mean(per-token prob)
    with pytest.raises(ValueError):
        r.as_claim()                                          # a generated sequence is a candidate, not a claim


def test_evo2_live_falls_back_to_deferred_when_hosted_call_fails(monkeypatch):
    # a hosted failure must degrade to an honest deferred CANDIDATE, never a fabricated sequence
    monkeypatch.setenv("PEN_STACK_ORACLE_NET", "1")
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    def _boom(seed, n):
        raise RuntimeError("hosted 503")
    monkeypatch.setattr(genome, "_call_evo2_generate", _boom)
    r = genome.generate_dna("ATGGCG", n=7)
    assert r.is_candidate and r.value is None and r.available is False


def test_live_oracle_status_surface_is_honest(monkeypatch):
    # v6.4: the execution/latency map covers every wrapped model and the status reflects the live conditions
    monkeypatch.delenv("PEN_STACK_ORACLE_NET", raising=False)
    from pen_stack.oracles.status import execution_map, oracle_status, summary
    em = execution_map()
    assert {"viennarna", "alphagenome", "evo2", "proteinmpnn", "esm3", "rfdiffusion", "state",
            "alphafold3", "boltz-2", "chai-1", "protenix"} <= set(em)
    for card in em.values():
        assert card.get("execution") and card.get("latency_class") in {"instant", "seconds", "slow", "long_job"}
    st = oracle_status(probe=False)
    assert st["viennarna"]["live"] is True                       # in-process, always live
    assert st["alphagenome"]["live"] is False                    # needs PEN_STACK_ORACLE_NET=1 (off here)
    assert st["alphafold3"]["execution"] == "cloud_a100" and st["alphafold3"]["live"] is False  # HELD
    assert st["state"]["execution"] == "deferred" and st["state"]["live"] is False              # honest defer
    s = summary()
    assert "viennarna" in s["live"] and set(s["held_cloud"]) == {"alphafold3", "boltz-2", "chai-1", "protenix"}


def test_hosted_oracle_goes_live_when_enabled(monkeypatch):
    # with the flag on + a key present, the hosted oracles report live (config-level, no network call)
    monkeypatch.setenv("PEN_STACK_ORACLE_NET", "1")
    monkeypatch.setenv("NVIDIA_API_KEY", "x")
    monkeypatch.setenv("ALPHAGENOME_API_KEY", "y")
    from pen_stack.oracles.status import oracle_status
    st = oracle_status(probe=False)
    assert st["evo2"]["live"] is True and st["alphagenome"]["live"] is True


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
