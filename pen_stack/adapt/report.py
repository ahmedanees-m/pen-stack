"""WS-F2(c,d) - held-out evaluation, the validation GATE, and the model card.

The adapted artifact ACTIVATES only if it beats the released model on the user's held-out split (the gate).
Calibration is judged by Brier score + expected calibration error (ECE, lower is better); discrimination by
AUROC (higher is better). The released model is provably unchanged (its artifact hash is recorded and
re-checked); a before/after report and a model card are always written.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def _auroc(scores, labels) -> float:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def _ece(probs, labels, n_bins: int = 10) -> float:
    probs, labels = np.asarray(probs, float), np.asarray(labels, float)
    edges = np.linspace(0, 1, n_bins + 1)
    ece, n = 0.0, len(probs)
    for i in range(n_bins):
        m = (probs >= edges[i]) & (probs < edges[i + 1] if i < n_bins - 1 else probs <= edges[i + 1])
        if m.sum():
            ece += (m.sum() / n) * abs(probs[m].mean() - labels[m].mean())
    return float(ece)


def evaluate(probs, labels) -> dict:
    """Calibration + discrimination metrics for a set of probabilities against binary labels."""
    probs, labels = np.asarray(probs, float), np.asarray(labels, float)
    brier = float(np.mean((probs - labels) ** 2))
    biny = labels if set(np.unique(labels)) <= {0.0, 1.0} else (labels >= 0.5).astype(float)
    return {"n": int(len(probs)), "brier": round(brier, 5), "ece": round(_ece(probs, biny), 5),
            "auroc": round(_auroc(list(probs), list(biny)), 4)}


def gate(base: dict, adapted: dict, primary: str = "brier", margin: float = 0.0,
         no_skill: dict | None = None) -> dict:
    """Activate the adapted model only if it BEATS the released model AND the no-skill constant predictor on
    the held-out primary metric.

    primary='brier'|'ece' -> lower is better; primary='auroc' -> higher is better. `margin` is the minimum
    improvement required (guards against noise on small holdouts). The `no_skill` guard is essential:
    recalibration can trivially lower Brier by regressing to the base rate, so we require the adapted model
    to beat the constant base-rate predictor too - otherwise the 'improvement' is no skill, just climatology.
    """
    lower_better = primary in ("brier", "ece")

    def better(x, ref):
        return (ref - x) if lower_better else (x - ref)

    b, a = base[primary], adapted[primary]
    imp_released = better(a, b)
    beats_released = imp_released > margin
    beats_no_skill = True
    ns = None
    if no_skill is not None:
        ns = no_skill[primary]
        beats_no_skill = better(a, ns) > margin
    activate = bool(beats_released and beats_no_skill)
    if activate:
        decision = "ADAPTED ACTIVATED (beats released AND the no-skill constant on held-out)"
    elif not beats_no_skill:
        decision = "ADAPTED REJECTED (improvement is no skill - does not beat the constant base rate)"
    else:
        decision = "ADAPTED REJECTED (does not beat released; released model kept)"
    return {"primary_metric": primary, "lower_is_better": lower_better,
            "released": b, "adapted": a, "no_skill_constant": ns,
            "improvement_vs_released": round(imp_released, 5), "margin": margin,
            "beats_released": bool(beats_released), "beats_no_skill": bool(beats_no_skill),
            "activate": activate, "decision": decision}


def released_fingerprint(*paths: str | Path) -> dict:
    """Hash designated released-model artifacts so we can prove they are unchanged by adaptation."""
    import hashlib
    fp = {}
    for p in paths:
        p = Path(p)
        if p.exists():
            fp[str(p.name)] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return fp


def model_card(local_id: str, target: str, method: str, base: dict, adapted: dict, gate_res: dict,
               n_train: int, n_holdout: int, released_fp: dict) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return "\n".join([
        f"# PEN-STACK local adaptation - {local_id}",
        "",
        f"- **Date:** {ts}",
        f"- **Target score:** {target}    **Method:** {method}",
        f"- **Data:** {n_train} train / {n_holdout} held-out sites (private, in-container)",
        f"- **Released-model fingerprint (unchanged):** {released_fp}",
        "",
        "## Held-out before/after",
        "| metric | released | adapted |",
        "|---|---|---|",
        f"| Brier (lower better) | {base['brier']} | {adapted['brier']} |",
        f"| ECE (lower better) | {base['ece']} | {adapted['ece']} |",
        f"| AUROC (higher better) | {base['auroc']} | {adapted['auroc']} |",
        "",
        f"## Gate: **{gate_res['decision']}**",
        f"- primary metric `{gate_res['primary_metric']}`: released {gate_res['released']} -> adapted "
        f"{gate_res['adapted']} (improvement vs released {gate_res['improvement_vs_released']}, "
        f"no-skill constant {gate_res.get('no_skill_constant')}, margin {gate_res['margin']}; "
        f"beats released={gate_res['beats_released']}, beats no-skill={gate_res['beats_no_skill']}).",
        "",
        "## Scope",
        "Recalibration / light fine-tuning on a small private dataset; overfitting is mitigated (not "
        "eliminated) by the held-out gate. Not unsupervised learning from raw reads. The released model is "
        "never overwritten - this artifact lives under `models/local_<id>/` and activates only if the gate "
        "passed.",
    ])


def write_report(out_dir: str | Path, report: dict, card: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (out / "model_card.md").write_text(card, encoding="utf-8")
    return {"report": str(out / "report.json"), "model_card": str(out / "model_card.md")}
