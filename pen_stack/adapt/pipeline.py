"""WS-F2 - the adaptation pipeline (ingest -> split -> recalibrate/finetune -> held-out gate -> version).

`adapt()` is the one entry point. It splits the user's sites into train/held-out (chromosome-grouped when
possible), fits the adaptation on train, scores the released vs adapted model on the SAME held-out split,
and applies the validation gate. The adapted artifact is written under models/local_<id>/ ONLY - the
released model is never overwritten, and its fingerprint is checked before/after to prove it (acceptance).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pen_stack.adapt import report as R
from pen_stack.adapt.recalibrate import recalibrate

_ROOT = Path(__file__).resolve().parents[2]
_MODELS = _ROOT / "models"
# released score-producing modules - the "released model" we must prove is unchanged by adaptation.
_RELEASED = [_ROOT / "pen_stack" / "wgenome" / m for m in ("safety.py", "durability.py", "writability.py")]


def _split(df: pd.DataFrame, seed: int, holdout_frac: float = 0.3):
    """Chromosome-grouped holdout when >=2 chromosomes (no leakage); else a seeded random split."""
    rng = np.random.default_rng(seed)
    chroms = df["chrom"].unique()
    if len(chroms) >= 2:
        n_ho = max(1, int(round(len(chroms) * holdout_frac)))
        ho_chroms = set(rng.choice(chroms, size=n_ho, replace=False))
        mask = df["chrom"].isin(ho_chroms)
    else:
        mask = pd.Series(rng.random(len(df)) < holdout_frac, index=df.index)
    return df[~mask].reset_index(drop=True), df[mask].reset_index(drop=True)


def adapt(df: pd.DataFrame, target: str = "safety", method: str = "isotonic", local_id: str = "local",
          seed: int = 20260604, primary: str = "brier", margin: float = 0.0,
          feature_cols: list[str] | None = None, models_dir: str | Path = _MODELS) -> dict:
    """Recalibrate (or fine-tune) the released `target` score on the user frame (needs 'score' + 'label').

    Returns the held-out before/after report + the gate decision + the artifact paths. The adapted model is
    activated (written + flagged) only if it beats the released model on the held-out split.
    """
    if "score" not in df.columns or "label" not in df.columns:
        raise ValueError("adapt() needs standardized columns 'score' and 'label' (see adapt.ingest)")
    fp_before = R.released_fingerprint(*_RELEASED)

    train, holdout = _split(df, seed)
    if len(train) < 5 or len(holdout) < 3:
        raise ValueError(f"not enough data after split (train={len(train)}, holdout={len(holdout)})")

    base_holdout = np.clip(holdout["score"].to_numpy(float), 0, 1) # released score as a probability
    if method == "isotonic":
        cal = recalibrate(train["score"], train["label"])
        adapted_holdout = cal.transform(holdout["score"])
        artifact = "calibrator.json"
    elif method == "finetune":
        from pen_stack.adapt.finetune import finetune_head, predict_proba
        cols = feature_cols or ["score"]
        model = finetune_head(train[cols].to_numpy(float), train["label"], seed=seed)
        adapted_holdout = predict_proba(model, holdout[cols].to_numpy(float))
        cal, artifact = None, "head.txt"
    else:
        raise ValueError(f"unknown method: {method!r} (use 'isotonic' or 'finetune')")

    # no-skill constant predictor: the TRAIN base rate applied to every held-out site (no leakage). The
    # adapted model must beat this too, else its 'improvement' is just regression to climatology.
    base_rate = float(np.clip(train["label"].mean(), 1e-6, 1 - 1e-6))
    no_skill = R.evaluate(np.full(len(holdout), base_rate), holdout["label"])

    base = R.evaluate(base_holdout, holdout["label"])
    adapted = R.evaluate(adapted_holdout, holdout["label"])
    gate = R.gate(base, adapted, primary=primary, margin=margin, no_skill=no_skill)

    out_dir = Path(models_dir) / f"local_{local_id}"
    fp_after = R.released_fingerprint(*_RELEASED)
    released_unchanged = fp_before == fp_after
    report = {"local_id": local_id, "target": target, "method": method,
              "n_train": int(len(train)), "n_holdout": int(len(holdout)),
              "held_out_before": base, "held_out_after": adapted, "held_out_no_skill": no_skill, "gate": gate,
              "released_model_unchanged": released_unchanged,
              "released_fingerprint": fp_after, "activated": gate["activate"]}
    card = R.model_card(f"local_{local_id}", target, method, base, adapted, gate,
                        len(train), len(holdout), fp_after)
    paths = R.write_report(out_dir, report, card)
    # persist the adapted artifact ONLY when the gate passes; otherwise remove any stale artifact so a
    # previously-activated adaptation that now fails the gate is not left active (released model stays in force).
    artifact_path = out_dir / artifact
    if gate["activate"]:
        if method == "isotonic":
            cal.save(artifact_path)
        else:
            model.booster_.save_model(str(artifact_path))
        paths["artifact"] = str(artifact_path)
    else:
        for stale in (out_dir / "calibrator.json", out_dir / "head.txt"):
            if stale.exists():
                stale.unlink()
    report["paths"] = paths
    return report
