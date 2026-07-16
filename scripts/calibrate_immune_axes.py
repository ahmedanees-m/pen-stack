"""Attempt to OUTCOME-VALIDATE every immune/expression proxy against INDEPENDENT measured data.

The gate (pen_stack.validate.immune_calibration.calibrate_axis) upgrades an axis to "outcome_validated"
ONLY when N>=6 paired (proxy, independent-measured-outcome) points exist AND the bootstrap Spearman CI excludes
zero. This script runs that gate for each axis with the best public INDEPENDENT data we could curate, and prints
the status. It NEVER fabricates an outcome dataset to manufacture a positive result.

Run: `python scripts/calibrate_immune_axes.py` (CI-safe; pure-Python + scipy).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from pen_stack.validate.immune_calibration import calibrate_axis

_ROOT = Path(__file__).resolve().parents[1]


def _midpoint_score(rng: list[float]) -> float:
    """preexisting_score = 1 − midpoint(seroprevalence %)/100 (matches seroprevalence_oracle)."""
    return round(1 - (sum(rng) / 2) / 100, 4)


def nab() -> dict:
    """pre-existing NAb: 6 AAV serotypes scored. Proxy = Calcedo+Boutin midpoints; observed = INDEPENDENT
    Basque cohort (Navarro-Oliveros 2024). The one axis that reaches N=6."""
    sero = yaml.safe_load((_ROOT / "configs/seroprevalence.yaml").read_text(encoding="utf-8"))["serotypes"]
    obs_cfg = yaml.safe_load((_ROOT / "configs/calibration/preexisting_nab_independent.yaml").read_text(encoding="utf-8"))
    obs_prev = obs_cfg["observed_nab_prevalence_pct"]
    serotypes = [s for s in obs_prev if s in sero]
    proxy = [_midpoint_score(sero[s]["nab_seroprevalence_pct"]) for s in serotypes]
    observed = [round(1 - obs_prev[s] / 100, 4) for s in serotypes] # eligibility (same direction)
    res = calibrate_axis(proxy, observed, axis="preexisting_nab")
    res["entities"] = serotypes
    res["independent_source"] = obs_cfg["source"]["citation"]
    return res


# Structural barrier: the other proxies score FEWER than the 6 entities the gate needs to even run.
_STRUCTURAL = {
    "genotoxicity": {"entities_scored": 3, "what": "vector classes (HIV/lentiviral, HTLV/deltaretroviral, MLV/gammaretroviral)",
                     "outcome_needed": "measured genotoxicity per vector (IVIM mutagenic frequency / tumour-prone mouse incidence)",
                     "barrier": "N=3 < 6, the proxy scores only 3 vector classes; cannot run the gate."},
    "cd8_epitope": {"entities_scored": 5, "what": "capsids (AAV2, Ad5, VSVg, +2)",
                    "outcome_needed": "measured anti-capsid CD8 T-cell response rates per serotype",
                    "barrier": "N≈5 < 6, too few capsids scored; cannot run the gate."},
    "innate": {"entities_scored": 0, "what": "no fixed entity set (per-cargo-sequence)",
               "outcome_needed": "measured TLR9/RIG-I innate-activation per sequence",
               "barrier": "no fixed paired set; cannot assemble ≥6 independent points."},
    "anti_peg": {"entities_scored": 1, "what": "a single population prevalence value",
                 "outcome_needed": "measured re-dosing-failure rate / independent anti-PEG prevalence",
                 "barrier": "N=1, a single population statistic; cannot run the gate."},
    "relative_expression": {"entities_scored": 5, "what": "named promoters (ef1a, cag, cmv, pgk, ubc)",
                            "outcome_needed": "MPRA / independent comparative promoter-strength measurements",
                            "barrier": "N=5 < 6, palette must be expanded to ≥6 promoters with independent strengths."},
}


def expression() -> dict:
    """relative-expression promoter ordinal, INDEPENDENT validation. The palette is anchored to Qin 2010 /
    Norrman 2010, so the test is whether it predicts a DIFFERENT study's measurements: Damdindorj 2014
    (AAV context, colon/fibroblast lines). It does NOT, the two studies genuinely disagree (Damdindorj found
    CMV strongest, CAG/EF1a much weaker; Qin found the opposite) because promoter strength is context-dependent.
    A consistency check vs Qin alone gives rho=0.94 but is CIRCULAR (same source), not reported as validation."""
    from pen_stack.twin.mechanistic import promoter_info
    proms = ["cmv", "actb", "sv40", "ef1a", "cag", "hsv_tk"] # overlap with Damdindorj 2014
    proxy = [float(promoter_info(p)["strength"]) for p in proms]
    observed = [1.00, 0.80, 0.65, 0.50, 0.40, 0.20] # Damdindorj 2014 (independent) ranking
    res = calibrate_axis(proxy, observed, axis="relative_expression")
    res["entities"] = proms
    res["note"] = ("INDEPENDENT test vs Damdindorj 2014 (10.1371/journal.pone.0106472), palette is "
                   "Qin/Norrman-anchored; the studies disagree (context-dependence), so it does NOT validate")
    return res


def main() -> None:
    print("=" * 88)
    print("PEN-STACK proxy → outcome validation (gate: N>=6 AND bootstrap Spearman CI excludes 0)")
    print("=" * 88)

    r = nab()
    print(f"\n[preexisting_nab] N={r['n']} serotypes={r['entities']}")
    print(f" independent outcome: {r['independent_source']}")
    print(f" Spearman rho = {r['spearman']} CI = {r['ci']} -> status = {r['status'].upper()}")
    print(f" {r['label']}")
    if r["status"] != "outcome_validated":
        print(" => stays (population proxy). Note: at N=6 the bootstrap CI is ~[-1,1], it cannot exclude 0,")
        print(" so even a strong rho would not pass; ~15-20+ independent serotypes/points are needed.")

    e = expression()
    print(f"\n[relative_expression] N={e['n']} promoters={e['entities']}")
    print(f" {e['note']}")
    print(f" Spearman rho = {e['spearman']} CI = {e['ci']} -> status = {e['status'].upper()}")
    print(" => stays, the palette is now COMPREHENSIVE (31 promoters + 6 modifiers, all literature-cited),")
    print(" but it does NOT outcome-validate: an independent study (Damdindorj 2014) DISAGREES with the")
    print(" anchor (Qin 2010) on CMV/CAG/EF1a ordering. Promoter strength is genuinely CONTEXT-DEPENDENT")
    print(" (cell type × vector × readout), so a single context-free ordinal cannot be validated cross-study.")
    print(" The model's value is that it now ENCODES that context per promoter, not a fake single number.")

    for axis, info in _STRUCTURAL.items():
        if axis == "relative_expression":
            continue
        print(f"\n[{axis}] scores {info['entities_scored']} {info['what']}")
        print(f" would need: {info['outcome_needed']}")
        print(f" => stays, {info['barrier']}")

    print("\n" + "-" * 88)
    print("CONCLUSION: no axis meets the gate with current public data. The labels are accurate. Reaching ")
    print("requires EXPANDING each proxy to >=~15 scored entities AND matching independent measured outcomes, ")
    print("a data-generation effort (the standing real-data-validation bottleneck), not a code change.")


if __name__ == "__main__":
    main()
