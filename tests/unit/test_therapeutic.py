"""Phase 2, Step 2.3 - therapeutic-readiness scoring.

Pre-registered criterion: deliverability classes match known facts (ISCro4 326 aa -> AAV), and every
component (S_Deliv / S_Cargo / S_HumanCell) is retrievable from the row (transparent, not collapsed).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pen_stack.score.recalibrate import load_axes_config
from pen_stack.score.therapeutic import deliverability_class, therapeutic_profile

_ATLAS = Path(__file__).resolve().parents[2] / "pen_stack" / "atlas" / "atlas.parquet"


def test_deliverability_class_known_facts():
    cfg = load_axes_config()
    assert deliverability_class(326, cfg) == "AAV" # ISCro4 -> single AAV
    assert deliverability_class(1368, cfg) == "split-AAV" # SpCas9
    assert deliverability_class(None, cfg) == "unknown"


def test_components_retained():
    if not _ATLAS.exists():
        pytest.skip("atlas.parquet not built")
    atlas = pd.read_parquet(_ATLAS)
    prof = therapeutic_profile(atlas)
    for col in ("deliv_class", "S_Deliv", "S_Cargo", "S_HumanCell", "readiness"):
        assert col in prof.columns
    iscro4 = prof[prof["representative_system"] == "ISCro4"].iloc[0]
    assert iscro4["deliv_class"] == "AAV"
    assert iscro4["S_Deliv"] == 1.0
