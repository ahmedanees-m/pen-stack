"""WS-ORACLE (v6.13 PEN-ORACLE) unit tests: the affinity dimension, per-oracle reliability, and the
cross-oracle disagreement-to-interval rule, all under the one oracle contract."""
from __future__ import annotations

from pen_stack.oracles import affinity, reliability, structure_run
from pen_stack.oracles.status import oracle_status, summary


def test_affinity_is_candidate_and_cache_or_abstain():
    # an uncached request defers (no fabrication), never runs the long job on the request path
    r = affinity.predict_affinity("MKVLLAAAAA", "CCO", pair_type="ligand")
    assert r.available is False
    assert r.value is None
    assert r.oracle == "affinity"
    assert r.provenance.model == "boltz-2-affinity"


def test_affinity_flags_protein_protein_and_protein_dna_out_of_scope():
    for pair in ("protein_protein", "protein_dna"):
        r = affinity.predict_affinity("MKVLLA", "CCO", pair_type=pair)
        assert r.extrapolating is True
        assert r.in_scope is False


def test_affinity_unknown_pair_type_raises():
    import pytest
    with pytest.raises(ValueError):
        affinity.predict_affinity("MKVLLA", "CCO", pair_type="not_a_pair")


def test_reliability_reports_published_numbers_verbatim_with_citations():
    fep = reliability.reliability("boltz-2-affinity")[0]
    assert fep["value"] == 0.62  # Boltz-2 FEP+ Pearson r, paper-reported
    assert fep["citation"] == ["10.1101/2025.06.14.659707"]
    assert fep["reported_by"] == "paper"
    # the standing disclaimer makes clear these are published numbers, not a claim about this stack
    assert "not a claim about this stack" in reliability.disclaimer().lower() \
        or "not a claim about this stack's" in reliability.disclaimer().lower()


def test_reliability_does_not_invent_unverified_numbers():
    # where a verbatim score was not verified, the value is null and the benchmark is the cited pointer
    af3 = reliability.reliability("alphafold3")[0]
    assert af3["value"] is None
    assert af3["benchmark"]
    assert af3["citation"]


def test_disagreement_widens_interval_monotonically():
    chk = reliability.disagreement_widens_monotonically()
    assert chk["monotone_nondecreasing"] is True
    uncs = chk["native_uncertainty"]
    assert uncs == sorted(uncs)  # non-decreasing with the spread
    assert uncs[-1] > uncs[0]    # and it actually widens


def test_oracle_status_surfaces_reliability_and_the_affinity_oracle():
    st = oracle_status()
    assert "boltz-2-affinity" in st
    assert st["boltz-2-affinity"]["reliability"][0]["value"] == 0.62
    s = summary()
    assert s["disagreement_to_interval"]["monotone_nondecreasing"] is True
    assert s["reliability_note"]


def test_structure_run_complexes_and_cache_or_abstain():
    cx = structure_run.complexes()
    assert "ert2_4oht" in cx
    # an uncached complex consistency defers (never fabricated)
    assert structure_run.get("MKVLLAAAAA").available is False
