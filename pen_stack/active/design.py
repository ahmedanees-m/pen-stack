"""Batch experiment selection with diversity.

Greedy batch construction: maximise summed acquisition while spreading across the design space, so a batch is a
DIVERSE set of informative experiments, not k copies of the single most-uncertain point. Each chosen experiment
carries its expected information gain.
"""
from __future__ import annotations

from pen_stack.active.acquire import acquisition_components

# design facets used for the diversity (redundancy) penalty. cargo_bp is included (v7.3.18) so cargo variants are
# treated as distinct and spread across the batch, instead of collapsing (they differ in feasibility, not outcome).
_FACETS = ("writer_family", "delivery_vehicle", "chrom", "edit_intent", "cell_type", "cargo_bp")


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
    # acquisition is candidate-INTRINSIC (only the redundancy penalty depends on what's already chosen), so score
    # each candidate ONCE up front, this both fixes the prior O(k*n) recomputation and keeps the greedy loop cheap,
    # so a richer candidate pool stays responsive.
    scored = [(c, acquisition_components(c, cell_state, model_ctx)) for c in candidates]
    chosen: list[tuple[dict, dict, float]] = []
    remaining = list(scored)
    while remaining and len(chosen) < k:
        chosen_cands = [c for c, _, _ in chosen]
        best_i = max(range(len(remaining)),
                     key=lambda i: remaining[i][1]["acquisition"] - w_div * _redundancy(remaining[i][0], chosen_cands))
        c, comp = remaining.pop(best_i)
        # marginal_gain = the greedy objective AT SELECTION: intrinsic informativeness minus overlap with the
        # already-chosen set. It is submodular (diminishing returns), so it is distinct and DECREASES down the
        # batch, the per-experiment "how much does adding THIS one still teach us" that the near-constant
        # intrinsic acquisition alone cannot show (two equally-informative experiments differ by their novelty vs
        # what is already scheduled). This is the real active-learning value, not a fabricated spread.
        marginal = comp["acquisition"] - w_div * _redundancy(c, chosen_cands)
        chosen.append((c, comp, round(marginal, 6)))
    # each returned experiment carries its full acquisition breakdown (composite + components + buildable + the
    # marginal gain and rank), so the UI can rank by, and explain, genuine informativeness, not a near-constant
    # EIG. `expected_info_gain` is kept as a top-level key for backward compatibility.
    return [{**c, **comp, "marginal_gain": mg, "rank": i + 1} for i, (c, comp, mg) in enumerate(chosen)]
