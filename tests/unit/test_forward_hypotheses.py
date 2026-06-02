"""Phase 3, Step 3.6 — forward hypotheses + grounded ranking.

Criterion: hypotheses are concrete (site + writer), registered with a date; numeric fields come from the
validated models (not the LLM); the ranking is produced over cited reviews.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_WDF = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / "atlas_k562.parquet"

pytestmark = pytest.mark.skipif(not _WDF.exists(), reason="Phase-1 writability atlas not present")


def test_hypotheses_are_concrete_and_dated():
    from pen_stack.validate.forward_hypotheses import register_hypotheses
    h = register_hypotheses()
    assert not h.empty
    for col in ("gene", "proposed_chrom", "proposed_pos", "writer", "score", "registered_date"):
        assert col in h.columns
    assert h["status"].eq("novel_prediction").all()
    assert h["registered_date"].notna().all()


def test_grounded_ranking_runs():
    from pen_stack.validate.forward_hypotheses import (
        cited_reviews,
        grounded_pairwise_rank,
        register_hypotheses,
    )
    h = register_hypotheses()
    reviews = cited_reviews(h)
    ranking = grounded_pairwise_rank(h, reviews, use_llm=False)
    assert set(ranking) == set(h["name"])
    # reviews carry citations (grounded)
    assert all("citations" in v for v in reviews.values())
