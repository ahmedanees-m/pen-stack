"""Per-oracle reliability registry (v6.13, WS-ORACLE) + the disagreement-to-interval monotonicity check.

Reliability here is the wrapped model's PUBLISHED accuracy on PUBLIC benchmarks, reported VERBATIM with citation
(``configs/oracles/reliability.yaml``). It is NOT recomputed here and NOT a claim about this stack's own accuracy.
Each oracle output remains a candidate carrying its own native uncertainty; reliability is surfaced precisely so a
confident-looking value is not over-trusted. Where a verbatim number was not independently verified the registry
records ``null`` plus the cited benchmark (the pointer), never a guess.

The module also exposes :func:`disagreement_widens_monotonically`, which confirms the cross-oracle consensus
mechanism (:func:`pen_stack.oracles.consensus`, native uncertainty + half the cross-oracle spread) widens the
reported interval MONOTONICALLY as the spread grows. That is the v6.13 acceptance check for the
disagreement-to-uncertainty rule.
"""
from __future__ import annotations

from functools import lru_cache

from pen_stack._resources import resource


@lru_cache(maxsize=1)
def _doc() -> dict:
    import yaml
    return yaml.safe_load(resource("configs/oracles/reliability.yaml").read_text(encoding="utf-8"))


def reliability(oracle: str) -> list | None:
    """The published-reliability records for one oracle (or None if the oracle is not in the registry)."""
    return _doc()["oracles"].get(oracle)


def all_reliability() -> dict:
    """The full per-oracle reliability registry."""
    return _doc()["oracles"]


def disclaimer() -> str:
    """The standing disclaimer: published numbers, reported verbatim, not a claim about this stack."""
    return _doc()["disclaimer"].strip()


def _num_result(value: float, unc: float):
    from pen_stack.oracles import build_result
    return build_result("structure", "boltz-2", value=value, native_uncertainty=unc, available=True)


def disagreement_widens_monotonically(spreads: list[float] | None = None) -> dict:
    """Confirm :func:`consensus` widens the reported interval monotonically with the cross-oracle spread.

    For each spread ``s`` two numeric oracles are placed symmetrically about a common centre, each with the same
    small native uncertainty; the consensus native uncertainty must be non-decreasing in ``s``. Returns the
    measured sequence and the monotonicity verdict (the gate reports the mechanism as working or broken).
    """
    from pen_stack.oracles import consensus
    spreads = spreads if spreads is not None else [0.0, 0.05, 0.1, 0.2, 0.4]
    centre, member_unc = 0.5, 0.05
    uncs: list[float] = []
    for s in spreads:
        members = [_num_result(centre - s / 2, member_unc), _num_result(centre + s / 2, member_unc)]
        uncs.append(consensus(members, oracle="structure").native_uncertainty)
    monotone = all(uncs[i + 1] >= uncs[i] - 1e-9 for i in range(len(uncs) - 1))
    return {"spreads": spreads, "native_uncertainty": uncs, "monotone_nondecreasing": monotone,
            "rule": "native_uncertainty = max(member native uncertainty) + 0.5 * (max - min) over the "
                    "available numeric oracles"}
