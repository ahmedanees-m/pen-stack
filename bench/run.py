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


def _deterministic_agent() -> dict:
    """The grounded state machine (no LLM) - the structural no-fabrication gate; runs everywhere."""
    from pen_stack.agent.pen_agent import plan_write_session
    goals = [("TRAC", "knock_in_with_disruption"), ("HBB", "high_durability_insertion"),
             ("AAVS1", "safe_harbour_insertion"), ("CCR5", "safe_harbour_insertion"),
             ("HBG1", "regulatory_excision"), ("PDCD1", "knock_in_with_disruption"),
             ("FXN", "repeat_excision"), ("CLYBL", "high_durability_insertion")]
    runs, all_clean, matched = [], True, 0
    for gene, intent in goals:
        try:
            r = plan_write_session(gene, intent)
        except Exception as e:  # noqa: BLE001
            runs.append({"gene": gene, "error": f"{type(e).__name__}: {e}"})
            continue
        all_clean = all_clean and r["no_fabrication"]
        matched += int(r["completed"])
        runs.append({"gene": gene, "no_fabrication": r["no_fabrication"], "completed": r["completed"],
                     "degraded": len(r["degraded_modes"]), "refused": len(r["refusals"])})
    return {"no_fabrication_pass": all_clean, "grounded_tasks_matched": matched, "runs": runs}


def _llm_orchestrator() -> dict | None:
    """The REAL external LLM-agent baseline: the LLM (orchestrator.run_agent) actually drives the validated
    tools, and we audit that every number in its trace equals a direct tool call (no fabrication). Runs only
    when an LLM provider is reachable; this is the leaderboard's >=1 external-LLM-agent baseline (E1)."""
    from pen_stack.rag.llm import active_provider
    provider = active_provider()
    if provider is None:
        return None
    from pen_stack.agent.orchestrator import run_agent
    from pen_stack.validate.agent_eval import no_fabrication
    goals = [("knock a CAR into TRAC, disrupting the TCR", "TRAC"),
             ("insert a durable cassette at a safe harbour", "AAVS1"),
             ("write a gene into CCR5 for HIV resistance", "CCR5"),
             ("place a durable transgene at the CLYBL safe harbour", "CLYBL")]
    checks, clean, grounded, llm_drove = [], True, 0, 0
    for goal, gene in goals:
        try:
            res = run_agent(goal)
            nf = no_fabrication(res)
        except Exception as e:  # noqa: BLE001 - LLM hiccup must never crash the bench
            checks.append({"goal": gene, "error": f"{type(e).__name__}: {e}"})
            continue
        clean = clean and nf["passed"]
        grounded += int(bool(res.get("trace")))
        llm_drove += int(bool(res.get("llm")))          # True only when the LLM actually drove (not fallback)
        checks.append({"goal": gene, "no_fabrication": nf["passed"], "tool_calls": len(res.get("trace", [])),
                       "llm_driven": res.get("llm", False), "refused": res.get("refused", False)})
    return {"provider": provider, "no_fabrication_pass": clean, "grounded_runs": grounded,
            "llm_driven_runs": llm_drove, "n_goals": len(goals), "checks": checks}


def run_agent_solver() -> dict:
    """Agent solver = (a) deterministic state-machine gate + (b) the real LLM orchestrator when reachable."""
    det = _deterministic_agent()
    llm = _llm_orchestrator()
    out = {"deterministic_no_fabrication_pass": det["no_fabrication_pass"],
           "grounded_tasks_matched": det["grounded_tasks_matched"],
           "deterministic_runs": det["runs"]}
    if llm is not None:                         # real external LLM-agent baseline
        out.update({"provider": llm["provider"], "no_fabrication_pass": llm["no_fabrication_pass"],
                    "grounded": llm["grounded_runs"] > 0, "llm_agent": llm})
    else:                                       # no LLM reachable -> report the deterministic gate only
        out.update({"provider": "deterministic (no LLM reachable)",
                    "no_fabrication_pass": det["no_fabrication_pass"],
                    "grounded": det["grounded_tasks_matched"] > 0})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Genome-Writing Bench v0.1")
    ap.add_argument("--agent", action="store_true", help="also run the PEN-Agent no-fabrication solver")
    ap.add_argument("--ungrounded-live", action="store_true",
                    help="call the live LLMs (offline=False) to (re)populate the ungrounded-baseline cache")
    ap.add_argument("--verify", action="store_true", help="verify frozen SHA256SUMS and exit")
    args = ap.parse_args(argv)

    if args.verify:
        v = verify_shasums()
        print(json.dumps(v, indent=2))
        return 0 if v["verified"] else 1

    bench = harness.run_bench()
    llm = run_agent_solver() if args.agent else None
    # Ungrounded-LLM contrast (T7): replay from cache by default; --ungrounded-live calls the models once.
    from pen_stack.validate.ungrounded_baseline import run as ungrounded_run
    ung = ungrounded_run(offline=not args.ungrounded_live)
    _RESULTS.parent.mkdir(parents=True, exist_ok=True)
    _RESULTS.write_text(json.dumps({"bench": bench, "agent": llm, "ungrounded": ung}, indent=2, default=str),
                        encoding="utf-8")
    _LEADERBOARD.write_text(solvers.render_leaderboard_md(bench, llm, ung), encoding="utf-8", newline="\n")
    write_shasums()
    print(f"tasks available: {bench['n_available']}/{bench['n_tasks']}; "
          f"planner beats naive on {bench['planner_beats_baseline']}/{bench['n_with_baseline']}; "
          f"agent no-fabrication: {None if llm is None else llm['no_fabrication_pass']}")
    print(f"-> {_RESULTS}\n-> {_LEADERBOARD}\n-> {_SHA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
