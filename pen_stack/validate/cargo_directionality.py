"""WS-D acceptance - Cargo Polish directionality on a small curated set.

No supervised silencing dataset is claimed. The bar is DIRECTIONALITY: a high-CpG, bacterial-style cassette
(the classic silencing-prone construct) must score above a CpG-depleted / mammalian-optimised cassette and
above an insulator-flanked, CpG-depleted cassette - and every raised flag must carry a concrete suggestion.

The curated sequences are synthetic but representative of their class (documented composition), not tuned to
a threshold. Directionality, not the absolute score, is the claim.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.planner.cargo_polish import scan_cargo

_OUT = Path(__file__).resolve().parents[2] / "out" / "cargo_directionality.json"

# representative constructs (documented composition; deterministic):
# - bacterial high-CpG: dense CG dinucleotides + high GC (bacterial backbone / unmethylated CpG islands)
# - mammalian CpG-depleted: synonymous-codon style, CG avoided, GC ~ 0.5
# - insulated CpG-depleted: the depleted cassette flanked by a (CpG-free) spacer standing in for a UCOE/cHS4
_HIGH_CPG = "GCGCGGCGGCGCGCGGCGGCGCGCGGCGGCGCGCGGCGG" * 12
_DEPLETED = "GACAAGCTGGAAGAACTGAAGGACATCTACAAGGACATC" * 12 # CG-free, GC ~ 0.48
_INSULATED = ("ATAACTTACTATCATCAACTATCATCAACTATCATCAAC" * 4) + _DEPLETED

PANEL = [
    {"name": "bacterial_high_cpg", "klass": "silencing_prone", "seq": _HIGH_CPG},
    {"name": "mammalian_cpg_depleted", "klass": "silencing_resistant", "seq": _DEPLETED},
    {"name": "insulated_cpg_depleted", "klass": "silencing_resistant", "seq": _INSULATED},
]


def run(out: str | Path = _OUT) -> dict:
    scans = {e["name"]: scan_cargo(e["seq"]) for e in PANEL}
    risk = {n: s["cargo_durability_risk"] for n, s in scans.items()}
    # every flag carries a non-empty suggestion
    all_flags_have_suggestions = all(
        bool(f.get("suggestion")) for s in scans.values() for f in s["flags"])
    prone = risk["bacterial_high_cpg"]
    resistant_max = max(risk["mammalian_cpg_depleted"], risk["insulated_cpg_depleted"])
    report = {
        "risk": risk,
        "bands": {n: s["band"] for n, s in scans.items()},
        "directionality_ok": bool(prone > resistant_max),
        "high_cpg_minus_resistant": round(prone - resistant_max, 4),
        "all_flags_have_suggestions": bool(all_flags_have_suggestions),
        "n_flags": {n: s["n_flags"] for n, s in scans.items()},
        "scope": "directionality on a small curated set; heuristic flag, not a supervised predictor",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps({**report, "scans": scans}, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
