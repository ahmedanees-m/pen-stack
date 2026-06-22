"""Off-request structure-oracle runner (v6.13, WS-ORACLE) over named genome-writing complexes.

The structure oracles (AlphaFold3 / Boltz-2 / Chai-1 / Protenix) are held: a full complex prediction is a long
GPU / cloud batch, so it runs OFF the request path and the result is cached; the request path only ever replays
the cache or abstains (:func:`pen_stack.oracles.structure.consistency`). This module names the writer-substrate /
att-site complexes the substrate cares about, exposes a cache-or-abstain :func:`get` over the cross-oracle
consistency, and an :func:`ingest_boltz_confidence` hook that folds a completed off-request Boltz run's confidence
(pLDDT / pTM) into the cache so the request path can replay it.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.oracles import build_result, cache_put
from pen_stack.oracles.schema import OracleResult
from pen_stack.oracles.structure import consistency, predict_structure

# Named complexes relevant to genome writing. Sequences are supplied at call time; these entries describe what a
# held off-request run would target. `kind` records why a structure oracle is or is not the right tool.
_COMPLEXES = {
    "ert2_4oht": {
        "description": "ERT2 ligand-binding domain (human ESR1, UniProt P03372 res 305-554) with "
                       "4-hydroxytamoxifen, the inducible-writer chemical switch",
        "kind": "protein_ligand"},
    "bxb1_attb": {
        "description": "Bxb1 serine integrase engaging its attB DNA target",
        "kind": "protein_dna"},
    "prime_editor_target": {
        "description": "Prime editor (Cas9 nickase-RT fusion) engaging its primed genomic target",
        "kind": "protein_dna"},
}


def complexes() -> dict:
    """The registry of named writer-substrate / att-site complexes a held structure run would target."""
    return dict(_COMPLEXES)


def get(protein_seq: str, models: list[str] | None = None) -> OracleResult:
    """Cross-oracle structure consistency for a complex's protein, cache-or-abstain (never runs the long job).

    Replays committed structure-oracle caches and combines them; divergence widens the interval. When no backend
    has been run off-request and cached, the consensus is unavailable (a deferred result), never fabricated.
    """
    return consistency(protein_seq, models)


def single(protein_seq: str, model: str = "boltz-2") -> OracleResult:
    """One structure oracle's confidence for a sequence (cache-replayed if present, else deferred)."""
    return predict_structure(protein_seq, model)


def ingest_boltz_confidence(protein_seq: str, out_dir: str | Path, model: str = "boltz-2") -> str:
    """Fold a completed OFF-REQUEST Boltz run's confidence into the structure cache, keyed as ``predict_structure``.

    Reads Boltz's ``confidence_*.json`` (``complex_plddt`` on a 0-1 scale) and caches a pLDDT-like value with
    native uncertainty ``1 - pLDDT``, so :func:`predict_structure` (and thus :func:`get`) replays it. Returns the
    cache key. Called after a separate GPU batch completes; never on the request path.
    """
    out = Path(out_dir)
    cj = sorted(p for p in out.rglob("confidence*.json"))
    if not cj:
        raise FileNotFoundError(f"no confidence*.json under {out}")
    d = json.loads(cj[0].read_text(encoding="utf-8"))
    plddt = d.get("complex_plddt")
    if plddt is None:
        raise KeyError(f"complex_plddt absent in {cj[0].name}")
    plddt = float(plddt)
    if plddt > 1.0:  # some writers report 0-100; normalise to 0-1
        plddt = plddt / 100.0
    inputs = {"seq_len": len(protein_seq), "seq": protein_seq.upper(), "model": model}
    key = build_result("structure", model, inputs=inputs, available=False).provenance.cache_key
    cache_put(key, {"value": round(plddt, 4), "native_uncertainty": round(1.0 - plddt, 4),
                    "ptm": d.get("ptm"), "iptm": d.get("iptm"), "source_file": cj[0].name})
    return key
