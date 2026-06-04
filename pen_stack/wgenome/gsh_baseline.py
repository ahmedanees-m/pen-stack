"""Genomic safe-harbour (GSH) rule-set baseline (v3.1, WS-B3).

A published multi-criterion GSH rule (Papapetrou/Sadelain/Pellenz style) implemented from the existing
per-bin annotations: outside a gene, and minimum distances to the nearest TSS, cancer/oncogene, and
essential gene. We compute it as a graded safety score and compare its **safe-harbour discrimination**
(held-out validated GSH vs matched controls, reusing WS-A3) against the learned writability model.

The headline safety claim is **discrimination** (validated GSH vs matched controls), NOT the
`genotoxic_cis` AUROC - which is circular (its label is proximity to five oncogenes, i.e. the distance
baseline's own definition) and is demoted to a clearly-labeled diagnostic.

Acceptance (prereg/ws_b.yaml): the learned model beats the GSH rule-set on discrimination AUROC; report
the delta. If it does not, say so - the rule is a strong, interpretable baseline.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
_OUT = _ROOT / "out" / "gsh_baseline.json"

# published-style minimum distances (bp). Graded: a bin scores higher the further it clears each minimum.
_MIN_DIST = {"dist_tss": 5000, "dist_oncogene": 50000, "dist_essential": 50000}


def gsh_rule_score(df: pd.DataFrame) -> pd.Series:
    """Graded GSH-rule safety score in [0,1]: mean over criteria of min(dist / threshold, 1)."""
    parts = []
    for col, thr in _MIN_DIST.items():
        if col in df.columns:
            parts.append((df[col].clip(lower=0) / thr).clip(upper=1.0))
    if not parts:
        return pd.Series(0.0, index=df.index)
    return pd.concat(parts, axis=1).mean(axis=1)


def _auroc(scores, labels) -> float:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def run(ct: str = "k562", out: str | Path = _OUT) -> dict:
    """Discrimination AUROC: GSH rule-set vs the learned writability model, on the WS-A3 GSH/controls."""
    from pen_stack.validate.blind_gsh_discovery import _load_features, gsh_positives
    import yaml
    cfg = yaml.safe_load((_ROOT / "configs" / "gsh_validated_heldout.yaml").read_text(encoding="utf-8"))
    df = _load_features(ct)
    safe = pd.read_parquet(_ROOT.parent / "phase_1" / "features" / "safety_annot.parquet")[
        ["chrom", "bin", "dist_tss", "dist_oncogene", "dist_essential"]]
    df = df.drop(columns=[c for c in ["dist_tss", "dist_oncogene", "dist_essential"] if c in df.columns]).merge(
        safe, on=["chrom", "bin"], how="left")
    df["gsh_rule"] = gsh_rule_score(df)

    positives = gsh_positives(df, cfg)
    controls = pd.read_parquet(_ROOT / "data" / "gsh_matched_controls.parquet")
    idx = df.set_index(["chrom", "bin"])
    def vals(frame, col):
        return [idx.loc[(r.chrom, r.bin), col] for r in frame.itertuples() if (r.chrom, r.bin) in idx.index]
    pr, cr = vals(positives, "gsh_rule"), vals(controls, "gsh_rule")
    pw, cw = vals(positives, "writability"), vals(controls, "writability")
    labels_r = [1] * len(pr) + [0] * len(cr)
    labels_w = [1] * len(pw) + [0] * len(cw)
    auroc_rule = _auroc(pr + cr, labels_r)
    auroc_learned = _auroc(pw + cw, labels_w)

    # Bootstrap 95% CI for the learned AUROC and the learned-minus-rule delta (prereg/ws_b.yaml: report delta
    # AND CI). Resample positives and controls independently (stratified). With only ~5 GSH positives the CI
    # is WIDE by construction - reported honestly rather than hidden.
    rng = np.random.default_rng(20260604)
    npos, nctrl = len(pw), len(cw)
    boot_learned, boot_delta = [], []
    if npos and nctrl:
        pw_a, cw_a = np.array(pw, float), np.array(cw, float)
        pr_a, cr_a = np.array(pr, float), np.array(cr, float)
        for _ in range(2000):
            pi = rng.integers(0, npos, npos)
            ci = rng.integers(0, nctrl, nctrl)
            lab = [1] * npos + [0] * nctrl
            al = _auroc(list(pw_a[pi]) + list(cw_a[ci]), lab)
            ar = _auroc(list(pr_a[pi]) + list(cr_a[ci]), lab)
            if not (np.isnan(al) or np.isnan(ar)):
                boot_learned.append(al)
                boot_delta.append(al - ar)

    def _ci(b):
        return [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)] if b else None

    report = {
        "primary_safety_metric": "safe-harbour discrimination (validated GSH vs matched controls)",
        "n_positives": npos, "n_controls": nctrl,
        "auroc_learned_writability": round(auroc_learned, 4),
        "auroc_learned_ci95": _ci(boot_learned),
        "auroc_gsh_ruleset_baseline": round(auroc_rule, 4) if not np.isnan(auroc_rule) else None,
        "learned_beats_ruleset": bool(auroc_learned > auroc_rule) if not np.isnan(auroc_rule) else None,
        "delta": round(auroc_learned - auroc_rule, 4) if not np.isnan(auroc_rule) else None,
        "delta_ci95": _ci(boot_delta),
        "delta_ci_excludes_zero": (bool(_ci(boot_delta)[0] > 0) if boot_delta else None),
        "ci_note": f"bootstrap 2000x over {npos} positives + {nctrl} controls (seed 20260604); CI is wide "
                   "because only ~5 validated GSH anchor the positives - reported honestly.",
        "genotoxic_cis_auroc": "DEMOTED to a diagnostic - circular (label = proximity to 5 oncogenes = the "
                               "distance baseline's own definition); not a safety headline",
        "rule_thresholds_bp": _MIN_DIST,
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
