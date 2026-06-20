"""Machine-readable rules engine for genome writing (v3.3, WS-R). Rules are versioned data in
configs/rules/*.yaml; evaluators (rules/evaluators.py) delegate to the existing validated functions; the
solver (rules/solver.py) returns legality + named reasons. Import evaluators so they register on load."""
from pen_stack.rules import evaluators as _evaluators # noqa: F401 (registers evaluators)
from pen_stack.rules.loader import load_ruleset
from pen_stack.rules.schema import Design, Rule, Ruleset
from pen_stack.rules.solver import evaluate, is_legal, legality_report

__all__ = ["load_ruleset", "Design", "Rule", "Ruleset", "evaluate", "is_legal", "legality_report"]
