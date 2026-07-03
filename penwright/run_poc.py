"""PENWRIGHT proof-of-concept driver — runs P1..P7 end to end and collects the artifacts.

    python -m penwright.run_poc            # run everything into out/penwright/

Runs the autonomous multi-round loop (P1) on three scenarios (golden path, flawed-seed self-correction,
hazardous-request refusal), issues + verifies a signed passport, then executes each depth pillar (P2..P7),
writing every figure + metrics file into the output directory and a combined ``poc_results.json``.

Deterministic and offline: no live LLM or oracle network call is required (the loop is deterministic; oracles
defer / cache-replay unless PEN_STACK_ORACLE_NET=1 + keys are set). Every reported number is tool-sourced.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from penwright import build_dossier, issue_passport, run_autonomous_loop, verify_passport

_OUT = "out/penwright"

# the golden-path goal: a durable, safe CAR-construct insertion in a T-cell safe-harbour locus
_GOAL = {"gene": "TRAC", "write_type": "insertion", "writer_family": "bridge_IS110",
         "delivery_vehicle": "AAV_single", "edit_intent": "safe_harbour_insertion", "cargo_bp": 3000,
         "cell_type": "K562", "safety": 0.8, "p_durable": 0.75, "writer_activity": 0.7}
# a deliberately flawed seed (oversize cargo into AAV_single) to drive the self-correction story
_FLAWED_SEED = {"write_type": "insertion", "writer_family": "bridge_IS110", "cargo_bp": 30000,
                "delivery_vehicle": "AAV_single", "cell_type": "K562",
                "safety": 0.8, "p_durable": 0.7, "writer_activity": 0.7}
# a hazardous request the enforcing gate must refuse first
_HAZARD = {"goal": "express a ribosome-inactivating toxin", "cargo_function": "ricin-like RIP",
           "pfam_domains": ["PF00161", "PF00652"], "function_tags": ["ribosome_inactivating_protein"],
           "source_taxon": "Ricinus communis", "write_type": "insertion"}

_TS = "2026-07-07T00:00:00Z"  # fixed stamp (the loop is deterministic and reads no wall clock)


def run_p1(out_dir: str = _OUT) -> dict[str, Any]:
    """P1 — the autonomous multi-round loop across three scenarios, with a signed passport."""
    os.makedirs(out_dir, exist_ok=True)
    golden = run_autonomous_loop(_GOAL, cell_state="K562", max_rounds=5)
    redesign = run_autonomous_loop(_GOAL, seed_candidates=[_FLAWED_SEED], cell_state="K562", max_rounds=5)
    refusal = run_autonomous_loop(_HAZARD, cell_state="K562")

    dossier = build_dossier(redesign)
    passport = issue_passport(dossier, actor="penwright-poc", ts=_TS)
    passport_check = verify_passport(passport)
    # tamper probe: flipping a refused verdict to cleared must invalidate the passport
    import copy
    tampered = copy.deepcopy(passport)
    tampered["body"]["clearance"] = "cleared_TAMPERED"
    tamper_check = verify_passport(tampered)

    Path(os.path.join(out_dir, "p1_loop_trace.json")).write_text(
        json.dumps({"golden": golden, "redesign": redesign, "refusal": refusal}, indent=2, default=str),
        encoding="utf-8")
    Path(os.path.join(out_dir, "p1_dossier.json")).write_text(json.dumps(dossier, indent=2, default=str),
                                                              encoding="utf-8")
    Path(os.path.join(out_dir, "p1_passport.json")).write_text(json.dumps(passport, indent=2, default=str),
                                                              encoding="utf-8")
    return {
        "pillar": "P1",
        "golden": {"converged": golden["converged"], "n_rounds": golden["n_rounds"],
                   "quality_trajectory": golden["quality_trajectory"]},
        "self_correction": {"converged": redesign["converged"], "n_rounds": redesign["n_rounds"],
                            "quality_trajectory": redesign["quality_trajectory"],
                            "improved_over_run": redesign["improved_over_run"]},
        "hazard_refusal": {"refused": refusal["refused"], "safety_decision": refusal["safety"]["decision"]},
        "passport": {"clearance": passport["clearance"], "algorithm": passport["algorithm"],
                     "intact_valid": passport_check["valid"], "tamper_detected": not tamper_check["valid"]},
        "artifacts": ["p1_loop_trace.json", "p1_dossier.json", "p1_passport.json"],
        "headline": ("Multi-round loop: golden path converges in {} round(s); a flawed seed self-corrects "
                     "{}→{} across {} rounds; a hazardous request is refused at the gate; the signed passport "
                     "verifies and detects tampering."
                     ).format(golden["n_rounds"],
                              redesign["quality_trajectory"][0] if redesign["quality_trajectory"] else "?",
                              redesign["quality_trajectory"][-1] if redesign["quality_trajectory"] else "?",
                              redesign["n_rounds"]),
    }


def main(out_dir: str = _OUT) -> dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    results: dict[str, Any] = {}

    print("=" * 88)
    print("PENWRIGHT — Proof of Concept: P1..P7")
    print("=" * 88)

    # ---- P1 ----
    results["P1"] = run_p1(out_dir)
    print(f"\n[P1] {results['P1']['headline']}")

    # ---- P2..P7 depth pillars ----
    from penwright.pillars import (p2_outcome_axis, p3_pseudo_attp, p4_oracle_live, p5_safety_eval,
                                   p6_adoption, p7_ablation)
    for tag, mod in [("P2", p2_outcome_axis), ("P3", p3_pseudo_attp), ("P4", p4_oracle_live),
                     ("P5", p5_safety_eval), ("P6", p6_adoption), ("P7", p7_ablation)]:
        try:
            r = mod.run(out_dir)
            results[tag] = r
            print(f"\n[{tag}] {r.get('headline', '(no headline)')}")
        except Exception as e:  # noqa: BLE001 - report the failure, never fabricate a result
            results[tag] = {"pillar": tag, "error": f"{type(e).__name__}: {e}"}
            print(f"\n[{tag}] ERROR: {type(e).__name__}: {e}")

    Path(os.path.join(out_dir, "poc_results.json")).write_text(json.dumps(results, indent=2, default=str),
                                                              encoding="utf-8")
    print("\n" + "=" * 88)
    print(f"Artifacts written to {out_dir}/  (figures: *.png, metrics: *.json, combined: poc_results.json)")
    print("=" * 88)
    return results


if __name__ == "__main__":
    main()
