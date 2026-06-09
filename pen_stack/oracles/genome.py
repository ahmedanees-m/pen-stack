"""Genome oracles (v4.0, WS-O1) — AlphaGenome / Evo2 / accessibility baselines, under one contract.

AlphaGenome (regulatory tracks + variant effect) is **OOD-gated**: scoring a locus outside the model's
training distribution sets `extrapolating=True` / `in_scope=False` (the model does not generalize to unseen
loci — labelled, not hidden). Evo2 supplies a likelihood/zero-shot *claim*-scope scalar and, separately,
*generated DNA candidates* (output_kind=candidate → cannot enter a claim path). ChromBPNet/Borzoi are kept as
honest baselines. Heavy backends run on-demand and are cached; when absent the adapter defers (or replays a
committed cache entry) rather than fabricating a value.
"""
from __future__ import annotations

from pen_stack.oracles import build_result, cache_get
from pen_stack.oracles.schema import OracleResult


def _deferred_or_cached(oracle: str, model: str, inputs: dict, *, extrapolating: bool = False,
                        in_scope: bool = True, output_kind: str | None = None,
                        backend_note: str = "backend not installed") -> OracleResult:
    r = build_result(oracle, model, inputs=inputs, available=False, extrapolating=extrapolating,
                     in_scope=in_scope, output_kind=output_kind, note=backend_note)
    hit = cache_get(r.provenance.cache_key)
    if hit is not None:
        return build_result(oracle, model, inputs=inputs, value=hit.get("value"),
                            native_uncertainty=hit.get("native_uncertainty"), available=True, cached=True,
                            source="cache", extrapolating=extrapolating, in_scope=in_scope,
                            output_kind=output_kind, note="replayed from committed oracle cache")
    return r


def variant_effect(variant: str, locus: str, in_distribution: bool = True) -> OracleResult:
    """AlphaGenome variant-effect prediction, OOD-gated by `in_distribution`."""
    inputs = {"variant": variant, "locus": locus}
    try:
        import alphagenome  # noqa: F401
    except Exception:  # noqa: BLE001 - hosted/on-demand; absent in CI
        return _deferred_or_cached("genome", "alphagenome", inputs, extrapolating=not in_distribution,
                                   in_scope=in_distribution,
                                   backend_note="AlphaGenome on-demand (hosted); deferred without access")
    # (live path would call alphagenome here; structure3d.py already does for contact maps)
    return build_result("genome", "alphagenome", inputs=inputs, value=None, available=False,
                        extrapolating=not in_distribution, in_scope=in_distribution,
                        note="AlphaGenome client present; wire predict_variant for the live value")


def sequence_likelihood(seq: str) -> OracleResult:
    """Evo2 zero-shot sequence likelihood — a claim-scope scalar (NOT a generated sequence)."""
    inputs = {"seq_len": len(seq), "seq": seq.upper()}
    try:
        import evo2  # noqa: F401
    except Exception:  # noqa: BLE001
        return _deferred_or_cached("genome", "evo2", inputs, output_kind="claim",
                                   backend_note="Evo2 backend not installed (large; on-demand)")
    return build_result("genome", "evo2", inputs=inputs, output_kind="claim", available=False,
                        note="Evo2 present; wire likelihood scoring for the live value")


def generate_dna(prompt: str, n: int = 1) -> OracleResult:
    """Evo2 generative DNA — a CANDIDATE (output_kind=candidate); cannot enter a claim path unverified."""
    inputs = {"prompt": prompt, "n": n}
    return _deferred_or_cached("genome", "evo2", inputs, output_kind="candidate",
                               backend_note="Evo2 generation is a CANDIDATE; verify before any claim")


def accessibility_baseline(locus: str) -> OracleResult:
    """ChromBPNet/Borzoi accessibility/expression — an honest BASELINE comparator to AlphaGenome."""
    inputs = {"locus": locus}
    return _deferred_or_cached("genome", "chrombpnet_borzoi", inputs, output_kind="baseline",
                               backend_note="ChromBPNet/Borzoi baseline; on-demand")
