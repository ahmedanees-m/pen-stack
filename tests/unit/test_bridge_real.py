"""Phase 1.5 - validation on the REAL Perry 2025 data.

Skips automatically when the (copyrighted, not-committed) Perry supplementary is absent, so CI stays green
without it; runs the measured-profile + discrimination + DMS checks when the tables are present locally.
"""
from __future__ import annotations

import pytest

from pen_stack.bridge.ingest import load_insertion_sites

pytestmark = pytest.mark.skipif(load_insertion_sites().empty, reason="Perry 2025 supplementary not present")


def test_measured_profile_confirms_central_core():
    from pen_stack.validate.paper4_real_validation import measured_profile
    mp = measured_profile()
    assert mp["available"] is True
    assert mp["central_core_confirmed"] is True # positions 7-9 are most conserved
    assert set(mp["most_critical_positions"]) & {7, 8, 9}


def test_discrimination_beats_hamming_on_real_offtargets():
    from pen_stack.validate.paper4_real_validation import discrimination_auroc
    d = discrimination_auroc()
    assert d["model_beats_hamming"] is True
    assert d["model_auroc"] > d["hamming_auroc"]


def test_dms_recovers_enhancers():
    from pen_stack.validate.paper4_real_validation import dms_enhancers
    e = dms_enhancers()
    assert e["available"] is True
    assert e["n_enhancing"] > 0
    assert e["top_enhancers"][0]["z"] > 0 # top mutation is activity-enhancing
