"""Loop-Bench (v7.0 Stage J, J-WS4): the closed-loop / self-driving-lab gates as a reportable bench.

Reports the three Stage J gates from committed, deterministic code (no network; the cloud-lab submission is
mock / dry-run):
  1. cloud-lab + biosecurity gate: a safety-cleared design round-trips to a cloud lab (mock receipt), and a
     hazardous design is BLOCKED before any protocol is emitted (the biosecurity gate is intact).
  2. SDL-brain benchmark: the EIG/VOI designer is benchmarked against the public optimizers (BayBE / Atlas) on a
     shared acquisition task; the result is reported verbatim with both cited (a win is not required - the
     acquisition advantage is rep-sensitive on the synthetic task and reported either way).
  3. validation campaign: the expression-validation campaign is cloud-lab-executable, targets the calibrate_axis
     gate, and reports EIG-vs-random verbatim.
"""
from __future__ import annotations

from typing import Any

# a benign, legal design (safety-cleared) and a hazardous one (the biosecurity gate must refuse export)
_BENIGN = {"write_type": "insertion", "gene": "AAVS1", "cargo_bp": 2000, "cell_type": "hek293t",
           "installed_att": True, "cargo_function": "insert a GFP reporter at the AAVS1 safe-harbour locus"}
_HAZARD = {"write_type": "insertion", "gene": "AAVS1", "cargo_bp": 2000, "cell_type": "hek293t",
           "cargo_function": "express active ricin toxin A chain for cytotoxicity"}
_REPS = 30  # fixed for a deterministic, reproducible bench


def _cloudlab_gate() -> dict[str, Any]:
    from pen_stack.build.cloudlab import submit_gated
    cleared = submit_gated(_BENIGN, {"round": 1}, actor="bench")
    blocked = submit_gated(_HAZARD, {"round": 1}, actor="bench")
    cleared_ok = (cleared.get("status") == "submitted_mock") and (not cleared.get("blocked"))
    blocked_ok = bool(blocked.get("blocked")) and ("submitted" not in blocked or blocked.get("submitted") is False)
    return {
        "cleared_design_submits_mock": cleared_ok,
        "cleared_job_id": cleared.get("job_id"),
        "hazard_blocked": blocked_ok,
        "hazard_reason": blocked.get("reason"),
        "gate_pass": bool(cleared_ok and blocked_ok),
    }


def _brain_gate() -> dict[str, Any]:
    from pen_stack.active.brains import benchmark
    b = benchmark(reps=_REPS, rounds=6)
    return {
        "eig_vs_random": b["eig_vs_random"],
        "eig_beats_random": b["eig_beats_random"],
        "result": b["result"],
        "references_cited": sorted(b["references"]),
        "baybe_installed": b["baybe_installed"],
        "gate_pass": bool(b["gate_pass"]),  # benchmark ran + reported verbatim + both references cited
    }


def _campaign_gate() -> dict[str, Any]:
    from pen_stack.active.campaign import design_campaign
    c = design_campaign(reps=_REPS, rounds=6)
    targets_gate = "calibrate_axis" in c["target_gate"]["gate"]
    return {
        "n_candidates": c["n_candidates"],
        "batch_size": c["batch_size"],
        "cloud_lab_executable": c["cloud_lab_executable"],
        "targets_calibrate_axis": targets_gate,
        "eig_beats_random": c["eig_beats_random"],
        "autonomy_level": c["autonomy_level"],
        "gate_pass": bool(c["cloud_lab_executable"] and targets_gate and c["batch_size"] > 0),
    }


def run() -> dict[str, Any]:
    """Run the three Loop-Bench gates and report them with an overall verdict."""
    cloud = _cloudlab_gate()
    brain = _brain_gate()
    camp = _campaign_gate()
    return {
        "bench": "Loop-Bench (PEN-LOOP, Stage J)",
        "reps": _REPS,
        "cloudlab_biosecurity": cloud,
        "brain_benchmark": brain,
        "validation_campaign": camp,
        "autonomy": "Level 3 (human in control); no Level-4 claim",
        "all_gates_pass": bool(cloud["gate_pass"] and brain["gate_pass"] and camp["gate_pass"]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
