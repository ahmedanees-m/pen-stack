"""Inverse-design optimiser with edit_intent.

Pre-registered criterion: edit_intent changes the ranking sensibly - an in-gene site ranks high for
knock_in_with_disruption and low for safe_harbour_insertion. Uses a synthetic candidate frame (offline)
plus, when present, the writability atlas for an end-to-end check.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pen_stack.planner.optimize import EditIntent, plan, score_candidates

_ATLAS_DIR = Path(__file__).resolve().parents[2].parent / "phase_1" / "out"
_WDF = _ATLAS_DIR / "atlas_k562.parquet"
_HAVE_HSPC = _WDF.exists() and (_ATLAS_DIR / "atlas_hspc.parquet").exists()


def _synthetic():
    # two sites: one inside the target gene (on_target), one safe off-target
    return pd.DataFrame({
        "chrom": ["chr14", "chr14"],
        "bin": [100, 200],
        "safety": [0.6, 1.0],
        "p_durable": [0.8, 0.9],
        "reachable_tier1": ["bridge_IS110;Cas9;Cas12a", "bridge_IS110;Cas9;Cas12a"],
        "on_target": [True, False],
    })


def test_intent_flips_on_target_ranking():
    cands = _synthetic()
    ki = score_candidates(cands, EditIntent.KNOCK_IN_DISRUPT, cargo_bp=2000)
    sh = score_candidates(cands, EditIntent.SAFE_HARBOUR, cargo_bp=2000)
    # knock-in rewards the on-target site -> it ranks first; safe-harbour penalises it -> ranks last
    assert bool(ki.iloc[0]["on_target"]) is True
    assert bool(sh.iloc[0]["on_target"]) is False


def test_components_and_writer_retained():
    out = score_candidates(_synthetic(), EditIntent.HIGH_DURABILITY, cargo_bp=2000)
    for col in ("safety", "p_durable", "writer", "writer_activity", "score", "cargo_ok"):
        assert col in out.columns
    assert set(out["writer"]) <= {"bridge_IS110", "Cas9", "Cas12a"}


def _synthetic_unsafe():
    # a genotoxic on-target site (safety=0) that is MORE durable, vs a safe off-target site
    return pd.DataFrame({
        "chrom": ["chr11", "chr11"], "bin": [100, 200],
        "safety": [0.0, 1.0], "p_durable": [0.99, 0.6],
        "reachable_tier1": ["bridge_IS110;Cas9", "bridge_IS110;Cas9"],
        "on_target": [True, False],
    })


def test_all_frontend_intents_resolve_incl_landing_pad_and_legacy_alias():
    # Two of six dropdown intents used to 422. Every frontend intent (+ the old alias) must resolve.
    for v in ("safe_harbour_insertion", "knock_in_with_disruption", "high_durability_insertion",
              "regulatory_element_excision", "landing_pad_insertion", "repeat_excision", "regulatory_excision"):
        assert EditIntent(v) is not None


def test_safety_floor_demotes_genotoxic_for_gene_avoiding_intents():
    # A safe-harbour / landing-pad intent must NOT top-rank a genotoxic site even if it is the most
    # durable; it is flagged `genotoxic` and demoted below the safe site.
    out = score_candidates(_synthetic_unsafe(), EditIntent.SAFE_HARBOUR, cargo_bp=2000)
    assert "genotoxic" in out.columns
    assert bool(out.iloc[0]["genotoxic"]) is False and float(out.iloc[0]["safety"]) >= 0.5
    assert bool(out[out["safety"] < 0.5].iloc[0]["genotoxic"]) is True


def test_genotoxic_flagged_even_when_intended_on_target():
    # For a gene-TARGETING intent the unsafe on-target is the user's choice -> FLAGGED, not hidden.
    out = score_candidates(_synthetic_unsafe(), EditIntent.HIGH_DURABILITY, cargo_bp=2000)
    assert bool(out[out["on_target"]].iloc[0]["genotoxic"]) is True


def test_resolve_gene_is_case_insensitive():
    # New finding: 'lmo2' silently missed the uppercase 'LMO2' in the coords table -> 0 loci and a misleading
    # "gene may be unrecognized". resolve_gene must map any case (and stray whitespace) to the symbol as STORED,
    # preserving legitimately mixed-case symbols (e.g. C1orf43) rather than blindly upper-casing.
    from pen_stack.planner.optimize import _gene_coords, gene_coords_path, resolve_gene
    if not gene_coords_path().exists():
        pytest.skip("gene_coords table not present")
    sym = str(_gene_coords()["gene"].iloc[0])  # a symbol actually in the table, whatever its casing
    assert resolve_gene(sym.lower()) == sym
    assert resolve_gene(sym.upper()) == sym
    assert resolve_gene(f"  {sym.lower()}  ") == sym  # surrounding whitespace tolerated


@pytest.mark.skipif(
    not _WDF.exists(),
    reason="writability atlas absent - run 'make fetch' (scripts/fetch_artifacts.sh) to download it "
           "from Zenodo; the science does not execute without it")
def test_end_to_end_trac():
    wdf = pd.read_parquet(_WDF)
    ki = plan("TRAC", EditIntent.KNOCK_IN_DISRUPT, 2000, wdf, k=5)
    assert not ki.empty
    assert bool(ki.iloc[0]["on_target"]) # knock-in ranks an in-TRAC site at the top


@pytest.mark.skipif(
    not _HAVE_HSPC,
    reason="writability atlas (k562 + hspc) absent - run 'make fetch' (scripts/fetch_artifacts.sh) to "
           "download it from Zenodo; the science does not execute without it")
def test_hspc_partial_safety_is_conservative_not_fail_unsafe():
    # HSPC (partial coverage) must NOT claim safe where the full-coverage atlas flags a genotoxic bin.
    # Near the LMO2 oncogene, the corrected HSPC safety must be low (was fail-unsafe = 1.0 for many bins).
    from pen_stack.atlas.crosslink import load_writability
    h = load_writability("hspc")
    h = h.assign(chrom=h["chrom"].astype(str))
    lmo2 = h[(h["chrom"] == "chr11") & (h["bin"].between(33858, 33892))]
    assert not lmo2.empty
    assert float(lmo2["safety"].max()) <= 0.5           # conservative floor: no fail-unsafe LMO2 bin
    assert "safety_coverage" in h.columns               # the correction is disclosed, not silent
    assert "safety_raw" in h.columns                    # the raw per-ct value is retained for transparency
