"""The Genome-Writing Challenge — one-command runner (PEN-STACK v5.13, WS-CHALLENGE).

    python benchmarks/genome_writing_challenge/run.py            # score the PEN-STACK reference on the current round
    python benchmarks/genome_writing_challenge/run.py --round 2026R1

External agents score themselves by importing `evaluate` + `Submission` (see SUBMISSIONS.md / docs/integrations.md):

    from benchmarks.genome_writing_challenge.harness import Submission, evaluate
    print(evaluate(Submission(name="my-agent", predict_fn=my_predict))["aggregate"])

The reference (PEN-STACK itself) anchors the leaderboard; held-out private labels are released after each round.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from benchmarks.genome_writing_challenge.harness import evaluate, reference_submission  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Genome-Writing Challenge runner")
    ap.add_argument("--round", default="2026R1")
    args = ap.parse_args()
    result = evaluate(reference_submission(), round_id=args.round)
    out = _ROOT / "out" / "challenge_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("submission", "round", "aggregate", "by_family",
                                             "immune_risk_task_included", "no_circular_labels",
                                             "no_fabrication", "n_tasks")}, indent=2))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
