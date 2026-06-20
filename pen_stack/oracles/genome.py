"""Genome oracles (v4.0, WS-O1), AlphaGenome / Evo2 / accessibility baselines, under one contract.

AlphaGenome (regulatory tracks + variant effect) is **OOD-gated**: scoring a locus outside the model's
training distribution sets `extrapolating=True` / `in_scope=False` (the model does not generalize to unseen
loci, labelled, not hidden). Evo2 supplies a likelihood/zero-shot *claim*-scope scalar and, separately,
*generated DNA candidates* (output_kind=candidate → cannot enter a claim path). ChromBPNet/Borzoi are kept as
baselines. Heavy backends run on-demand and are cached; when absent the adapter defers (or replays a
committed cache entry) rather than fabricating a value.
"""
from __future__ import annotations

import os
import re

from pen_stack.oracles import build_result, cache_get, cache_put
from pen_stack.oracles.schema import OracleResult

# ---- hosted Evo2-40B (NVIDIA), live path, opt-in via PEN_STACK_ORACLE_NET=1 (CI stays offline by default) ----
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


_VAR_RE = re.compile(r"(?:(chr[\w]+)[:\s]*)?(\d+)?\s*([ACGT]+)\s*>\s*([ACGT]+)", re.I)
_LOCUS_RE = re.compile(r"(chr[\w]+)[:\s]*(\d+)?", re.I)


def _parse_variant(variant: str, locus: str):
    """Parse a variant ('chr1:1000 A>T' / 'chr1:1A>T' / 'A>G' + locus 'chr19:1010000') -> (chrom,pos,ref,alt)."""
    m = _VAR_RE.search(variant or "")
    if not m:
        return None
    chrom, pos, ref, alt = m.group(1), m.group(2), m.group(3), m.group(4)
    if not chrom or not pos:
        lm = _LOCUS_RE.search(locus or "")
        if lm:
            chrom = chrom or lm.group(1)
            pos = pos or lm.group(2)
    if not (chrom and pos and ref and alt):
        return None
    return chrom, int(pos), ref.upper(), alt.upper()


def variant_effect(variant: str, locus: str, in_distribution: bool = True) -> OracleResult:
    """AlphaGenome variant-effect prediction, OOD-gated by `in_distribution`.

    LIVE via the existing `wgenome.AlphaGenomeProvider` (real `score_variant`, REF vs ALT) when
    `PEN_STACK_ORACLE_NET=1` and the alphagenome package + key are present; otherwise deferred / cache-replay
    (value None, OOD gate intact, never fabricated). Reuses the v3.1 provider, no duplicate client."""
    inputs = {"variant": variant, "locus": locus}
    parsed = _parse_variant(variant, locus)
    if _oracle_net_enabled() and parsed:
        from pen_stack.wgenome.providers import AlphaGenomeProvider
        prov = AlphaGenomeProvider()
        if prov.available():
            chrom, pos, ref, alt = parsed
            try:
                rec = prov.score_variant(chrom, pos, ref, alt)
            except Exception as e: # noqa: BLE001 - hosted/network; defer, never fabricate
                return _deferred_or_cached("genome", "alphagenome", inputs, extrapolating=not in_distribution,
                                           in_scope=in_distribution,
                                           backend_note=f"AlphaGenome score_variant failed ({type(e).__name__}); deferred")
            if rec.get("available"):
                return build_result(
                    "genome", "alphagenome", inputs=inputs,
                    value={"effect_max_abs": rec["effect_max_abs"], "effect_mean_abs": rec["effect_mean_abs"],
                           "output": rec["output"], "n_scores": rec["n_scores"],
                           "chrom": chrom, "position": pos, "ref": ref, "alt": alt},
                    available=True, source="hosted_api", extrapolating=not in_distribution, in_scope=in_distribution,
                    note=("AlphaGenome score_variant (REF vs ALT, recommended RNA_SEQ scorer): max|effect| over the "
                          "predicted regulatory tracks. A regulatory-effect magnitude, not a claim the edit works."))
    # deferred / cache-replay, package/key/flag absent or variant unparseable (OOD gate preserved, no fabrication)
    return _deferred_or_cached("genome", "alphagenome", inputs, extrapolating=not in_distribution,
                               in_scope=in_distribution,
                               backend_note="AlphaGenome deferred (set PEN_STACK_ORACLE_NET=1 + package/key to score live)")


def sequence_likelihood(seq: str) -> OracleResult:
    """Evo2 zero-shot sequence likelihood, a claim-scope scalar (NOT a generated sequence)."""
    inputs = {"seq_len": len(seq), "seq": seq.upper()}
    try:
        import evo2 # noqa: F401
    except Exception: # noqa: BLE001
        return _deferred_or_cached("genome", "evo2", inputs, output_kind="claim",
                                   backend_note="Evo2 backend not installed (large; on-demand)")
    return build_result("genome", "evo2", inputs=inputs, output_kind="claim", available=False,
                        note="Evo2 present; wire likelihood scoring for the live value")


def generate_dna(prompt: str, n: int = 20) -> OracleResult:
    """Evo2 generative DNA, a CANDIDATE (output_kind=candidate); cannot enter a claim path unverified.

    LIVE via NVIDIA's hosted Evo2-40B when `PEN_STACK_ORACLE_NET=1` and an NVIDIA key is present: Evo2 conditions
    on a DNA context (the seed) and extends it; the per-token model probability is surfaced as native uncertainty.
    Otherwise deferred / cache-replay (value None, never fabricated). The result is still a CANDIDATE, a generated
    sequence is a proposal, not a claim (`as_claim()` raises)."""
    seed = _sanitize_dna(prompt)
    inputs = {"prompt": prompt, "seed": seed, "n": int(n)}
    if _oracle_net_enabled() and _nvidia_key() and seed:
        key_obj = build_result("genome", "evo2", inputs=inputs, output_kind="candidate")
        try:
            resp = _call_evo2_generate(seed, n)
        except Exception as e: # noqa: BLE001 - hosted/network; fall back to deferred (no fabrication)
            return _deferred_or_cached("genome", "evo2", inputs, output_kind="candidate",
                                       backend_note=f"hosted Evo2 call failed ({type(e).__name__}); deferred")
        continuation = _sanitize_dna(resp.get("sequence", "")) # hosted endpoint returns the continuation only
        probs = resp.get("sampled_probs") or []
        mean_p = (sum(probs) / len(probs)) if probs else None
        unc = round(1.0 - mean_p, 4) if mean_p is not None else None
        val = {"generated": continuation, "full": seed + continuation, "seed": seed,
               "per_token_prob": probs, "n_tokens": len(continuation), "elapsed_ms": resp.get("elapsed_ms")}
        cache_put(key_obj.provenance.cache_key, {"value": val, "native_uncertainty": unc})
        return build_result("genome", "evo2", inputs=inputs, value=val, native_uncertainty=unc,
                            available=True, source="hosted_api", output_kind="candidate",
                            note=("Evo2-40B (NVIDIA hosted) extended the DNA seed; per-token model probability "
                                  "surfaced as uncertainty. CANDIDATE, verify (writer-verification) before any claim."))
    return _deferred_or_cached("genome", "evo2", inputs, output_kind="candidate",
                               backend_note="Evo2 generation is a CANDIDATE; verify before any claim")


def accessibility_baseline(locus: str) -> OracleResult:
    """ChromBPNet/Borzoi accessibility/expression, an BASELINE comparator to AlphaGenome."""
    inputs = {"locus": locus}
    return _deferred_or_cached("genome", "chrombpnet_borzoi", inputs, output_kind="baseline",
                               backend_note="ChromBPNet/Borzoi baseline; on-demand")
