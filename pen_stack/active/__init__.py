"""pen_stack.active — the experiment designer / the "Learn" brain of a self-driving lab (v5.10).

Turn "I'm uncertain" into "run THIS experiment next": score each candidate experiment by the information it is
expected to yield (from the calibrated v5.9 twin), reward experiments that would validate an immune PROXY axis
(v5.6), assemble a diverse batch, and prove on held-out data — with confidence intervals — that this learns
faster than random or greedy, reporting honestly when it does not. Lab-optional, falsifiable by construction.
"""
from __future__ import annotations

from pen_stack.active.acquire import (
    acquisition_score,
    expected_information_gain,
    immune_voi,
    predictive_entropy,
)
from pen_stack.active.design import batch_diversity, select_batch
from pen_stack.active.validate import retrospective_active_learning

__all__ = ["expected_information_gain", "immune_voi", "predictive_entropy", "acquisition_score",
           "select_batch", "batch_diversity", "retrospective_active_learning"]
