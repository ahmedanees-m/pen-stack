"""pen_stack.design, the grounded generative designer (v5.8).

Generate candidate end-to-end writing systems, keep only those that pass safety + legality + calibration
(verifier-as-discriminator), and return the Pareto frontier of real tradeoffs, including an immune-risk axis
grounded in the v5.6 profile. Nothing unvalidated is asserted: every survivor is `output_kind="candidate"`.
"""
from __future__ import annotations

from pen_stack.design.generate import generate_designs
from pen_stack.design.pareto import AXES, neg_immune_risk, pareto_front
from pen_stack.design.space import candidate_space, deliverability_score

__all__ = ["generate_designs", "candidate_space", "deliverability_score",
           "pareto_front", "neg_immune_risk", "AXES"]
