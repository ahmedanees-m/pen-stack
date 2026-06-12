"""Genome oracles (v4.0, WS-O1) — AlphaGenome / Evo2 / accessibility baselines, under one contract.

AlphaGenome (regulatory tracks + variant effect) is **OOD-gated**: scoring a locus outside the model's
training distribution sets `extrapolating=True` / `in_scope=False` (the model does not generalize to unseen
loci — labelled, not hidden). Evo2 supplies a likelihood/zero-shot *claim*-scope scalar and, separately,
*generated DNA candidates* (output_kind=candidate → cannot enter a claim path). ChromBPNet/Borzoi are kept as
honest baselines. Heavy backends run on-demand and are cached; when absent the adapter defers (or replays a
committed cache entry) rather than fabricating a value.
"""
from __future__ import annotations

import os

from pen_stack.oracles import build_result, cache_get, cache_put
from pen_stack.oracles.schema import OracleResult

# ---- hosted Evo2-40B (NVIDIA) — live path, opt-in via PEN_STACK_ORACLE_NET=1 (CI stays offline by default) ----
_EVO2_URL = "https://health.api.nvidia.com/v1/biology/arc/evo2-40b/generate"


def _oracle_net_enabled() -> bool:
    """Live oracle network calls are opt-in (the deployed VM sets it; CI/offline leave it unset → deferred)."""
    return os.getenv("PEN_STACK_ORACLE_NET") == "1"


def _nvidia_key() -> str | None:
    key = os.getenv("NVIDIA_API_KEY")
    if key:
        return key.strip()
    from pen_stack._resources import project_root
    f = project_root() / "configs" / "nvidia_api_key.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def _sanitize_dna(s: str) -> str:
    return "".join(c for c in (s or "").upper() if c in "ACGTN")


def _call_evo2_generate(seed: str, n: int) -> dict:
    import requests
    key = _nvidia_key()
    if not key:
        raise RuntimeError("no NVIDIA_API_KEY for hosted Evo2")
    body = {"sequence": seed, "num_tokens": int(n), "top_k": 4, "enable_sampled_probs": True}
    r = requests.post(_EVO2_URL, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      json=body, timeout=float(os.getenv("PEN_STACK_ORACLE_TIMEOUT", "120")))
    r.raise_for_status()
    return r.json()


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


def generate_dna(prompt: str, n: int = 20) -> OracleResult:
    """Evo2 generative DNA — a CANDIDATE (output_kind=candidate); cannot enter a claim path unverified.

    LIVE via NVIDIA's hosted Evo2-40B when `PEN_STACK_ORACLE_NET=1` and an NVIDIA key is present: Evo2 conditions
    on a DNA context (the seed) and extends it; the per-token model probability is surfaced as native uncertainty.
    Otherwise deferred / cache-replay (value None, never fabricated). The result is still a CANDIDATE — a generated
    sequence is a proposal, not a claim (`as_claim()` raises)."""
    seed = _sanitize_dna(prompt)
    inputs = {"prompt": prompt, "seed": seed, "n": int(n)}
    if _oracle_net_enabled() and _nvidia_key() and seed:
        key_obj = build_result("genome", "evo2", inputs=inputs, output_kind="candidate")
        try:
            resp = _call_evo2_generate(seed, n)
        except Exception as e:  # noqa: BLE001 - hosted/network; fall back to deferred honestly (no fabrication)
            return _deferred_or_cached("genome", "evo2", inputs, output_kind="candidate",
                                       backend_note=f"hosted Evo2 call failed ({type(e).__name__}); deferred")
        continuation = _sanitize_dna(resp.get("sequence", ""))     # hosted endpoint returns the continuation only
        probs = resp.get("sampled_probs") or []
        mean_p = (sum(probs) / len(probs)) if probs else None
        unc = round(1.0 - mean_p, 4) if mean_p is not None else None
        val = {"generated": continuation, "full": seed + continuation, "seed": seed,
               "per_token_prob": probs, "n_tokens": len(continuation), "elapsed_ms": resp.get("elapsed_ms")}
        cache_put(key_obj.provenance.cache_key, {"value": val, "native_uncertainty": unc})
        return build_result("genome", "evo2", inputs=inputs, value=val, native_uncertainty=unc,
                            available=True, source="hosted_api", output_kind="candidate",
                            note=("Evo2-40B (NVIDIA hosted) extended the DNA seed; per-token model probability "
                                  "surfaced as uncertainty. CANDIDATE — verify (writer-verification) before any claim."))
    return _deferred_or_cached("genome", "evo2", inputs, output_kind="candidate",
                               backend_note="Evo2 generation is a CANDIDATE; verify before any claim")


def accessibility_baseline(locus: str) -> OracleResult:
    """ChromBPNet/Borzoi accessibility/expression — an honest BASELINE comparator to AlphaGenome."""
    inputs = {"locus": locus}
    return _deferred_or_cached("genome", "chrombpnet_borzoi", inputs, output_kind="baseline",
                               backend_note="ChromBPNet/Borzoi baseline; on-demand")
