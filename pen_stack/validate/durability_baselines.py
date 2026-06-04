"""Durability baselines (v3.1, WS-B1 + WS-B2).

WS-B2 - multi-mark vs single-mark ablation. Train the durability targets (chromatin -> integrated-cassette
expression, and chromatin -> silenced) on (a) H3K9me3 alone, (b) H3K27ac alone, (c) all available marks,
on the SAME chromosome-grouped folds, and report the deltas. (The TRIP supervision is mESC ES-Bruce4,
which carries five histone marks and no ATAC/DNase, so the ablation is over the five marks, reported
honestly rather than the seven the human atlas uses.)

WS-B1 - endogenous-expression baseline. Predict endogenous expression at each TRIP locus (AlphaGenome
RNA-seq/CAGE, via wgenome/providers.py) and use it directly as a durability predictor; compare against the
TRIP-trained model on the same folds. This quantifies what the writing-specific supervision adds over
predicting endogenous expression. Runs only when an AlphaGenome provider + expression cache are available;
otherwise B1 is reported as pending (B2 is independent).

Acceptance (prereg/ws_b.yaml): B2 - all-marks >= best single-mark on out-of-fold silenced-AUROC, or report
the negative. B1 - report TRIP-trained vs endogenous-proxy Spearman; if the proxy is not beaten by the
pre-registered margin, reframe the durability novelty (e.g. around integration-site genotoxicity).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
_TRIP = _ROOT.parent / "phase_1" / "features" / "trip_with_chromatin.parquet"
_OUT = _ROOT / "out" / "durability_baselines.json"
_MARKS = ["H3K27ac", "H3K4me1", "H3K4me3", "H3K9me3", "H3K27me3"]


def _auroc(scores, labels) -> float:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def _spearman(a, b) -> float:
    a, b = pd.Series(a), pd.Series(b)
    return float(a.corr(b, method="spearman"))


def _cv_oof(df: pd.DataFrame, feats: list[str], seed: int = 42):
    """Chromosome-grouped out-of-fold predictions. Returns (d, sil_oof, exp_oof) aligned to d's rows."""
    import lightgbm as lgb
    from sklearn.model_selection import GroupKFold
    d = df.dropna(subset=feats + ["silenced", "expression"]).copy().reset_index(drop=True)
    groups = d["chrom"].astype("category").cat.codes.to_numpy()
    n_splits = min(5, len(np.unique(groups)))
    gkf = GroupKFold(n_splits=n_splits)
    sil_oof = np.full(len(d), np.nan)
    exp_oof = np.full(len(d), np.nan)
    X = d[feats].to_numpy()
    for tr, te in gkf.split(X, d["silenced"], groups):
        clf = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, verbose=-1, random_state=seed)
        clf.fit(X[tr], d["silenced"].to_numpy()[tr])
        sil_oof[te] = clf.predict_proba(X[te])[:, 1]
        reg = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.05, verbose=-1, random_state=seed)
        reg.fit(X[tr], d["expression"].to_numpy()[tr])
        exp_oof[te] = reg.predict(X[te])
    return d, sil_oof, exp_oof


def _cv_scores(df: pd.DataFrame, feats: list[str], seed: int = 42) -> dict:
    """Chromosome-grouped out-of-fold: silenced AUROC + expression Spearman with a LightGBM model."""
    d, sil_oof, exp_oof = _cv_oof(df, feats, seed)
    return {"silenced_auroc": round(_auroc(sil_oof, d["silenced"].to_numpy()), 4),
            "expression_spearman": round(_spearman(exp_oof, d["expression"]), 4),
            "n": int(len(d)), "n_features": len(feats)}


def multimark_ablation() -> dict:
    if not _TRIP.exists():
        return {"available": False, "note": "TRIP-with-chromatin not present"}
    df = pd.read_parquet(_TRIP)
    subsets = {"H3K9me3_only": ["H3K9me3"], "H3K27ac_only": ["H3K27ac"], "all_marks": _MARKS}
    res = {k: _cv_scores(df, v) for k, v in subsets.items()}
    best_single = max(res["H3K9me3_only"]["silenced_auroc"], res["H3K27ac_only"]["silenced_auroc"])
    return {"available": True, "subsets": res,
            "all_marks_silenced_auroc": res["all_marks"]["silenced_auroc"],
            "best_single_mark_silenced_auroc": round(best_single, 4),
            "all_marks_beats_best_single": bool(res["all_marks"]["silenced_auroc"] >= best_single)}


def endogenous_expression_baseline(n_sample: int = 150, seed: int = 20260604,
                                   ontology: str = "EFO:0005483", margin: float = 0.05,
                                   offline: bool = False) -> dict:
    """WS-B1. AlphaGenome endogenous ES-Bruce4 RNA-seq at each TRIP integration site, used DIRECTLY as a
    durability predictor, vs the TRIP-trained model - both scored by Spearman against the measured cassette
    `expression` on the SAME seeded sample of loci. ES-Bruce4 (EFO:0005483) is AlphaGenome's exact match to
    the cell line the TRIP supervision was measured in, so this is a fair same-cell-line baseline.

    Runs on a seeded sample (default 150 loci) because a per-locus 1 Mb prediction over all 11,433 sites is
    API-prohibitive; predictions are cached so the result is reproducible offline. If the provider is absent,
    returns pending. Acceptance (prereg/ws_b.yaml): TRIP-trained Spearman beats the endogenous proxy by
    >= `margin`; otherwise reframe the durability novelty (negative reported honestly).
    """
    try:
        from pen_stack.wgenome.providers import AlphaGenomeProvider
    except Exception:  # noqa: BLE001
        return {"available": False, "provider_present": False, "note": "providers module import failed"}
    provider = AlphaGenomeProvider(assembly="mm10")
    if (not provider.available() and not offline) or not _TRIP.exists():
        return {"available": False, "provider_present": provider.available(),
                "note": "AlphaGenome package+key or TRIP data absent; B1 pending (B2/B3 independent)."}

    df = pd.read_parquet(_TRIP)
    d, _sil, exp_oof = _cv_oof(df, _MARKS, seed=42)          # TRIP-trained OOF over all loci
    d = d.assign(trip_oof=exp_oof)
    sample = d.sample(n=min(n_sample, len(d)), random_state=seed).reset_index(drop=True)

    proxy = []
    for r in sample.itertuples():
        rec = provider.expression(r.chrom, int(r.pos), int(r.pos), ontology=ontology, organism="mouse",
                                  offline=offline)
        proxy.append(rec.get("rna_seq_mean", np.nan))
    sample = sample.assign(endo_proxy=proxy).dropna(subset=["endo_proxy", "trip_oof", "expression"])
    if offline and len(sample) == 0:
        return {"available": False, "provider_present": provider.available(),
                "note": "offline: AlphaGenome expression cache empty; run B1 live once to populate."}

    sp_trip = _spearman(sample["trip_oof"], sample["expression"])
    sp_proxy = _spearman(sample["endo_proxy"], sample["expression"])
    return {"available": True, "n_sample": int(len(sample)), "ontology": ontology,
            "cell_line": "ES-Bruce4 (matches TRIP supervision cell line)",
            "trip_trained_spearman": round(sp_trip, 4),
            "endogenous_proxy_spearman": round(sp_proxy, 4),
            "delta": round(sp_trip - sp_proxy, 4), "margin": margin,
            "trip_beats_proxy_by_margin": bool((sp_trip - sp_proxy) >= margin),
            "interpretation": "writing-specific (TRIP-trained) signal beyond endogenous expression"
                              if (sp_trip - sp_proxy) >= margin else
                              "endogenous expression explains most of the durability signal at this sample; "
                              "reframe durability novelty toward integration-site genotoxicity (prereg downgrade)"}


def run(out: str | Path = _OUT, b1_offline: bool = True) -> dict:
    # B1 defaults to offline (cache-only) so run()/CI never make live API calls; populate the cache once with
    # endogenous_expression_baseline(offline=False), then this reproduces the pilot numbers offline.
    report = {"B2_multimark_ablation": multimark_ablation(),
              "B1_endogenous_expression_baseline": endogenous_expression_baseline(offline=b1_offline)}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
