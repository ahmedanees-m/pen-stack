"""Phase 1.5 - off-target engine validation (position model beats naive Hamming)."""
from __future__ import annotations

from pen_stack.validate.paper4_validation import run


def test_model_beats_hamming_auroc():
    r = run()
    assert r["model_beats_hamming"] is True
    assert r["model_auroc"] >= 0.95          # near-perfect core/no-core separation
    assert r["hamming_auroc"] < r["model_auroc"]
    assert r["n_core_preserved"] > 0 and r["n_core_disrupted"] > 0
