"""Oracle-Bench (v6.13 PEN-ORACLE, I-WS4): the oracle-mesh gates as a reportable bench.

Reports the Stage I gates from committed, deterministic code (the affinity gate replays a committed cache entry;
no network, CI-safe):
  1. reliability verbatim: the per-oracle reliability registry reports PUBLISHED benchmark numbers verbatim with
     citations (the Boltz-2 affinity FEP+ Pearson r is the verified anchor), carries the standing "not a claim
     about this stack" disclaimer, and never invents a number where one was not verified (value is null + a
     cited pointer).
  2. disagreement to interval: cross-oracle disagreement widens the reported interval MONOTONICALLY with the
     spread (the consensus mechanism, checked, not asserted).
  3. affinity contract: the Boltz-2 affinity oracle returns a CANDIDATE with native uncertainty for a grounded,
     in-domain example (the 4-hydroxytamoxifen / ERT2 inducible-writer switch, replayed from cache), and flags
     protein-protein / protein-DNA pairs as out-of-scope (extrapolating); an uncached request defers (no
     fabrication).
"""
from __future__ import annotations

from typing import Any

# The grounded, in-domain example: 4-hydroxytamoxifen binding the ERT2 ligand-binding domain (human ESR1,
# UniProt P03372 res 305-554), the chemical switch of inducible genome writers. Run off-request on a GPU and
# cached; the bench replays the committed cache entry.
ERT2_LBD = ("SLALSLTADQMVSALLDAEPPILYSEYDPTRPFSEASMMGLLTNLADRELVHMINWAKRVPGFVDLTLHDQVHLLECAWLEILMIGLVWRSME"
            "HPGKLLFAPNLLLDRNQGKCVEGMVEIFDMLLATSSRFRMMNLQGEEFVCLKSIILLNSGVYTFLSSTLKSLEEKDHIHRVLDKITDTLIHLM"
            "AKAGLTLQQQHQRLAQLLLILSHIRHMSNKGMEHLYSMKCKNVVPLYDLLLEMLDAHRLHAPTS")
OHT_SMILES = "CCC(=C(C1=CC=C(C=C1)O)C2=CC=C(C=C2)OCCN(C)C)C3=CC=CC=C3"


def _reliability_verbatim() -> dict[str, Any]:
    from pen_stack.oracles.reliability import all_reliability, disclaimer
    reg = all_reliability()
    fep = None
    for rec in reg.get("boltz-2-affinity", []):
        if rec.get("metric", "").startswith("Pearson r"):
            fep = rec
    cited = all(rec.get("citation") for recs in reg.values() for rec in recs if rec.get("benchmark"))
    return {
        "n_oracles": len(reg),
        "boltz2_affinity_fep_pearson_r": fep.get("value") if fep else None,
        "boltz2_affinity_fep_citation": fep.get("citation") if fep else None,
        "all_benchmark_records_cited": bool(cited),
        "disclaimer_present": bool(disclaimer()),
        "gate_pass": bool(fep and fep.get("value") == 0.62 and fep.get("citation") and cited and disclaimer()),
    }


def _disagreement_monotonic() -> dict[str, Any]:
    from pen_stack.oracles.reliability import disagreement_widens_monotonically
    chk = disagreement_widens_monotonically()
    chk["gate_pass"] = bool(chk["monotone_nondecreasing"])
    return chk


def _affinity_contract() -> dict[str, Any]:
    from pen_stack.oracles.affinity import predict_affinity
    grounded = predict_affinity(ERT2_LBD, OHT_SMILES, pair_type="inducer_switch", ligand_name="4-hydroxytamoxifen")
    ood = predict_affinity(ERT2_LBD, OHT_SMILES, pair_type="protein_dna")
    uncached = predict_affinity("MKVLLAAAAA", "CCO", pair_type="ligand")
    gv = grounded.value or {}
    return {
        "grounded_example": "4-hydroxytamoxifen / ERT2 (inducible-writer switch)",
        "grounded_available": grounded.available,
        "grounded_cached": grounded.cached,
        "grounded_binder_probability": gv.get("binder_probability"),
        "grounded_affinity_pred_value": gv.get("affinity_pred_value"),
        "grounded_native_uncertainty": grounded.native_uncertainty,
        "ood_pair_extrapolating": ood.extrapolating,
        "ood_pair_in_scope": ood.in_scope,
        "uncached_defers": (uncached.available is False),
        "gate_pass": bool(grounded.available and grounded.native_uncertainty is not None
                          and gv.get("binder_probability") is not None
                          and ood.extrapolating and not ood.in_scope
                          and uncached.available is False),
    }


def run() -> dict[str, Any]:
    """Run the three Oracle-Bench gates and report them with an overall verdict."""
    rel = _reliability_verbatim()
    dis = _disagreement_monotonic()
    aff = _affinity_contract()
    return {
        "bench": "Oracle-Bench (PEN-ORACLE)",
        "reliability_verbatim": rel,
        "disagreement_to_interval": dis,
        "affinity_contract": aff,
        "all_gates_pass": bool(rel["gate_pass"] and dis["gate_pass"] and aff["gate_pass"]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
