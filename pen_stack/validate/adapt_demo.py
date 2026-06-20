"""WS-F acceptance demo - the adaptation gate on a held-out dataset (deterministic, CI-safe, synthetic).

Demonstrates all WS-F acceptance points without any private data or atlas:
  1. ACTIVATE case: a miscalibrated released score + informative labels -> isotonic recalibration improves
     held-out Brier/ECE -> the gate ACTIVATES the adapted model.
  2. REJECT case: labels independent of the score -> no held-out improvement -> the gate REJECTS (the
     released model is kept). This proves the gate actually guards quality, not just rubber-stamps.
  3. The released model is provably unchanged in both cases (fingerprint identical), and a before/after
     report + model card are written under models/local_<id>/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pen_stack.adapt.pipeline import adapt

_OUT = Path(__file__).resolve().parents[2] / "out" / "adapt_demo.json"
_CHROMS = ["chr1", "chr2", "chr3", "chr4", "chr5", "chr6"]


def _synth(n: int, seed: int, informative: bool) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    latent = rng.random(n) # the true risk in [0,1]
    if informative:
        label = (rng.random(n) < latent).astype(float) # label tracks latent
        score = np.clip(latent ** 2, 0, 1) # SAME ranking, miscalibrated (under-predicts)
    else:
        label = (rng.random(n) < 0.5).astype(float) # label independent of score
        score = rng.random(n)
    chrom = rng.choice(_CHROMS, size=n)
    return pd.DataFrame({"chrom": chrom, "bin": rng.integers(0, 10_000, n), "score": score, "label": label})


def run(out: str | Path = _OUT) -> dict:
    activate = adapt(_synth(400, 1, informative=True), target="safety", method="isotonic",
                     local_id="demo_activate", primary="brier", margin=0.0)
    reject = adapt(_synth(400, 2, informative=False), target="safety", method="isotonic",
                   local_id="demo_reject", primary="brier", margin=0.01)
    report = {
        "activate_case": {"gate": activate["gate"]["decision"], "activated": activate["activated"],
                          "brier_released": activate["held_out_before"]["brier"],
                          "brier_adapted": activate["held_out_after"]["brier"],
                          "auroc_preserved": bool(abs(activate["held_out_before"]["auroc"]
                                                      - activate["held_out_after"]["auroc"]) < 0.05),
                          "released_model_unchanged": activate["released_model_unchanged"]},
        "reject_case": {"gate": reject["gate"]["decision"], "activated": reject["activated"],
                        "brier_released": reject["held_out_before"]["brier"],
                        "brier_adapted": reject["held_out_after"]["brier"],
                        "released_model_unchanged": reject["released_model_unchanged"]},
        "acceptance": {
            "adaptation_improves_or_is_rejected": bool(activate["activated"] and not reject["activated"]),
            "released_model_provably_unchanged": bool(activate["released_model_unchanged"]
                                                      and reject["released_model_unchanged"]),
            "before_after_report_produced": bool(Path(activate["paths"]["report"]).exists()
                                                 and Path(activate["paths"]["model_card"]).exists()),
        },
        "scope": "recalibration / light fine-tuning behind a held-out gate; not unsupervised learning.",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
