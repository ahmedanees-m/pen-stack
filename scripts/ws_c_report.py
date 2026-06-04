"""WS-C consolidated report - AlphaGenome sequence features + 3D structural risk.

Reads out/seq_vs_measured_{k562,hepg2}.json (C2) and out/structure3d_sanity.json (C3). Run those validators
first (live once to populate the AlphaGenome cache; offline thereafter).
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_OUT = _ROOT / "out" / "ws_c_report.md"


def _load(name: str) -> dict:
    f = _ROOT / "out" / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def build() -> str:
    lines = [
        "# PEN-STACK v3.1 - AlphaGenome integration (WS-C)",
        "",
        "Hybrid integration: the measured-ENCODE writability atlas stays the backbone; AlphaGenome (hosted "
        "API, no local GPU) supplies on-demand per-locus signals. See `docs/alphagenome_feasibility.md`.",
        "",
        "## C2 - Predicted vs measured tracks",
    ]
    for ct in ("k562", "hepg2"):
        r = _load(f"seq_vs_measured_{ct}.json")
        if not r.get("available"):
            lines.append(f"- {ct.upper()}: pending ({r.get('note', 'not run')}).")
            continue
        pt = r.get("per_track", {})
        sl = r.get("score_level_degradation", {})
        lines += [
            f"### {ct.upper()} (n={r.get('n_sample')}, median per-track Spearman "
            f"{r.get('median_track_spearman')})",
            "- Per-track Spearman: " + ", ".join(f"{k} {v['spearman']}" for k, v in pt.items()) + ".",
            f"- Score-level recovery (predicted vs measured): writability "
            f"{sl.get('writability_spearman')}, safety {sl.get('safety_spearman')}, p_durable "
            f"{sl.get('p_durable_spearman')}.",
            f"- Score-replacement low confidence: **{sl.get('score_replacement_low_confidence')}** - "
            f"{sl.get('interpretation', '')}",
        ]
        if ct == "k562":
            lines.append("- Coverage: AlphaGenome has no H3K9me3 track for K562 (excluded); HepG2 has all 7.")
    s3 = _load("structure3d_sanity.json").get("summary", _load("structure3d_sanity.json"))
    lines += [
        "",
        "## C3 - 3D structural risk (contact-map deltas)",
        f"- Sanity check across {s3.get('n_loci')} known enhancer-hijacking loci: strong-enhancer insert "
        f"raises aberrant oncogene contacts above a matched neutral insert at "
        f"**{s3.get('n_strong_gt_neutral')}/{s3.get('n_loci')}** loci (pass: {s3.get('sanity_pass')}).",
        "- Per-locus strong-minus-neutral aberrant contact gain: "
        + ", ".join(f"{k} {v}" for k, v in (s3.get("per_locus", {}) or {}).items()) + ".",
        "- Gate G-C: ships as a flag with confidence, never a hard pass/fail; heuristic, not a calibrated "
        "probability; contacts are cell-type-specific (GM12878 - K562 has no AlphaGenome Hi-C track).",
        "",
        "## Decision reinforced",
        "Per-track accessibility transfers well, but the composite writability score degrades when rebuilt "
        "from predicted tracks - so the measured-track atlas remains the backbone and AlphaGenome is used "
        "for on-demand track/3D signals and the endogenous-expression baseline (WS-B1).",
    ]
    return "\n".join(lines)


def run(out: str | Path = _OUT) -> Path:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(build(), encoding="utf-8")
    return Path(out)


if __name__ == "__main__":
    print(run().read_text(encoding="utf-8"))
