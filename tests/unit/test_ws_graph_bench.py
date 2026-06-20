"""WS-BA (v4.5) unit tests - graph-grounded multi-hop reasoning bench task. CI-safe."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.genome_writing_bench import harness # noqa: E402
from pen_stack.validate import bench_graph_tasks as G # noqa: E402


def test_graph_reasoning_accuracy_and_grounding():
    r = G.run()
    assert r["available"] and r["graph_reasoning_accuracy"] == 1.0
    assert r["ungrounded_baseline_accuracy"] == 0.0
    assert r["all_answers_grounded"] is True and r["no_fabrication"] is True
    assert all(row["grounded"] and row["correct"] for row in r["rows"])


def test_bench_v0_3_1_registers_graph_task():
    cfg = harness.load_tasks()
    assert cfg["version"] >= "0.3.1"
    ids = {t["id"] for t in cfg["tasks"]}
    assert "graph_multihop_reasoning" in ids
    r = harness.run_bench(["graph_multihop_reasoning"])
    assert r["results"][0]["planner_score"] > r["results"][0]["baseline_score"]
