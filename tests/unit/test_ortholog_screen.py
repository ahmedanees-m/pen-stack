"""Phase 1.5 (secondary, exploratory) - 72-system ortholog characterisation.

Skips when the (copyrighted) Perry Table S1 is absent. Asserts only what is honest: a descriptive
sequence-similarity organisation, NOT an activity prediction.
"""
from __future__ import annotations

import pytest

from pen_stack.bridge.ingest import load_screen


@pytest.mark.skipif(load_screen().empty, reason="Perry 2025 Table S1 not present")
def test_ortholog_characterisation_is_descriptive():
    from pen_stack.bridge.ortholog_screen import summary
    s = summary()
    assert s["available"] is True
    assert s["exploratory"] is True
    assert s["n_systems"] >= 70                      # ~72 orthologs
    assert "caveat" in s and "NOT an activity predictor" in s["caveat"]
    # sanity: the closest characterised relative IS621 ranks among the most similar to ISCro4
    names = [r["Name"] for r in s["most_similar_to_ref"]]
    assert any(str(n) == "IS621" for n in names)
