"""Genome-Writing Bench v0.1 - solvers + leaderboard assembly (PEN-STACK v3.1, WS-E1).

Three solvers are compared on the same tasks:

  * `deterministic_planner` - the validated PEN-STACK planning tools (the reference).
  * `naive_baseline`        - the honest baseline already implemented inside each scorer (safety-only site
                              ranking, writer prevalence, Hamming-distance off-target, etc.).
  * `llm_agent`             - PEN-Agent (agent/orchestrator.py) driven through the MCP tool registry. Because
                              it ORCHESTRATES the same deterministic tools, on grounded tasks its numbers
                              EQUAL the planner's; its distinguishing axis is the no-fabrication HARD GATE
                              (T6) and correct tool selection. Listed on the leaderboard only when an LLM ran.

The point of the leaderboard is not to crown a winner but to show (a) the planner beats the naive baseline
on grounded tasks, and (b) an LLM agent can reach the planner's numbers ONLY by grounding every value in a
tool result - never by inventing them.
"""
from __future__ import annotations

SOLVERS = ("deterministic_planner", "naive_baseline", "llm_agent")


def leaderboard_rows(bench: dict, llm: dict | None = None) -> list[dict]:
    """Assemble per-solver leaderboard rows from a harness.run_bench() result (+ optional LLM-agent run)."""
    avail = [r for r in bench["results"] if r["available"]]
    rows = [
        {"solver": "deterministic_planner",
         "tasks_scored": len(avail),
         "beats_naive_on": f"{bench['planner_beats_baseline']}/{bench['n_with_baseline']}",
         "no_fabrication": "n/a (deterministic)",
         "note": "validated planning tools - the reference"},
        {"solver": "naive_baseline",
         "tasks_scored": sum(1 for r in avail if r["baseline_score"] is not None),
         "beats_naive_on": "-",
         "no_fabrication": "n/a (deterministic)",
         "note": "safety-only / prevalence / Hamming baselines"},
    ]
    if llm is not None:
        rows.append({
            "solver": "llm_agent",
            "tasks_scored": llm.get("grounded_tasks_matched", 0),
            "beats_naive_on": "= planner (grounded)" if llm.get("grounded") else "-",
            "no_fabrication": "PASS" if llm.get("no_fabrication_pass") else "FAIL",
            "note": f"{llm.get('provider', 'llm')} via MCP; equals planner only by grounding every value"})
    return rows


def render_leaderboard_md(bench: dict, llm: dict | None = None) -> str:
    rows = leaderboard_rows(bench, llm)
    lines = [
        "# Genome-Writing Bench v0.1 - Leaderboard",
        "",
        f"Tasks: **{bench['n_available']}/{bench['n_tasks']} available** in this run "
        "(unavailable = needs the Phase-1 atlas / Perry tables / an LLM, which run on the VM/local).",
        f"Deterministic planner beats the naive baseline on **{bench['planner_beats_baseline']}/"
        f"{bench['n_with_baseline']}** grounded tasks with a baseline.",
        "",
        "| Solver | Tasks scored | Beats naive | No-fabrication | Note |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['solver']} | {r['tasks_scored']} | {r['beats_naive_on']} | "
                     f"{r['no_fabrication']} | {r['note']} |")
    lines += [
        "",
        "## Per-task results",
        "| Task | Family | Available | Planner | Naive baseline | Gate |",
        "|---|---|---|---|---|---|",
    ]
    for r in bench["results"]:
        gate = "PASS" if r.get("gate_pass") else ("FAIL" if r.get("hard_gate") and r["available"] else "-")
        lines.append(f"| {r['id']} | {r['family']} | {r['available']} | "
                     f"{r['planner_score']} | {r['baseline_score']} | {gate} |")
    lines += [
        "",
        "Scope: tasks are bounded by available documented writes (small, survivorship-biased). The bench "
        "measures grounded planning quality and site/writer/off-target discrimination, not clinical outcome. "
        "No task is scored against a circular label (Gate G-A).",
    ]
    return "\n".join(lines)
