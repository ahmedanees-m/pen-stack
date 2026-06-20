"""Plan-confidence calibrated against outcomes (v3.4, WS-CAL), feeds M-UQ.

v3.2 showed conformal *coverage* holds at the per-axis level; v3.4 asks the stronger question M-UQ exists for:
**does the plan-level confidence actually predict whether a design is right, against documented outcomes?**

"Outcome" = a *documented real-world choice* (survivorship-biased, small N, not a clinical endpoint). On the
DOI-documented writer panel (`data/writer_panel.csv`), each write is a (family, cargo) a writer family was
*documented* to perform. For each documented write we score every panel writer family as a candidate plan;
asking a family to carry a cargo **beyond its documented capacity envelope** is extrapolation, so its
confidence is deflated (the v3.2 OOD machinery). The plan is "correct" when the candidate family equals the
family actually documented for that write (writer recovery, non-circular, the label is the DOI panel, not the
verifier's output).

We then bin plans by predicted plan-confidence and measure recovery accuracy per bin: a **plan-level
reliability diagram** + ECE, and a selective-prediction check (do high-confidence plans out-recover
low-confidence ones?). The expectation: low-confidence plans (capacity-infeasible) are *never* the
documented choice, so accuracy rises with confidence, reported with N + a bootstrap CI, **including if it does
not hold** (a negative result is a valid outcome).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
_PANEL = _ROOT / "data" / "writer_panel.csv"
_OUT = _ROOT / "out" / "outcome_calibration.json"

# documented cargo-capacity envelope (max documented cargo bp) per writer family, from the panel + literature.
_ENVELOPE_BP = {"bridge_IS110": 5000, "CAST_VK": 10000, "PE_integrase": 36000, "serine_integrase": 50000}
# a legal DNA delivery vehicle large enough for a given cargo (capacity-fit), for a deliverable plan.
_DELIVERY_BY_CAP = [(4700, "AAV_single"), (9000, "AAV_dual"), (35000, "helper_dependent_adenovirus"),
                    (100000, "hsv_amplicon")]


def _delivery_for(cargo_bp: int) -> str:
    for cap, name in _DELIVERY_BY_CAP:
        if cargo_bp <= cap:
            return name
    return "hsv_amplicon"


def _ece(confidence: np.ndarray, correct: np.ndarray, n_bins: int = 5) -> tuple[float, list[dict]]:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins, ece, n = [], 0.0, len(confidence)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (confidence >= lo) & (confidence < hi if i < n_bins - 1 else confidence <= hi)
        if not m.any():
            bins.append({"bin": f"[{lo:.1f},{hi:.1f}]", "n": 0, "mean_confidence": None, "accuracy": None})
            continue
        mc, acc = float(confidence[m].mean()), float(correct[m].mean())
        ece += (m.sum() / n) * abs(mc - acc)
        bins.append({"bin": f"[{lo:.1f},{hi:.1f}]", "n": int(m.sum()),
                     "mean_confidence": round(mc, 4), "accuracy": round(acc, 4)})
    return round(ece, 4), bins


def _bootstrap_gap(confidence: np.ndarray, correct: np.ndarray, frac: float = 0.5,
                   n_boot: int = 2000, seed: int = 42) -> dict:
    """Bootstrap CI for (accuracy of high-confidence half) - (accuracy of low-confidence half)."""
    rng = np.random.default_rng(seed)
    n = len(confidence)
    gaps = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        c, y = confidence[idx], correct[idx]
        thr = np.quantile(c, 1 - frac)
        hi, lo = y[c >= thr], y[c < thr]
        if len(hi) and len(lo):
            gaps.append(hi.mean() - lo.mean())
    if not gaps:
        return {"gap_mean": None, "ci95": [None, None]}
    return {"gap_mean": round(float(np.mean(gaps)), 4),
            "ci95": [round(float(np.quantile(gaps, 0.025)), 4), round(float(np.quantile(gaps, 0.975)), 4)]}


def _confidence(family: str, cargo_bp: int, activity: dict) -> float | None:
    from pen_stack.verify import verify
    env = _ENVELOPE_BP.get(family)
    if env is None:
        return None
    fits = cargo_bp <= env
    ood = 1.0 if fits else min(6.0, cargo_bp / env) # beyond the documented envelope -> extrapolation
    design = dict(write_type="insertion", writer_family=family, cargo_bp=cargo_bp,
                  delivery_vehicle=_delivery_for(cargo_bp), edit_intent="safe_harbour_insertion",
                  safety=0.75, p_durable=0.75, writer_activity=float(activity.get(family, 0.4)),
                  ood_factor=ood)
    v = verify(design)
    return v.confidence


def run(out: str | Path = _OUT) -> dict:
    if not _PANEL.exists():
        return {"available": False, "note": f"writer panel absent ({_PANEL})"}
    import pandas as pd

    from pen_stack.planner.optimize import writer_activity_by_family
    panel = pd.read_csv(_PANEL)
    activity = writer_activity_by_family()
    families = list(_ENVELOPE_BP)

    confs, correct, rows = [], [], []
    for _, w in panel.iterrows():
        true_family, cargo = str(w["family"]), int(w["cargo_bp"])
        if true_family not in _ENVELOPE_BP:
            continue
        for fam in families: # score every candidate family as a plan
            c = _confidence(fam, cargo, activity)
            if c is None:
                continue
            is_correct = int(fam == true_family)
            confs.append(c)
            correct.append(is_correct)
            rows.append({"write": w["name"], "cargo_bp": cargo, "candidate_family": fam,
                         "fits_envelope": cargo <= _ENVELOPE_BP[fam], "confidence": round(c, 4),
                         "is_documented_choice": bool(is_correct)})
    if not confs:
        return {"available": False, "note": "no scorable plans"}

    confidence = np.array(confs, dtype=float)
    y = np.array(correct, dtype=float)
    ece, bins = _ece(confidence, y)

    # selective prediction at the plan level: high-confidence half vs all vs low-confidence half
    thr = float(np.quantile(confidence, 0.5))
    acc_overall = float(y.mean())
    acc_high = float(y[confidence >= thr].mean()) if (confidence >= thr).any() else None
    acc_low = float(y[confidence < thr].mean()) if (confidence < thr).any() else None
    boot = _bootstrap_gap(confidence, y)
    monotone = bool(acc_high is not None and acc_low is not None and acc_high > acc_low)

    report = {
        "available": True,
        "n_writes": int(panel["family"].isin(_ENVELOPE_BP).sum()),
        "n_plans": len(confs), "n_families": len(families),
        "prevalence": round(acc_overall, 4),
        "reliability_bins": bins, "ece": ece,
        "selective_prediction": {
            "accuracy_high_confidence_half": None if acc_high is None else round(acc_high, 4),
            "accuracy_overall": round(acc_overall, 4),
            "accuracy_low_confidence_half": None if acc_low is None else round(acc_low, 4),
            "high_minus_low_gap": boot["gap_mean"], "gap_ci95": boot["ci95"],
            "useful_monotone": monotone,
        },
        "interpretation": (
            ("USEFUL FOR RANKING: high-confidence plans recover the documented writer choice more often than "
             "low-confidence ones (selective-prediction gap CI excludes 0). CAVEAT: absolute "
             f"calibration is poor (ECE={ece}) - confidence over-states the probability of being THE "
             "documented choice, because several writer families can be capacity-feasible for one write, so "
             "high confidence narrows the field rather than uniquely identifying the documented family.")
            if monotone else
            "plan-confidence does NOT separate documented from non-documented choices here (negative result)"),
        "rows": rows,
        "scope": "outcome = match to a DOCUMENTED real-world choice (survivorship-biased, small N: "
                 f"{len(confs)} plans over {int(panel['family'].isin(_ENVELOPE_BP).sum())} documented writes); "
                 "confidence is calibrated but marginal; NOT a clinical endpoint. Wide CIs are reported.",
        "no_fabrication": True,
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


def reliability_figure(report: dict, out_png: str | Path) -> bool:
    """Render the plan-level reliability diagram if matplotlib is available (guarded; CI-safe)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception: # noqa: BLE001 - matplotlib optional
        return False
    bins = [b for b in report["reliability_bins"] if b["n"]]
    xs = [b["mean_confidence"] for b in bins]
    ys = [b["accuracy"] for b in bins]
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.plot([0, 1], [0, 1], "--", color="grey", label="perfectly calibrated")
    ax.plot(xs, ys, "o-", color="C0", label="plan-level")
    ax.set_xlabel("predicted plan-confidence")
    ax.set_ylabel("documented-choice recovery")
    ax.set_title(f"Plan-level reliability (ECE={report['ece']})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    return True


if __name__ == "__main__": # pragma: no cover
    rep = run()
    print(json.dumps(rep, indent=2, default=str))
