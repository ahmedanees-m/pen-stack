"""pen_stack.loop, the closed loop (v5.12), autonomy Level 3.

PEN-STACK generates safe legal designs, predicts their outcomes, chooses the most informative experiments,
exports gated protocols, runs them in the simulated lab or a real one, ingests results through the world-model's
gate, and updates its calibration, twin, and immune labels round after round, detecting when observations drift
from predictions and widening uncertainty rather than over-trusting a stale model. It keeps a human in control at
every gate, never fabricates a number, and stops deliberately at autonomy Level 3.
"""
from __future__ import annotations

from pen_stack.loop.continual import continual_update
from pen_stack.loop.cycle import AUTONOMY_LEVEL, loop_converges_faster_than_random, run_loop
from pen_stack.loop.drift import detect_drift

__all__ = ["run_loop", "continual_update", "detect_drift", "loop_converges_faster_than_random", "AUTONOMY_LEVEL"]
