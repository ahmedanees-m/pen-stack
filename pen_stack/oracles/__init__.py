"""The L1 oracle mesh (v4.0, WS-O), one contract over the biomolecular foundation models.

`pen_stack.oracles` wraps AlphaGenome / Evo2 / structure predictors (AF3, Boltz-2, Chai-1, Protenix) /
protein-design models (ESM3, RFdiffusion, ProteinMPNN) / ViennaRNA / the bridge energetics model under a
single `OracleResult` contract (value + provenance + native uncertainty + scope card). Heavy backends run
on-demand (hosted API / local GPU) and are cached + version-pinned; when a backend is absent the adapter
returns a *deferred* result (available=False), the core stays runnable offline from cache.
"""
from __future__ import annotations

from typing import Any

from pen_stack.oracles.cache import cache_get, cache_key, cache_put, scope_card
from pen_stack.oracles.schema import OracleResult, Provenance

__all__ = ["OracleResult", "Provenance", "build_result", "consensus", "assert_claimable",
           "cache_get", "cache_key", "cache_put", "scope_card"]


def build_result(oracle: str, model: str, *, value: Any = None, inputs: dict | None = None,
                 native_uncertainty: float | None = None, available: bool = True, cached: bool = False,
                 source: str = "adapter", extrapolating: bool = False, in_scope: bool = True,
                 output_kind: str | None = None, note: str | None = None) -> OracleResult:
    """Assemble an `OracleResult`, filling version / output_kind / scope from the model's scope card.

    `output_kind` defaults to the scope card's, but may be overridden per call (e.g. an Evo2 *likelihood*
    score is a claim-scope scalar, while an Evo2 *generated sequence* is a candidate)."""
    card = scope_card(model) or {}
    key = cache_key(oracle, model, card.get("version", "0"), inputs or {})
    return OracleResult(
        oracle=oracle, value=value,
        provenance=Provenance(model=model, version=card.get("version", "0"), source=source, cache_key=key),
        native_uncertainty=native_uncertainty,
        scope_card=model, in_scope=in_scope, extrapolating=extrapolating,
        output_kind=output_kind or card.get("output_kind", "claim"),
        available=available, cached=cached, note=note)


def assert_claimable(result: OracleResult) -> OracleResult:
    """Guard: a generative candidate cannot enter a claim path without writer-verification (Principle 1)."""
    return result.as_claim()


def consensus(results: list[OracleResult], oracle: str = "structure") -> OracleResult:
    """Cross-oracle self-consistency (v4.0 Principle 3): agreement is a confidence signal, **divergence
    widens the interval**. Combines redundant numeric oracles (e.g. AF3 / Boltz-2 / Chai-1 / Protenix); the
    reported native_uncertainty is increased by the spread across the available oracles."""
    avail = [r for r in results if r.available and isinstance(r.value, (int, float))]
    if not avail:
        return build_result(oracle, "consensus", available=False,
                            note="no available numeric oracle to combine")
    vals = [float(r.value) for r in avail]
    mean = sum(vals) / len(vals)
    spread = (max(vals) - min(vals)) if len(vals) > 1 else 0.0
    base_unc = max((r.native_uncertainty or 0.0) for r in avail)
    card = scope_card("boltz-2") or {}
    return OracleResult(
        oracle=oracle, value=round(mean, 4),
        provenance=Provenance(model="consensus", version=card.get("version", "0"), source="adapter",
                              extra={"members": [r.provenance.model for r in avail], "spread": round(spread, 4)}),
        # disagreement widens the interval: native uncertainty + half the cross-oracle spread
        native_uncertainty=round(base_unc + 0.5 * spread, 4),
        scope_card="boltz-2", in_scope=all(r.in_scope for r in avail),
        extrapolating=any(r.extrapolating for r in avail), output_kind="claim",
        available=True, note=f"consensus of {len(avail)} oracles; spread {round(spread, 4)} widens the interval")
