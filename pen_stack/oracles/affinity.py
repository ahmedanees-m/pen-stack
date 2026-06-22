"""Binding-affinity oracle (v6.13, WS-ORACLE), the Boltz-2 protein-ligand affinity head under the contract.

Boltz-2 (MIT; Passaro et al. 2025, DOI 10.1101/2025.06.14.659707) jointly predicts a complex structure and a
binding affinity for a protein with a small-molecule ligand: a binder probability (``affinity_probability_binary``)
and a predicted affinity value (``affinity_pred_value``, a log(IC50) micromolar-scale number, lower = stronger).
This oracle wraps that head under the L1 ``OracleResult`` contract:

* the prediction is a CANDIDATE / hypothesis, never a measured Kd;
* the model's own outputs supply the native uncertainty (the spread between Boltz-2's two affinity heads, or a
  binder-call entropy proxy);
* the affinity head is protein-SMALL-MOLECULE only, so protein-protein and protein-DNA requests are flagged
  out-of-scope (``extrapolating``);
* the backend runs OFF the request path (a GPU batch, ~10-30 min including MSA) and is cached; when no cached run
  is present the request path is cache-or-abstain and never blocks.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.oracles import build_result, cache_get, cache_put
from pen_stack.oracles.schema import OracleResult

_MODEL = "boltz-2-affinity"

# Pair types the affinity head COVERS (protein + small-molecule ligand), with a genome-writing-relevant gloss.
_LIGAND_PAIRS = {
    "inducer_switch": "a small-molecule inducer that switches a genome writer on/off (e.g. 4-OHT / ERT2)",
    "capsid_ligand": "a small molecule binding a delivery capsid (stabiliser or targeting ligand)",
    "effector_drug": "a drug binding a delivered effector protein",
    "ligand": "a generic protein + small-molecule ligand pair",
}
# Pair types OUTSIDE the affinity head's domain (it is protein-ligand only): returned extrapolating.
_OOD_PAIRS = {
    "protein_protein": "protein-protein affinity is not the Boltz-2 affinity head's domain (protein-ligand only)",
    "protein_dna": "protein-DNA affinity is not the Boltz-2 affinity head's domain (protein-ligand only)",
}

_UNITS = ("Boltz-2 affinity_pred_value: log(IC50) on a micromolar scale, lower = stronger binder "
          "(a prediction, not a measured Kd/IC50)")


def _inputs(protein_seq: str, ligand_smiles: str, pair_type: str) -> dict:
    return {"protein_len": len(protein_seq), "protein": protein_seq.upper(),
            "ligand_smiles": ligand_smiles, "pair_type": pair_type}


def predict_affinity(protein_seq: str, ligand_smiles: str, pair_type: str = "ligand",
                     ligand_name: str | None = None) -> OracleResult:
    """Predict protein-ligand binding affinity with the Boltz-2 head; cache-replayed if present, else deferred.

    ``pair_type`` in {inducer_switch, capsid_ligand, effector_drug, ligand} is in-scope; ``protein_protein`` /
    ``protein_dna`` are OUT of the affinity head's domain and returned extrapolating (the head is protein-ligand).
    The long GPU job is never run on the request path: an absent cached run yields a deferred result.
    """
    in_scope = pair_type in _LIGAND_PAIRS
    extrapolating = pair_type in _OOD_PAIRS
    if not in_scope and not extrapolating:
        raise ValueError(f"unknown pair_type {pair_type!r}; choose from "
                         f"{sorted(_LIGAND_PAIRS) + sorted(_OOD_PAIRS)}")
    inputs = _inputs(protein_seq, ligand_smiles, pair_type)
    note0 = (_OOD_PAIRS[pair_type] if extrapolating
             else "Boltz-2 affinity head; backend runs off-request on the GPU and is cached")
    r = build_result("affinity", _MODEL, inputs=inputs, available=False,
                     in_scope=in_scope, extrapolating=extrapolating, note=note0 + "; cache-or-abstain")
    hit = cache_get(r.provenance.cache_key)
    if hit is not None:
        note = "replayed from committed oracle cache"
        if extrapolating:
            note += "; OUT-OF-SCOPE pair_type for a protein-ligand head: treat as extrapolative"
        if ligand_name:
            note += f"; ligand={ligand_name}"
        return build_result("affinity", _MODEL, inputs=inputs, value=hit.get("value"),
                            native_uncertainty=hit.get("native_uncertainty"),
                            available=True, cached=True, source="cache",
                            in_scope=in_scope, extrapolating=extrapolating, note=note)
    return r  # deferred: no cached run, and the long job never runs on the request path


def value_from_boltz_output(out_dir: str | Path) -> dict:
    """Parse a Boltz-2 affinity prediction directory into the cached {value, native_uncertainty} payload.

    Native uncertainty is taken from the model's own outputs: half the spread between Boltz-2's two affinity
    heads when both are present, else a binder-call entropy proxy (``1 - |2p - 1|``, 0 at p in {0,1}, 1 at 0.5).
    """
    out = Path(out_dir)
    js = sorted(p for p in out.rglob("affinity*.json"))
    if not js:
        raise FileNotFoundError(f"no affinity*.json under {out}")
    d = json.loads(js[0].read_text(encoding="utf-8"))
    val = d.get("affinity_pred_value")
    prob = d.get("affinity_probability_binary")
    v1, v2 = d.get("affinity_pred_value1"), d.get("affinity_pred_value2")
    if v1 is not None and v2 is not None:
        unc = round(abs(float(v1) - float(v2)) / 2.0, 4)
        unc_src = "half the spread between the two Boltz-2 affinity heads"
    elif prob is not None:
        unc = round(1.0 - abs(2.0 * float(prob) - 1.0), 4)
        unc_src = "binder-call entropy proxy (1 - |2p - 1|)"
    else:
        unc, unc_src = None, "unavailable"
    value = {"affinity_pred_value": val, "binder_probability": prob, "units": _UNITS,
             "heads": {"affinity_pred_value1": v1, "affinity_pred_value2": v2},
             "native_uncertainty_source": unc_src, "source_file": js[0].name}
    return {"value": value, "native_uncertainty": unc}


def cache_affinity_run(protein_seq: str, ligand_smiles: str, pair_type: str, out_dir: str | Path) -> str:
    """Ingest an OFF-REQUEST Boltz-2 affinity run into the oracle cache, so the request path can replay it.

    Returns the cache key. Called after a separate GPU batch completes; never on the request path.
    """
    payload = value_from_boltz_output(out_dir)
    r = build_result("affinity", _MODEL, inputs=_inputs(protein_seq, ligand_smiles, pair_type), available=False)
    cache_put(r.provenance.cache_key, payload)
    return r.provenance.cache_key
