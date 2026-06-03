"""PEN-MONITOR orchestrator (Phase 2, Step 2.7) - the Europe PMC living-database engine.

Poll Europe PMC for every writer-family query, triage each hit into a candidate row (always cited),
de-duplicate, and write a human-reviewed curation queue. The atlas is **never** auto-edited; accepted
entries flow into the WT-KB/atlas with confidence=inferred only after a human accepts them.

Back-test: with ``back_test=True`` and a date window covering March 2026, the engine must surface the
known recent writer ISPpu10 (Europe PMC PPR1218813) into the queue - the pre-registered success check.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pen_stack.monitor.europepmc import search
from pen_stack.monitor.triage import _load_cues, triage_hit

_OUT = Path(__file__).resolve().parents[2] / "out" / "monitor_queue.csv"


def run_monitor(since: str = "2026-01-01", page_size: int = 50, back_test: bool = False,
                out: str | Path = _OUT, cfg_path: str | Path | None = None) -> dict:
    cfg = _load_cues(cfg_path) if cfg_path else _load_cues()
    rows, n_hits = [], 0
    for q in cfg["queries"]:
        try:
            hits = search(q["terms"], since_date=since, page_size=page_size)
        except RuntimeError:
            continue
        n_hits += len(hits)
        for h in hits:
            rows.append(triage_hit(h, default_family=q.get("family"), cfg=cfg))

    queue = pd.DataFrame(rows)
    if not queue.empty:
        queue = queue.drop_duplicates(subset=["source_id"]).reset_index(drop=True)
        # every queued candidate must carry a citation (source_id or doi)
        queue = queue[queue["source_id"].notna() | queue["doi"].notna()]

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(out, index=False)

    res = {"since": since, "n_hits": n_hits, "n_candidates": int(len(queue)), "queue": str(out)}
    if back_test:
        found = False
        if not queue.empty:
            blob = (queue["title"].fillna("") + " " + queue["source_id"].fillna("")).str.lower()
            found = bool(blob.str.contains("isppu10").any() or
                         (queue["source_id"] == "PPR1218813").any())
        res["isppu10_found"] = found
    return res


if __name__ == "__main__":  # pragma: no cover
    r = run_monitor(since="2026-01-01", back_test=True)
    print(r)
