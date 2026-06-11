"""Batch experiment selection with diversity (v5.10, WS-DESIGN).

Greedy batch construction: maximise summed acquisition while spreading across the design space, so a batch is a
DIVERSE set of informative experiments — not k copies of the single most-uncertain point. Each chosen experiment
carries its expected information gain.
"""
from __future__ import annotations

from pen_stack.active.acquire import acquisition_score, expected_information_gain

# design facets used for the diversity (redundancy) penalty.
_FACETS = ("writer_family", "delivery_vehicle", "chrom", "edit_intent", "cell_type")


def _redundancy(cand: dict, chosen: list[dict]) -> float:
    """Penalty for similarity to already-chosen experiments: fraction of shared design facets (0..1), summed."""
    if not chosen:
        return 0.0
    pen = 0.0
    for c in chosen:
        shared = sum(1 for f in _FACETS if cand.get(f) is not None and cand.get(f) == c.get(f))
        pen += shared / len(_FACETS)
    return pen


def batch_diversity(batch: list[dict]) -> float:
    """Mean pairwise distinctness over the facets (1 = all distinct). Higher = more diverse."""
    if len(batch) < 2:
        return 1.0
    pairs, dist = 0, 0.0
    for i in range(len(batch)):
        for j in range(i + 1, len(batch)):
            shared = sum(1 for f in _FACETS
                         if batch[i].get(f) is not None and batch[i].get(f) == batch[j].get(f))
            dist += 1.0 - shared / len(_FACETS)
            pairs += 1
    return dist / pairs if pairs else 1.0


def select_batch(candidates: list[dict], cell_state: str, model_ctx: dict | None = None,
                 *, k: int = 8, w_div: float = 0.5) -> list[dict]:
    """Greedy diverse batch: at each step pick the candidate maximising acquisition minus a redundancy penalty
    against the already-chosen set. Each returned experiment carries its expected information gain."""
    chosen: list[dict] = []
    remaining = list(candidates)
    while remaining and len(chosen) < k:
        best = max(remaining, key=lambda c: acquisition_score(c, cell_state, model_ctx)
                   - w_div * _redundancy(c, chosen))
        chosen.append(best)
        remaining.remove(best)
    return [{**c, "expected_info_gain": expected_information_gain(c, cell_state, model_ctx)} for c in chosen]
