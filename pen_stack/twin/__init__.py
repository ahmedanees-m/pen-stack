"""pen_stack.twin, the digital twin for genome writing (v5.9).

A calibrated, scope-bounded write-outcome predictor: mechanism where computable (cassette expression), an
in-distribution virtual-cell transcriptional-response estimate (OOD-gated), and an immune-outcome dimension
sourced from the v5.6 profile, fused into one prediction with an interval that widens under OOD and an explicit
boundary at phenotype. A hypothesis engine, grounded where it is weak; never an oracle of truth.
"""
from __future__ import annotations

from pen_stack.twin.calibrate import calibrate_outcome, interval_coverage
from pen_stack.twin.mechanistic import cassette_expression
from pen_stack.twin.outcome import predict_outcome

__all__ = ["predict_outcome", "cassette_expression", "calibrate_outcome", "interval_coverage"]
