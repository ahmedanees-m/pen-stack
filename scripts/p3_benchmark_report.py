"""WS-A6 - consolidated de-circularized benchmark report.

Emits out/ws_a_report.md with: the blind GSH discovery (A3, the HEADLINE), writer-family recovery (A4),
within-locus ranking (A5), and the intent specification-compliance table (A2). Each section carries its
scope statement. The targeted-intent gene-level recovery is NOT reported as predictive (see
docs/benchmark_circularity.md).
"""
from __future__ import annotations

from pathlib import Path

from pen_stack.validate import (
    blind_gsh_discovery,
    intent_specification,
    within_locus_ranking,
    writer_recovery,
)

_OUT = Path(__file__).resolve().parents[1] / "out" / "ws_a_report.md"


def build() -> str:
    a3 = blind_gsh_discovery.run()
    a4 = writer_recovery.run()
    a5 = within_locus_ranking.run()
    a2 = intent_specification.run()

    lines = [
        "# PEN-STACK v3.1 - De-circularized planning benchmark (WS-A)",
        "",
        "The headline is the **blind safe-harbour site discovery** (a search, not a confirmation). The "
        "former targeted-intent recovery@k is a definitional artifact and is reported only as a "
        "specification-compliance property (see `docs/benchmark_circularity.md`).",
        "",
        "## A3 (HEADLINE) - Blind safe-harbour site discovery",
        f"- Held-out GSH: **{a3['n_positives']}** loci ({a3['n_validated']} validated + "
        f"{a3['n_candidate']} candidate) vs **{a3['n_controls']}** matched controls "
        f"(controls SHA `{a3['controls_sha256'][:12]}`, frozen before scoring).",
        f"- **{a3['headline']}**",
        f"- Acceptance: all-loci CI excludes chance = "
        f"{a3['acceptance']['all_loci_ci_excludes_chance']}; writability beats safety baseline = "
        f"{a3['acceptance']['writability_beats_safety_AUROC']}; validated tier underpowered = "
        f"{a3['acceptance']['validated_tier_underpowered']}.",
        f"- Honest finding: {a3['honest_finding']}",
        f"- Scope: {a3['scope']}",
        "",
        "## A4 - Diversified writer-family recovery",
        f"- recovery@1 = **{a4['recovery_at_1']}** vs prevalence baseline {a4['prevalence_baseline_at_1']} "
        f"on {a4['n_entries']} entries across {a4['n_families']} families "
        f"(beats prevalence: {a4['beats_prevalence']}).",
        f"- Per family: {a4['per_family']}",
        f"- Scope: {a4['scope']}",
        "",
        "## A5 - Within-locus ranking (descriptive)",
        f"- {a5['n_top_quartile']}/{a5['n_loci']} documented bins in the top quartile of their locus "
        f"(fraction {a5['fraction_top_quartile']}).",
        *[f" - {p['name']} ({p['gene']}): percentile {p['within_locus_percentile']}, "
          f"top_quartile={p['top_quartile']}" for p in a5["per_locus"]],
        f"- Scope: {a5['scope']}",
        "",
        "## A2 - Intent specification-compliance (NOT predictive)",
        f"- {a2['n_correct']}/{a2['n_cases']} cases specification-correct (same locus ranks high under a "
        "targeted intent, low under safe-harbour).",
        f"- Scope: {a2['scope']}",
        "",
        "## Scope of the whole benchmark",
        "Computational and retrospective. It measures grounded planning quality and site/writer/off-target "
        "discrimination on a small, survivorship-biased set of documented writes - not clinical outcome.",
    ]
    return "\n".join(lines)


def run(out: str | Path = _OUT) -> Path:
    md = build()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(md, encoding="utf-8")
    return Path(out)


if __name__ == "__main__":
    p = run()
    print(p.read_text(encoding="utf-8"))
