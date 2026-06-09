"""Protein-design oracles (v4.0, WS-O3) — RFdiffusion / ProteinMPNN / ESM3, all CANDIDATES.

Every output here is a generative **candidate** (output_kind=candidate): a backbone, a designed sequence, or
an ESM3 design. By the contract (`OracleResult.as_claim()` raises) and a guard test, none of these can enter a
claim path without passing writer-verification (WS-WV) scoring against measured data — the encoded
pen-assemble lesson (0 validatable de-novo writers; we score/critique, never assert function). Heavy backends
run on-demand; absent → deferred candidate.
"""
from __future__ import annotations

from pen_stack.oracles import build_result, cache_get
from pen_stack.oracles.schema import OracleResult


def _candidate(model: str, inputs: dict, backend: str, note: str) -> OracleResult:
    r = build_result("protein_design", model, inputs=inputs, available=False, output_kind="candidate", note=note)
    hit = cache_get(r.provenance.cache_key)
    if hit is not None:
        return build_result("protein_design", model, inputs=inputs, value=hit.get("value"), available=True,
                            cached=True, source="cache", output_kind="candidate",
                            note="replayed from committed oracle cache (still a CANDIDATE)")
    try:
        __import__(backend)
    except Exception:  # noqa: BLE001
        return r
    return build_result("protein_design", model, inputs=inputs, available=False, output_kind="candidate",
                        note=f"{model} present; wire the generator (output stays a CANDIDATE)")


def generate_backbone(spec: dict, model: str = "rfdiffusion") -> OracleResult:
    """RFdiffusion / RFdiffusion-AA backbone generation — a CANDIDATE."""
    return _candidate(model, {"spec": spec}, "rfdiffusion",
                      "RFdiffusion backbone is a CANDIDATE; verify before any claim")


def design_sequence(backbone: dict, model: str = "proteinmpnn") -> OracleResult:
    """ProteinMPNN / LigandMPNN sequence design for a fixed backbone — a CANDIDATE."""
    return _candidate(model, {"backbone": backbone}, "proteinmpnn",
                      "ProteinMPNN sequence is a CANDIDATE; score against measured data before any claim")


def esm3_design(prompt: dict, model: str = "esm3") -> OracleResult:
    """ESM3 generative protein design / representation — a CANDIDATE."""
    return _candidate(model, {"prompt": prompt}, "esm",
                      "ESM3 design is a CANDIDATE; verify fold/activity before any claim")
