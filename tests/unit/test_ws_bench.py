"""WS-BENCH unit tests (Phase 3.4) - Genome-Writing Bench v0.3: multi-write-type routing + adversarial
probes. Pure-logic / verifier-backed, CI-safe (no atlas/LLM needed)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2] # repo root (holds benchmarks/) - not an installed pkg
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.genome_writing_bench import harness, solvers # noqa: E402
from pen_stack.validate import bench_adversarial_tasks as A # noqa: E402
from pen_stack.validate import bench_writetype_tasks as W # noqa: E402


def test_bench_is_v0_3_with_new_tasks():
    cfg = harness.load_tasks()
    assert cfg["version"] >= "0.3"
    ids = {t["id"] for t in cfg["tasks"]}
    assert {"multi_write_type_legality", "adversarial_robustness"} <= ids
    assert all(t["circular"] is False for t in cfg["tasks"])


def test_multi_write_type_legality_spans_router():
    r = W.run()
    assert r["available"] and r["writetype_accuracy"] == 1.0
    assert r["writetype_reason_accuracy"] == 1.0
    assert r["ungrounded_writetype_accuracy"] == 0.0
    assert r["n_write_types"] == 6 # all non-insertion write types
    assert r["no_fabrication"] is True


def test_adversarial_probes_grounded_passes_baseline_fails():
    r = A.run()
    assert r["available"]
    assert r["grounded_pass_rate"] == 1.0 and r["grounded_passes_all"]
    assert r["overconfident_baseline_pass_rate"] == 0.0
    assert r["baseline_fails_at_least_3"] is True
    assert r["no_fabrication"] is True # holds incl. under prompt injection (T15)
    probes = {p["probe"]: p["grounded_pass"] for p in r["probes"]}
    assert all(probes.values())
    assert {"T13_scope_disguise", "T14_contradictory",
            "T15_prompt_injection", "T16_distribution_shift"} <= set(probes)


def test_t15_injection_cannot_inject_a_number():
    probe = next(p for p in A.run()["probes"] if p["probe"] == "T15_prompt_injection")
    assert probe["confidence"] is None # the injected 1.0/0.99 never appears
    assert probe["no_fabrication"] is True


def test_harness_runs_new_tasks_and_planner_beats_baseline():
    r = harness.run_bench(["multi_write_type_legality", "adversarial_robustness"])
    assert r["version"] >= "0.3" and r["n_available"] == 2
    for x in r["results"]:
        assert x["planner_score"] > x["baseline_score"]


def test_leaderboard_renders_robustness_contrast():
    bench = harness.run_bench(["multi_write_type_legality", "adversarial_robustness"])
    md = solvers.render_leaderboard_md(bench)
    assert "Robustness tasks (v0.3)" in md
    assert "v0.3" in md
