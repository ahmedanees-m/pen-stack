"""Genome-Writing Bench v0.1 - reproducible scoring harness (PEN-STACK v3.1, WS-E1).

Loads tasks.yaml, runs each task's deterministic scorer ONCE, and reports the score for each solver:
  * deterministic planner -> the task's `metric` (validated planning tools)
  * naive baseline -> the task's `baseline_metric` (baseline already inside the scorer)
  * LLM agent -> equals the planner on grounded tasks (it orchestrates the SAME tools) and is
                             held to the no-fabrication HARD GATE (T6). Recorded only when an LLM ran.

A scorer that needs the Phase-1 atlas / Perry tables / an LLM returns `available: False` (or raises) when
those are absent; the harness marks the task `available: False` rather than failing - so it runs anywhere,
fully only on the VM/local. No task is scored against a circular label (inherits Gate G-A; `circular: false`
is asserted per task).
"""
from __future__ import annotations

import importlib
from functools import lru_cache
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
_TASKS = _HERE / "tasks.yaml"


@lru_cache(maxsize=1)
def load_tasks() -> dict:
    return yaml.safe_load(_TASKS.read_text(encoding="utf-8"))


def _get(report: dict, dotted: str | None):
    if dotted is None or report is None:
        return None
    cur = report
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _call_scorer(spec: str) -> dict:
    mod_name, func = spec.split(":")
    fn = getattr(importlib.import_module(mod_name), func)
    try:
        rep = fn()
    except Exception as e: # noqa: BLE001 - missing atlas/Perry/LLM -> task unavailable, not a bench failure
        return {"available": False, "error": f"{type(e).__name__}: {e}"}
    return rep if isinstance(rep, dict) else {"available": False}


def run_task(task: dict) -> dict:
    assert task.get("circular") is False, f"task {task['id']} must not use a circular label (Gate G-A)"
    rep = _call_scorer(task["scorer"])
    available = rep.get("available", True) is not False and "error" not in rep
    planner = _get(rep, task["metric"]) if available else None
    baseline = _get(rep, task.get("baseline_metric")) if available else None
    out = {"id": task["id"], "family": task["family"], "metric": task["metric"],
           "available": bool(available and planner is not None),
           "planner_score": planner, "baseline_score": baseline,
           "higher_is_better": task.get("higher_is_better", True),
           "ground_truth": task["ground_truth"]}
    if task.get("hard_gate"):
        out["hard_gate"] = True
        out["gate_rule"] = task["gate_rule"]
        out["gate_pass"] = bool(planner) if out["available"] else None
    if not available:
        out["reason"] = rep.get("error") or rep.get("note") or "scorer unavailable (data/LLM absent)"
    return out


def run_bench(task_ids: list[str] | None = None) -> dict:
    cfg = load_tasks()
    tasks = cfg["tasks"]
    if task_ids:
        tasks = [t for t in tasks if t["id"] in task_ids]
    results = [run_task(t) for t in tasks]
    avail = [r for r in results if r["available"]]
    planner_beats_baseline = sum(
        1 for r in avail if r["baseline_score"] is not None
        and ((r["planner_score"] > r["baseline_score"]) == r["higher_is_better"]))
    n_with_baseline = sum(1 for r in avail if r["baseline_score"] is not None)
    gates = [r for r in results if r.get("hard_gate")]
    return {"version": cfg["version"], "taxonomy": cfg["taxonomy"],
            "n_tasks": len(tasks), "n_available": len(avail),
            "planner_beats_baseline": planner_beats_baseline, "n_with_baseline": n_with_baseline,
            "hard_gates": [{"id": g["id"], "pass": g.get("gate_pass")} for g in gates],
            "results": results}


if __name__ == "__main__": # pragma: no cover
    import json
    print(json.dumps(run_bench(), indent=2, default=str))
