"""WS-B consolidated report - durability baselines + the safety primary-metric switch.

Emits out/ws_b_report.md from the two artifacts:
  * out/durability_baselines.json  (B1 endogenous-expression baseline, B2 multi-mark ablation)
  * out/gsh_baseline.json          (B3 GSH rule-set baseline; safe-harbour discrimination = PRIMARY safety)

Run pen_stack.validate.durability_baselines and pen_stack.wgenome.gsh_baseline first to refresh the JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DUR = _ROOT / "out" / "durability_baselines.json"
_GSH = _ROOT / "out" / "gsh_baseline.json"
_OUT = _ROOT / "out" / "ws_b_report.md"


def build() -> str:
    dur = json.loads(_DUR.read_text(encoding="utf-8")) if _DUR.exists() else {}
    gsh = json.loads(_GSH.read_text(encoding="utf-8")) if _GSH.exists() else {}
    b2 = dur.get("B2_multimark_ablation", {})
    b1 = dur.get("B1_endogenous_expression_baseline", {})
    sub = b2.get("subsets", {})

    lines = [
        "# PEN-STACK v3.1 - Durability baselines + safety primary-metric switch (WS-B)",
        "",
        "Honest baselines around the durability and safety claims: a same-cell-line endogenous-expression "
        "proxy (B1), a multi-mark ablation that earns the multi-track supervision (B2), and a published "
        "safe-harbour rule-set that the learned safety model must beat on the only non-circular safety "
        "metric - discrimination of validated safe harbours (B3).",
        "",
        "## B3 (PRIMARY SAFETY METRIC) - Safe-harbour discrimination",
        f"- Primary metric: **{gsh.get('primary_safety_metric', 'n/a')}**.",
        f"- **HEADLINE (absolute discrimination, not a delta): learned writability AUROC = "
        f"{gsh.get('auroc_learned_writability')}** (95% CI {gsh.get('auroc_learned_ci95')}, "
        f"N={gsh.get('n_positives')} curated positives vs {gsh.get('n_controls')} matched controls).",
        "- **Why the published distance rule is NOT the headline baseline:** it scores at/below chance "
        f"(curated AUROC {gsh.get('auroc_gsh_ruleset_baseline')}; validated-8 AUROC "
        f"**{gsh.get('auroc_gsh_ruleset_validated_tier')}**, below 0.5) because the functionally validated "
        "harbours are themselves *intragenic* (AAVS1 in PPP1R12C, CCR5, ROSA26-type loci), so a "
        "'far-from-genes' prior actively mis-ranks them. We therefore report the rule's failure as a "
        "**qualitative point**, not as a delta the learned model 'beats' - beating a worse-than-random "
        "baseline would be a low bar and is not claimed.",
        f"- For completeness the learned-minus-rule delta is reported as a **diagnostic only**: "
        f"{gsh.get('delta_DIAGNOSTIC_not_headline')} (95% CI {gsh.get('delta_ci95')}, excludes zero: "
        f"{gsh.get('delta_ci_excludes_zero')}) - it is **not** statistically significant at this N and is "
        "not used as a headline.",
        f"- Honest scope: the absolute CI is wide ({gsh.get('n_positives')} curated positives); a larger "
        "validated GSH set is the route to a precise estimate. The earlier 0.92-on-5 / delta-0.54 figures were "
        "fragile small-sample over-estimates and have been retired.",
        "- `genotoxic_cis` AUROC is **demoted to a diagnostic**: its label is proximity to five oncogenes, "
        "i.e. the distance baseline's own definition (circular); it is not a safety headline.",
        "",
        "## B2 - Multi-mark vs single-mark durability ablation (TRIP, ES-Bruce4)",
        f"- Out-of-fold silenced-AUROC: H3K9me3-only {sub.get('H3K9me3_only', {}).get('silenced_auroc')}, "
        f"H3K27ac-only {sub.get('H3K27ac_only', {}).get('silenced_auroc')}, "
        f"all-marks {sub.get('all_marks', {}).get('silenced_auroc')} "
        f"(n={sub.get('all_marks', {}).get('n')}, chromosome-grouped folds).",
        f"- all-marks >= best single mark: **{b2.get('all_marks_beats_best_single')}** "
        f"({b2.get('all_marks_silenced_auroc')} vs {b2.get('best_single_mark_silenced_auroc')}). "
        "H3K27ac carries most of the signal; the remaining marks add a small but non-negative margin.",
        "- Five histone marks, no ATAC/DNase in the ES-Bruce4 supervision - reported as a five-mark "
        "ablation, not the seven the human atlas uses.",
        "",
        "## B1 - Endogenous-expression baseline (AlphaGenome ES-Bruce4)",
    ]
    if b1.get("available"):
        lines += [
            f"- Same-cell-line proxy ({b1.get('cell_line')}), seeded sample of **{b1.get('n_sample')}** loci.",
            f"- TRIP-trained Spearman **{b1.get('trip_trained_spearman')}** vs endogenous-proxy Spearman "
            f"**{b1.get('endogenous_proxy_spearman')}** (delta {b1.get('delta')}, margin {b1.get('margin')}).",
            f"- TRIP supervision beats the proxy by the pre-registered margin: "
            f"**{b1.get('trip_beats_proxy_by_margin')}**.",
            f"- Interpretation: {b1.get('interpretation')}",
        ]
    else:
        lines += [f"- Pending: {b1.get('note', 'provider unavailable')}"]
    lines += [
        "",
        "## Scope",
        "Retrospective and computational. B1 is a seeded pilot (per-locus 1 Mb prediction over all 11,433 "
        "TRIP sites is API-prohibitive; predictions are cached for offline reproducibility).",
    ]
    return "\n".join(lines)


def run(out: str | Path = _OUT) -> Path:
    md = build()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(md, encoding="utf-8")
    return Path(out)


if __name__ == "__main__":
    print(run().read_text(encoding="utf-8"))
