"""The DBTL orchestrator — the closed loop (v5.12, WS-LOOP).

One continual design→build→test→learn cycle, integrating every prior cycle:
  generate (v5.8) → decide/batch (v5.10) → safety-gated export (v5.7+v5.11) → run (sim-lab v5.11 / real lab) →
  ingest (v4.5 gate v5.11) → drift (v5.12) → continual learn (v5.12).
**Autonomy Level 3**: closed, but with humans/lab IN CONTROL at every gate (safety, build, belief-admission) —
not autonomous. Numbers come only from tools; no stage fabricates a value.
"""
from __future__ import annotations

from typing import Any

AUTONOMY_LEVEL = 3


def _converged(history: list[dict]) -> bool:
    """Converge when the best observed readout stops improving meaningfully over the last two rounds."""
    bests = [h.get("best_readout") for h in history if h.get("best_readout") is not None]
    return len(bests) >= 2 and abs(bests[-1] - bests[-2]) < 0.01


def _best_readout(results: list) -> float | None:
    vals = []
    for r in results:
        payload = getattr(r, "payload", r)
        ro = payload.get("readout") if isinstance(payload, dict) else None
        if ro is not None:
            vals.append(float(ro))
    return max(vals) if vals else None


def run_loop(goal: dict, cell_state: str, *, candidates: list[dict] | None = None, rounds: int = 5,
             use_lab: bool = False, approver: str = "human", seed: int = 0) -> dict[str, Any]:
    """One Level-3 DBTL campaign. Gated: safety + build + belief-admission each await `approver`. Optimises
    efficacy AND immune-risk; numbers come only from tools; no stage fabricates. Pass an explicit `candidates`
    pool to run atlas-independently (sim-lab is the default; a real lab attaches at the same interface)."""
    from pen_stack.active.design import select_batch
    from pen_stack.build.ingest import ingest_result
    from pen_stack.build.protocol import ProtocolExportError, _to_protocol_ir, export_protocol
    from pen_stack.build.simlab import run_simulated
    from pen_stack.design.generate import generate_designs
    from pen_stack.loop.continual import continual_update
    from pen_stack.loop.drift import detect_drift

    history: list[dict] = []
    prev_version: str | None = None
    for r in range(rounds):
        cands = generate_designs(goal, candidates=candidates, keep=8, actor=approver)   # v5.8 (safe+legal+calibrated)
        if not cands:
            history.append({"round": r, "n": 0, "note": "no surviving candidates (atlas absent or all discarded)"})
            break
        batch = select_batch(cands, cell_state, {"round": r}, k=4)                       # v5.10 (info + immune-VOI)
        admitted, blocked = [], 0
        for d in batch:
            try:
                export_protocol(d, {"round": r}, actor=approver)                         # v5.7 safety-gate (may block)
            except ProtocolExportError:
                blocked += 1
                continue
            ir = _to_protocol_ir(d, {"round": r})
            res = (_run_real(ir, d) if use_lab else run_simulated(ir, d, cell_state, seed=seed + r))
            admitted.append(ingest_result(res, admitted_by=approver))                    # v4.5 gate (human approves)
        drift = detect_drift(batch, admitted, cell_state=cell_state)                      # v5.12
        update = continual_update(admitted, drift=drift, approver=approver, prev_version=prev_version)  # v5.12
        prev_version = update.get("version", prev_version)
        history.append({"round": r, "n": len(admitted), "blocked": blocked, "best_readout": _best_readout(admitted),
                        "drift": drift, "update": update})
        if _converged(history):
            break
    return {"goal": goal, "history": history, "final_model_version": prev_version,
            "autonomy_level": AUTONOMY_LEVEL, "human_in_control": True, "no_fabrication": True}


def _run_real(protocol_ir: dict, design: dict):  # pragma: no cover - a real lab attaches here
    raise NotImplementedError("attach a real lab at this interface (same shape as the sim-lab)")


def loop_converges_faster_than_random(reps: int = 15, rounds: int = 6) -> dict:
    """WS-DEMO: the loop's active Learn stage reaches a target model quality in FEWER rounds than random,
    proven retrospectively with reps + a bootstrap CI (the convergence headline; reuses the v5.10 validation)."""
    from pen_stack.active.validate import retrospective_active_learning
    r = retrospective_active_learning(reps=reps, rounds=rounds)
    return {"reaches_optimum_faster_than_random": r["active_beats_random"],
            "active_vs_random_ci": r["active_vs_random"]["ci"], "honest_note": r["honest_note"]}
