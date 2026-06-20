"""Calibrate the immune-risk PROXIES against OBSERVED immunogenicity outcomes (v5.6, WS-CALIB).

The v5.2-v5.6 immune axes are *proxies*: sequence/mechanistic (CD8 epitope load, innate CpG/dsRNA) or
population (anti-vector + anti-PEG seroprevalence). This module tests, two-sided and (the v3.4
discipline), whether a proxy actually CORRELATES with an observed immune response, and **labels each axis**
either "outcome-validated (rho=..., CI ...)" or "mechanistic/population proxy, not outcome-validated".

SCOPE (the central point of this workstream). Public, citable, paired (proxy, observed-immunogenicity-
outcome) data is sparse and heterogeneous. We do NOT fabricate an outcome dataset to manufacture a positive
result. `calibrate_axis()` computes a real Spearman rho + bootstrap CI when given >=6 paired points (and only
calls an axis "validated" when the CI excludes zero); with insufficient data it returns the conservative
"mechanistic_proxy" label. The current per-axis status (`AXIS_STATUS`) is therefore *proxy* for every axis,
that label is the deliverable, and it travels with the unified immune profile (v5.6 WS-PROFILE).
"""
from __future__ import annotations

import json
from pathlib import Path

_MIN_N = 6 # below this, too few paired points to validate (abstention)


def _bootstrap_spearman_ci(x, y, reps: int = 2000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI for Spearman's rho (resample paired observations with replacement)."""
    import numpy as np
    from scipy.stats import spearmanr
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    rng = np.random.default_rng(seed)
    rhos = []
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        if len(set(x[idx])) < 2 or len(set(y[idx])) < 2:
            continue
        rhos.append(spearmanr(x[idx], y[idx]).statistic)
    if not rhos:
        return (float("nan"), float("nan"))
    lo = float(np.percentile(rhos, 100 * alpha / 2))
    hi = float(np.percentile(rhos, 100 * (1 - alpha / 2)))
    return (round(lo, 3), round(hi, 3))


def calibrate_axis(proxy_scores: list[float], observed: list[float], *, axis: str,
                   reps: int = 2000) -> dict:
    """Spearman rho of a proxy vs an observed immune-response outcome + bootstrap CI.

    Returns a status of `outcome_validated` ONLY when N>=6 AND the bootstrap CI excludes zero; `weak_proxy`
    when N>=6 but the CI includes zero; `mechanistic_proxy` when there are too few paired points. Never
    upgrades an axis to "validated" without a CI excluding zero (pre-registered gate)."""
    n = len(proxy_scores)
    if n < _MIN_N or len(observed) != n:
        return {"axis": axis, "status": "mechanistic_proxy", "n": n,
                "reason": f"insufficient paired outcome data (N={n} < {_MIN_N})",
                "label": f"{axis}: mechanistic/population proxy, NOT outcome-validated"}
    from scipy.stats import spearmanr
    rho = float(spearmanr(proxy_scores, observed).statistic)
    lo, hi = _bootstrap_spearman_ci(proxy_scores, observed, reps=reps)
    validated = (lo == lo) and lo > 0 # CI excludes zero (and not NaN)
    return {"axis": axis, "status": "outcome_validated" if validated else "weak_proxy",
            "spearman": round(rho, 3), "ci": [lo, hi], "n": n,
            "label": (f"{axis}: outcome-validated (rho={rho:.2f}, CI {lo:.2f}, {hi:.2f}, N={n})" if validated
                      else f"{axis}: proxy, correlation not established (CI includes 0, N={n})")}


# Current status of each real axis. No axis has a sufficient public paired (proxy, observed-outcome)
# dataset, so every axis is a labelled PROXY. Each `reason` states the directional evidence that exists and why
# it is not yet a calibrated validation. (When real outcome data is assembled, call calibrate_axis() and
# promote the entry, never by hand.)
AXIS_STATUS: dict[str, dict] = {
    "genotoxicity": {
        "status": "mechanistic_proxy",
        "label": "genotoxicity: mechanistic proxy, NOT outcome-validated",
        "reason": "integration-site oncogene-proximity (VISDB x COSMIC) is directionally consistent with the "
                  "gammaretroviral-vs-lentiviral insertional-oncogenesis record (SCID-X1), but the vector-class "
                  "N is far too small for a calibrated CI."},
    "cd8_epitope": {
        "status": "mechanistic_proxy",
        "label": "cd8_epitope: mechanistic proxy, NOT outcome-validated",
        "reason": "MHC-I presentation reproduces the documented AAV<adenovirus adaptive ordering, but is not "
                  "calibrated against observed anti-capsid T-cell response RATES (no public paired dataset)."},
    "innate": {
        "status": "mechanistic_proxy",
        "label": "innate: mechanistic proxy (partial), NOT outcome-validated",
        "reason": "CpG O/E + dsRNA is a partial sequence proxy (nucleoside modification is out of sequence "
                  "scope) and is not calibrated against observed innate-cytokine outcomes."},
    "preexisting_nab": {
        "status": "population_proxy",
        "label": "preexisting_nab: population proxy, predicts eligibility, not response magnitude",
        "reason": "serosurvey prevalence IS the measured exclusion quantity; it predicts patient ELIGIBILITY, "
                  "not the magnitude of a realized immune response."},
    "anti_peg": {
        "status": "population_proxy",
        "label": "anti_peg: population proxy, gates re-dosing, not calibrated to re-dosing failure",
        "reason": "anti-PEG seroprevalence gates re-dosing; not calibrated against observed re-dosing-failure "
                  "rates (and induced post-dose-1 anti-PEG is a separate dynamic)."},
    "mhc2_writer": { # v6.9 G-WS1, CD4/MHC-II epitope load over the writer enzyme
        "status": "mechanistic_proxy",
        "label": "mhc2_writer: population proxy, NOT outcome-validated",
        "reason": "real NetMHCIIpan-4.0 eluted-ligand MHC-II epitope load over a frequent-HLA panel (v6.9.2; the "
                  "v6.9.0 P1-anchor proxy was replaced), a population-level presentation potential, NOT a "
                  "patient-HLA-specific magnitude or an observed-ADA-validated number."},
    "ada_writer": { # v6.9 G-WS2, ADA-risk (MHC-II x foreignness, self-tolerance filtered)
        "status": "mechanistic_proxy",
        "label": "ada_writer: mechanistic/population proxy, NOT outcome-validated",
        "reason": "ADA-risk = MHC-II epitope density x foreignness (self-tolerance filtered) recovers immunogenic-"
                  "vs-tolerated, but is not calibrated against observed ADA incidence at public-data power."},
}


def axis_label(axis: str) -> str:
    """The current validation label for an axis (travels with the unified immune profile). Unknown axis ->
    an explicit proxy label, never a silent 'validated'."""
    return AXIS_STATUS.get(axis, {}).get("label", f"{axis}: status unknown, treated as unvalidated proxy")


def run(out: str | Path = "phase_5.6/out/immune_calibration.json") -> dict:
    """Emit the per-axis calibration report. With no sufficient public outcome dataset, every axis is a
    labelled proxy, the negative is reported verbatim (no axis is forced to 'validated')."""
    report = {"workstream": "WS-CALIB", "min_n_to_validate": _MIN_N,
              "axes": AXIS_STATUS,
              "summary": "no axis has a sufficient public paired (proxy, observed-immunogenicity) dataset; "
                         "all axes are labelled mechanistic/population proxies (not outcome-validated). "
                         "calibrate_axis() will compute rho + bootstrap CI and promote an axis only when "
                         "N>=6 and the CI excludes zero.",
              "no_fabrication": True}
    p = Path(out)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError:
        pass
    return report
