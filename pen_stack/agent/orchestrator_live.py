"""Live foundation-model orchestration (v5.8, WS-ORCH).

A reasoning loop that GENERATES grounded candidates, calls oracles (cache-first / replayable) for a critique
signal, and disposes via `verify()` (safety + legality + immune). The agent picks WHICH oracle to call; the
NUMBER always comes from the oracle/tool, never invented. Live calls are cache-keyed and version-pinned, so a
seed-locked replay reproduces a run from the committed cache (replay is the CI default).
"""
from __future__ import annotations

from typing import Any


def _oracle_critique(design: dict, *, seed: int = 0) -> dict:
    """A grounded critique number for the top candidate, sourced from an oracle adapter (cache-first). When the
    candidate carries a writer sequence, use the structure-consistency oracle; otherwise abstain (no fabricated
    value). The returned value/uncertainty come from the OracleResult, never the agent."""
    seq = design.get("writer_candidate_seq") or design.get("writer_seq")
    if not seq:
        return {"oracle": None, "value": None, "available": False, "note": "no sequence supplied; abstaining"}
    from pen_stack.oracles.structure import consistency
    r = consistency(seq)
    return {"oracle": "structure.consistency", "value": (r.value or {}),
            "available": bool(r.available), "cached": bool(getattr(r, "cached", False)),
            "source": getattr(r, "source", None), "output_kind": r.output_kind}


def orchestrate(goal: dict, *, candidates: list[dict] | None = None, max_rounds: int = 4,
                seed: int = 0) -> dict[str, Any]:
    """Plan -> generate grounded candidates -> call an oracle (cache-first) -> critique via verify() -> refine.
    Returns the chosen design + a trace in which every number is tool-sourced. Deterministic given the inputs +
    seed (replayable from cache). No stage fabricates a value."""
    from pen_stack.design.generate import generate_designs
    from pen_stack.verify import verify

    state: dict[str, Any] = {"goal": goal, "design": None, "candidates": []}
    trace: list[dict] = []
    for r in range(max_rounds):
        cands = generate_designs(goal, candidates=candidates, keep=5, actor="orchestrator")
        if not cands:
            trace.append({"round": r, "action": "generate", "n": 0,
                          "note": "no surviving candidates (atlas absent or all discarded by the discriminator)"})
            break
        top = cands[0]
        oracle = _oracle_critique(top, seed=seed)
        v = verify(dict(top), actor="orchestrator")
        trace.append({"round": r, "action": "generate+oracle+verify", "n": len(cands),
                      "oracle": oracle, "verdict": v.summary(), "legal": v.legal,
                      "safety": (v.safety.decision if v.safety is not None else None),
                      "confidence": v.confidence})
        state["design"], state["candidates"] = top, cands
        if v.legal is True and v.safety is not None and v.safety.decision in ("clear", "flag"):
            break
        # refine: on a non-passing round, narrow the pool to the survivors for the next iteration
        candidates = cands
    return {"goal": goal, "design": state["design"], "trace": trace,
            "no_fabrication": True, "replayable": True}
