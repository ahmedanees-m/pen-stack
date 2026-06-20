"""v3.1 WS-B - durability baselines + safety primary-metric switch.

Data-dependent checks (TRIP / Phase-1 atlas) skip on CI. Pure-logic checks (rule monotonicity, provider
offline contract) run always and make NO network calls.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

_P1 = Path(__file__).resolve().parents[2].parent / "phase_1"
_TRIP = _P1 / "features" / "trip_with_chromatin.parquet"
_ATLAS = _P1 / "out" / "atlas_k562.parquet"


def test_gsh_rule_score_increases_with_distance():
    from pen_stack.wgenome.gsh_baseline import gsh_rule_score
    near = pd.DataFrame({"dist_tss": [0], "dist_oncogene": [0], "dist_essential": [0]})
    far = pd.DataFrame({"dist_tss": [1e6], "dist_oncogene": [1e6], "dist_essential": [1e6]})
    assert gsh_rule_score(far).iloc[0] > gsh_rule_score(near).iloc[0]
    assert 0.0 <= gsh_rule_score(near).iloc[0] <= gsh_rule_score(far).iloc[0] <= 1.0


def test_provider_offline_makes_no_network_call():
    # offline=True must never touch the network: an uncached request returns available=False.
    from pen_stack.wgenome.providers import AlphaGenomeProvider, smoke
    s = smoke()
    assert set(s) >= {"package_available", "key_present", "available", "cache_dir"}
    p = AlphaGenomeProvider(assembly="mm10")
    r = p.expression("chrZZ", 1, 1, ontology="EFO:0005483", organism="mouse", offline=True)
    assert r["available"] is False and "offline" in r["reason"]


def test_b1_offline_contract():
    # B1 in offline mode is cache-only: it returns a dict and never raises / never calls the API.
    from pen_stack.validate.durability_baselines import endogenous_expression_baseline as b1
    r = b1(offline=True)
    assert isinstance(r, dict) and "available" in r
    if r["available"]: # cache populated locally
        assert r["trip_beats_proxy_by_margin"] in (True, False)
        assert r["cell_line"].startswith("ES-Bruce4")
        # B1 must carry a paired-bootstrap CI on the delta (like B3) so the margin-pass is reported with its
        # significance, not as a bare point estimate.
        assert r["delta_ci95"] is not None and len(r["delta_ci95"]) == 2
        assert r["delta_ci95"][0] <= r["delta"] <= r["delta_ci95"][1]
        assert "delta_ci_excludes_zero" in r and "honest_finding" in r
        assert r["trip_trained_spearman_ci95"] is not None
        assert r["endogenous_proxy_spearman_ci95"] is not None


@pytest.mark.skipif(not _TRIP.exists(), reason="TRIP-with-chromatin not present")
def test_b2_all_marks_beats_best_single():
    from pen_stack.validate.durability_baselines import multimark_ablation
    r = multimark_ablation()
    assert r["available"] is True
    assert r["all_marks_beats_best_single"] is True
    assert r["all_marks_silenced_auroc"] >= r["best_single_mark_silenced_auroc"]


@pytest.mark.skipif(not _ATLAS.exists(), reason="Phase-1 atlas not present")
def test_b3_headline_is_absolute_discrimination_not_delta():
    from pen_stack.wgenome.gsh_baseline import run
    r = run()
    # HEADLINE must be the learned model's ABSOLUTE discrimination with CI + N, never a delta vs the rule.
    assert "headline" in r and "AUROC" in r["headline"] and "95% CI" in r["headline"] and "N=" in r["headline"]
    assert r["auroc_learned_ci95"][0] <= r["auroc_learned_writability"] <= r["auroc_learned_ci95"][1]
    # The distance rule is a QUALITATIVE failure case (near/below chance because harbours are intragenic),
    # NOT a number to headline a delta against. Validated-8 rule score is at/below chance.
    assert "rule_qualitative_finding" in r and "intragenic" in r["rule_qualitative_finding"]
    assert r["auroc_gsh_ruleset_validated_tier"] is not None and r["auroc_gsh_ruleset_validated_tier"] <= 0.5
    # The delta is demoted to a diagnostic and reported WITH its CI (which includes zero - not significant).
    assert "delta_DIAGNOSTIC_not_headline" in r
    assert r["delta_ci95"] is not None and len(r["delta_ci95"]) == 2
    assert "delta_ci_excludes_zero" in r and "honest_finding" in r
    assert "DEMOTED" in r["genotoxic_cis_auroc"] # circular metric must stay demoted
    assert r["n_positives"] >= 16 # scaled gold set
