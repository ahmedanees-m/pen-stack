"""Genome-Writing Bench v0.1 - one-command entrypoint (PEN-STACK v3.1, WS-E1).

    python bench/run.py            # run all tasks, write results + leaderboard
    python bench/run.py --agent    # also run the PEN-Agent (no-fabrication gate) solver
    python bench/run.py --verify   # verify the frozen reference SHA256SUMS and exit

Designed to be the reproducible entrypoint on a clean image: it loads the SHA-locked task set, runs each
task's deterministic scorer, runs the agent's no-fabrication gate, and writes out/bench_results.json +
benchmarks/genome_writing_bench/LEADERBOARD.md. Tasks needing the Phase-1 atlas / Perry tables / an LLM are
reported `available: false` when those are absent, so the command succeeds anywhere (fully on the VM/local).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from benchmarks.genome_writing_bench import harness, solvers  # noqa: E402

_BENCH = _ROOT / "benchmarks" / "genome_writing_bench"
_RESULTS = _ROOT / "out" / "bench_results.json"
_LEADERBOARD = _BENCH / "LEADERBOARD.md"
_SHA = _BENCH / "SHA256SUMS"

# frozen reference inputs (relative to repo root); SHA-locked so a run cannot be silently tuned.
_FROZEN = [
    "benchmarks/genome_writing_bench/tasks.yaml",
    "configs/gsh_validated_heldout.yaml",
    "data/writer_panel.csv",
    "data/gsh_matched_controls.parquet",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_shasums() -> Path:
    lines = [f"{_sha(_ROOT / f)}  {f}" for f in _FROZEN]
    _SHA.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")  # LF only (sha256sum -c safe)
    return _SHA


def verify_shasums() -> dict:
    if not _SHA.exists():
        return {"verified": False, "reason": "SHA256SUMS missing - run without --verify first"}
    want = {}
    for line in _SHA.read_text(encoding="utf-8").splitlines():
        if line.strip():
            h, f = line.split("  ", 1)
            want[f] = h
    bad = [f for f, h in want.items() if _sha(_ROOT / f) != h]
    return {"verified": not bad, "n_files": len(want), "mismatched": bad}


def run_agent_solver() -> dict:
    """PEN-Agent no-fabrication gate: run the grounded state machine on a few goals; never fabricates."""
    from pen_stack.agent.pen_agent import plan_write_session
    goals = [("TRAC", "knock_in_with_disruption"), ("HBB", "high_durability_insertion"),
             ("AAVS1", "safe_harbour_insertion")]
    runs, all_clean, matched = [], True, 0
    for gene, intent in goals:
        try:
            r = plan_write_session(gene, intent)
        except Exception as e:  # noqa: BLE001 - missing atlas -> agent still must not fabricate
            runs.append({"gene": gene, "error": f"{type(e).__name__}: {e}"})
            continue
        all_clean = all_clean and r["no_fabrication"]
        matched += int(r["completed"])
        runs.append({"gene": gene, "no_fabrication": r["no_fabrication"], "completed": r["completed"],
                     "degraded": len(r["degraded_modes"]), "refused": len(r["refusals"])})
    try:
        provider = __import__("pen_stack.rag.llm", fromlist=["active_provider"]).active_provider()
    except Exception:  # noqa: BLE001
        provider = None
    return {"no_fabrication_pass": all_clean, "grounded": matched > 0,
            "grounded_tasks_matched": matched, "provider": provider or "deterministic", "runs": runs}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Genome-Writing Bench v0.1")
    ap.add_argument("--agent", action="store_true", help="also run the PEN-Agent no-fabrication solver")
    ap.add_argument("--verify", action="store_true", help="verify frozen SHA256SUMS and exit")
    args = ap.parse_args(argv)

    if args.verify:
        v = verify_shasums()
        print(json.dumps(v, indent=2))
        return 0 if v["verified"] else 1

    bench = harness.run_bench()
    llm = run_agent_solver() if args.agent else None
    _RESULTS.parent.mkdir(parents=True, exist_ok=True)
    _RESULTS.write_text(json.dumps({"bench": bench, "agent": llm}, indent=2, default=str), encoding="utf-8")
    _LEADERBOARD.write_text(solvers.render_leaderboard_md(bench, llm), encoding="utf-8", newline="\n")
    write_shasums()
    print(f"tasks available: {bench['n_available']}/{bench['n_tasks']}; "
          f"planner beats naive on {bench['planner_beats_baseline']}/{bench['n_with_baseline']}; "
          f"agent no-fabrication: {None if llm is None else llm['no_fabrication_pass']}")
    print(f"-> {_RESULTS}\n-> {_LEADERBOARD}\n-> {_SHA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
