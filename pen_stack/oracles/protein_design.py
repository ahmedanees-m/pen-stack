"""Protein-design oracles (v4.0, WS-O3) — RFdiffusion / ProteinMPNN / ESM3, all CANDIDATES.

Every output here is a generative **candidate** (output_kind=candidate): a backbone, a designed sequence, or
an ESM3 design. By the contract (`OracleResult.as_claim()` raises) and a guard test, none of these can enter a
claim path without passing writer-verification (WS-WV) scoring against measured data — the encoded
pen-assemble lesson (0 validatable de-novo writers; we score/critique, never assert function). Heavy backends
run on-demand; absent → deferred candidate.
"""
from __future__ import annotations

import os

from pen_stack.oracles import build_result, cache_get, cache_put
from pen_stack.oracles.schema import OracleResult


def _oracle_net_enabled() -> bool:
    """Live oracle calls are opt-in (the VM sets it; CI/offline leave it unset → deferred)."""
    return os.getenv("PEN_STACK_ORACLE_NET") == "1"


def _model_server(env_var: str, default: str) -> str:
    return os.getenv(env_var, default).rstrip("/")


def _post(url: str, payload: dict, timeout_env: str = "PEN_STACK_MODEL_TIMEOUT", default_timeout: str = "600"):
    import requests
    r = requests.post(url, json=payload, timeout=float(os.getenv(timeout_env, default_timeout)))
    r.raise_for_status()
    return r.json()


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
    """RFdiffusion / RFdiffusion-AA backbone generation — a CANDIDATE.

    LIVE via the local RFdiffusion model server (`PEN_STACK_RFDIFFUSION_URL`, default localhost:9013) when
    `PEN_STACK_ORACLE_NET=1`, the spec gives a `length` or `contigs`, and the service is up: RFdiffusion
    diffuses a real backbone PDB (still a CANDIDATE — verify before any claim). Otherwise deferred."""
    inputs = {"spec": spec}
    length = (spec or {}).get("length") if isinstance(spec, dict) else None
    contigs = (spec or {}).get("contigs") if isinstance(spec, dict) else None
    if _oracle_net_enabled() and (length or contigs):
        key_obj = build_result("protein_design", model, inputs=inputs, output_kind="candidate")
        url = _model_server("PEN_STACK_RFDIFFUSION_URL", "http://localhost:9013")
        payload = {k: v for k, v in {"length": length, "contigs": contigs,
                                     "num_designs": spec.get("num_designs", 1)}.items() if v is not None}
        try:
            resp = _post(f"{url}/generate", payload, default_timeout="1200")
        except Exception:  # noqa: BLE001 - service down → defer honestly
            return _candidate(model, inputs, "rfdiffusion",
                              "RFdiffusion server unreachable; deferred CANDIDATE (start the model server)")
        designs = resp.get("designs") or []
        val = {"designs": designs, "n": len(designs), "contigs": resp.get("contigs"),
               "n_residues": (designs[0].get("n_residues") if designs else None)}
        cache_put(key_obj.provenance.cache_key, {"value": val})
        return build_result("protein_design", model, inputs=inputs, value=val, available=True,
                            source="local_gpu", output_kind="candidate",
                            note=("RFdiffusion diffused a backbone (local GPU). CANDIDATE — design a sequence "
                                  "(ProteinMPNN) + verify fold/activity before any claim."))
    return _candidate(model, inputs, "rfdiffusion",
                      "RFdiffusion backbone is a CANDIDATE; verify before any claim")


def design_sequence(backbone: dict, model: str = "proteinmpnn") -> OracleResult:
    """ProteinMPNN / LigandMPNN sequence design for a fixed backbone — a CANDIDATE.

    LIVE via the local ProteinMPNN model server (`PEN_STACK_PROTEINMPNN_URL`, default localhost:9011) when
    `PEN_STACK_ORACLE_NET=1`, the backbone carries a `pdb`, and the service is up; the designed sequences are a
    real ProteinMPNN output (still a CANDIDATE — `as_claim()` raises). Otherwise deferred / cache-replay."""
    inputs = {"backbone": backbone}
    pdb = (backbone or {}).get("pdb") if isinstance(backbone, dict) else None
    if _oracle_net_enabled() and isinstance(pdb, str) and "ATOM" in pdb:
        key_obj = build_result("protein_design", model, inputs=inputs, output_kind="candidate")
        url = _model_server("PEN_STACK_PROTEINMPNN_URL", "http://localhost:9011")
        try:
            resp = _post(f"{url}/design", {"pdb": pdb, "chains": backbone.get("chains"),
                                           "num_seqs": int(backbone.get("num_seqs", 4))})
        except Exception:  # noqa: BLE001 - service down/unreachable → defer honestly (no fabrication)
            return _candidate(model, inputs, "proteinmpnn",
                              "ProteinMPNN server unreachable; deferred CANDIDATE (start the model server to design)")
        designs = resp.get("designs") or []
        best = min((d.get("global_score") for d in designs if d.get("global_score") is not None), default=None)
        val = {"designs": designs, "n": len(designs), "best_global_score": best}
        cache_put(key_obj.provenance.cache_key, {"value": val})
        return build_result("protein_design", model, inputs=inputs, value=val, available=True,
                            source="local_gpu", output_kind="candidate",
                            note=("ProteinMPNN designed sequences for the backbone (local GPU). CANDIDATE — score "
                                  "against measured data (writer-verification) before any claim."))
    return _candidate(model, inputs, "proteinmpnn",
                      "ProteinMPNN sequence is a CANDIDATE; score against measured data before any claim")


def esm3_design(prompt: dict, model: str = "esm3") -> OracleResult:
    """ESM3 generative protein design / representation — a CANDIDATE.

    LIVE via the local ESM3-open model server (`PEN_STACK_ESM3_URL`, default localhost:9012) when
    `PEN_STACK_ORACLE_NET=1`, the prompt gives a masked `sequence` or a `length`, and the service is up: ESM3
    generates a real protein (still a CANDIDATE — verify fold/activity before any claim). Otherwise deferred."""
    inputs = {"prompt": prompt}
    seq = (prompt or {}).get("sequence") if isinstance(prompt, dict) else None
    length = (prompt or {}).get("length") if isinstance(prompt, dict) else None
    if _oracle_net_enabled() and (seq or length):
        key_obj = build_result("protein_design", model, inputs=inputs, output_kind="candidate")
        url = _model_server("PEN_STACK_ESM3_URL", "http://localhost:9012")
        payload = {k: v for k, v in {"sequence": seq, "length": length,
                                     "num_steps": prompt.get("num_steps"),
                                     "temperature": prompt.get("temperature")}.items() if v is not None}
        try:
            resp = _post(f"{url}/generate", payload)
        except Exception:  # noqa: BLE001 - service down → defer honestly
            return _candidate(model, inputs, "esm",
                              "ESM3 server unreachable; deferred CANDIDATE (start the model server to design)")
        val = {"sequence": resp.get("sequence"), "length": resp.get("length"),
               "num_steps": resp.get("num_steps"), "model": resp.get("backend")}
        cache_put(key_obj.provenance.cache_key, {"value": val})
        return build_result("protein_design", model, inputs=inputs, value=val, available=True,
                            source="local_gpu", output_kind="candidate",
                            note=("ESM3-open generated a protein sequence (local GPU). CANDIDATE — verify "
                                  "fold/activity (writer-verification) before any claim."))
    return _candidate(model, inputs, "esm",
                      "ESM3 design is a CANDIDATE; verify fold/activity before any claim")
