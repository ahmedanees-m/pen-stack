"""Paper 4 validation (Phase 1.5) — off-target engine vs naive Hamming.

The headline criterion that does NOT need the paywalled measured data: the position-weight model is
strictly more informative than a position-blind Hamming ranking. On a controlled set of pseudosites with
the SAME mismatch count but different positions, the model ranks biologically plausible off-targets
(distal mismatches, core preserved) above implausible ones (central CT core disrupted), while Hamming
cannot separate them. We quantify this as the AUROC of each score for discriminating
core-preserving (label 1, real off-target risk) vs core-disrupting (label 0, recombination abolished).

The blind recall of Perry 2025's measured off-target coordinates is gated on the paywalled supplementary
(prereg/paper4.yaml) and is not computed here.

Outputs: out/bridge_validation.json.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from pen_stack.bridge.ingest import load_profile_config
from pen_stack.bridge.offtarget import hamming_risk, mismatches, position_weights, risk_score

_OUT = Path(__file__).resolve().parents[2] / "out" / "bridge_validation.json"
_BASES = "ACGT"


def _auroc(scores: list[float], labels: list[int]) -> float:
    """AUROC via the Mann–Whitney U statistic (ties counted as 0.5)."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def build_controlled_set(core: str, n: int = 400, seed: int = 20260602) -> list[dict]:
    """Generate pseudosites with 1-2 mismatches; label 1 if core (CT) preserved, 0 if core disrupted."""
    rng = random.Random(seed)
    cfg = load_profile_config()
    core_idx = [p - 1 for p in cfg["central_core_positions"]]
    rows = []
    for _ in range(n):
        k = rng.choice([1, 2])
        positions = rng.sample(range(len(core)), k)
        site = list(core)
        for p in positions:
            site[p] = rng.choice([b for b in _BASES if b != core[p]])
        site = "".join(site)
        core_disrupted = any(p in core_idx for p in positions)
        rows.append({"site": site, "n_mm": k, "core_preserved": int(not core_disrupted)})
    return rows


def run(core: str = "ACGTGTCTACGTGA", out: str | Path = _OUT) -> dict:
    weights = position_weights()
    rows = build_controlled_set(core)
    model_scores, ham_scores, labels = [], [], []
    for r in rows:
        mm = mismatches(r["site"], core)
        model_scores.append(risk_score(mm, weights))
        ham_scores.append(hamming_risk(mm, len(core)))
        labels.append(r["core_preserved"])
    report = {
        "core": core, "n_pseudosites": len(rows),
        "n_core_preserved": sum(labels), "n_core_disrupted": len(labels) - sum(labels),
        "model_auroc": round(_auroc(model_scores, labels), 4),
        "hamming_auroc": round(_auroc(ham_scores, labels), 4),
        "model_beats_hamming": _auroc(model_scores, labels) > _auroc(ham_scores, labels),
        "note": "position-weight model vs naive Hamming on core-preserving vs core-disrupting pseudosites; "
                "blind recall of Perry 2025 measured off-targets is gated on the paywalled supplementary",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2))
