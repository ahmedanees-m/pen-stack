"""Local recalibration / private-data adaptation (v3.1, WS-F).

Released PEN-STACK models can be recalibrated (or lightly fine-tuned) on a user's own assays - inside
Docker, on private data that never leaves the machine - behind a VALIDATION GATE so quality cannot silently
regress. The adapted artifact activates only if it beats the released model on the user's held-out split;
the released model is never overwritten (separate versioning under models/local_<id>/).
"""
from __future__ import annotations

from pen_stack.adapt.pipeline import adapt
from pen_stack.adapt.recalibrate import IsotonicCalibrator, recalibrate
from pen_stack.adapt.report import evaluate, gate, model_card

__all__ = ["adapt", "IsotonicCalibrator", "recalibrate", "evaluate", "gate", "model_card"]
