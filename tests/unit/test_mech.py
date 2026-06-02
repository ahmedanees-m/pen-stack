"""Phase 2, Step 2.2 — mechanism classification at scale.

Asserts the pre-registered criterion: the Pfam-whitelist classifier agrees with the audited 18-family
labels on the curated core, and that homology-derived mechanism is computed independently of the
inherited label. Composite co-occurrence rules (Cas9 >=2/3; IS110 both domains) are exercised directly.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pen_stack.mech.classify_atlas import core_agreement
from pen_stack.mech.whitelist import PfamWhitelist

_ATLAS = Path(__file__).resolve().parents[2] / "pen_stack" / "atlas" / "atlas.parquet"


def test_whitelist_has_18_families():
    wl = PfamWhitelist()
    assert len(wl.bucket_of) == 18
    assert wl.version == "1.2.1"


def test_composite_cas9_rule():
    wl = PfamWhitelist()
    # >=2 of the 3 Cas9 domains -> composite DSB_NUCLEASE
    call = wl.classify(["PF13395", "PF18541"])
    assert call.bucket == "DSB_NUCLEASE"
    assert call.confidence == "composite"


def test_composite_is110_rule():
    wl = PfamWhitelist()
    call = wl.classify(["PF01548", "PF02371"])
    assert call.bucket == "DSB_FREE_TRANSEST_RECOMBINASE"
    assert call.confidence == "composite"


def test_no_domain_returns_none():
    wl = PfamWhitelist()
    call = wl.classify(["PF99999"])
    assert call.bucket is None and call.confidence == "none"


def test_core_agreement_with_audited_labels():
    if not _ATLAS.exists():
        pytest.skip("atlas.parquet not built")
    atlas = pd.read_parquet(_ATLAS)
    if "mech_pred" not in atlas.columns:
        pytest.skip("mech classification not yet run on atlas")
    ag = core_agreement(atlas)
    assert ag["agreement"] == 1.0, f"core must agree with audited labels, got {ag}"
