"""Target-site filter positive/negative controls (Phase 3.2, WS-MC / MC1 acceptance).

Pre-registered acceptance (prereg/ws_mc.yaml):
  * POSITIVE control, a site that carries the writer's required targeting element is AVAILABLE (the writer
    can engage it). Documented writes carry their element by construction (a Cas9 edit has an NGG PAM; a CAST
    insertion has a GTN PAM; a bridge target has the central CT core; a serine integrase write happens at an
    installed attB landing pad).
  * NEGATIVE control, a motif-absent site correctly REJECTS the writer (no PAM → no Cas/CAST; no att → no
    serine integrase; no core → no bridge). This is the hard mechanistic reject the funnel adds.

Sequence-computable and deterministic (no genome needed), so it runs in CI. The sequences are illustrative
motif-bearing vs motif-absent constructs that exercise each family's requirement.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.planner.target_site import target_site_available

_OUT = Path(__file__).resolve().parents[2] / "out" / "target_site_controls.json"

# Bxb1 attP landing pad (carries the att core), the documented serine-integrase target.
_ATTB = "AGGTTTGTCTGGTCAACCACCGCGGTCTCAGTGGTGTACGGTACAAACCCA"
# A site engineered with a CAST GTN PAM + a bridge CT core + a Cas9 NGG PAM (a permissive multi-writer window).
_PERMISSIVE = "ACGTGACCTAGGCTAGCTAGGTCAGCTAACTGGTCAGGTGCAGCTAGCTGACCTAGG"
# Motif-absent windows: a pure poly-A/T stretch (no NGG, no GTN PAM, no CT core, no att).
_POLYA = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def run(out: str | Path = _OUT) -> dict:
    cases = [
        # (label, family, seq, installed_att, expect_available)
        ("pos_cas9_pam", "Cas9", _PERMISSIVE, False, True),
        ("pos_cast_pam", "CAST_VK", _PERMISSIVE, False, True),
        ("pos_bridge_core", "bridge_IS110", _PERMISSIVE, False, True),
        ("pos_serine_installed_att", "serine_integrase", _ATTB, False, True),
        ("pos_pe_installable", "PE_integrase", _POLYA, False, True), # PE installs its own att anywhere
        ("neg_cast_no_pam", "CAST_VK", _POLYA, False, False),
        ("neg_serine_no_att", "serine_integrase", _PERMISSIVE, False, False),
        ("neg_bridge_no_core", "bridge_IS110", _POLYA, False, False),
        ("neg_cas12a_no_pam", "Cas12a", "GCGCGCGCGCGCGCGCGCGCGCGCGCGC", False, False),
    ]
    rows, n_correct = [], 0
    for label, fam, seq, att, expect in cases:
        v = target_site_available(fam, seq, installed_att=att)
        correct = bool(v["available"]) == expect
        n_correct += int(correct)
        rows.append({"label": label, "family": fam, "expect_available": expect,
                     "available": v["available"], "correct": correct, "reason": v["reason"]})
    pos = [r for r in rows if r["label"].startswith("pos_")]
    neg = [r for r in rows if r["label"].startswith("neg_")]
    report = {"available": True, "n": len(rows), "n_correct": n_correct,
              "positive_controls_pass": all(r["correct"] for r in pos),
              "negative_controls_pass": all(r["correct"] for r in neg),
              "passes": n_correct == len(rows), "rows": rows,
              "scope": "sequence-computable mechanistic screen (not an activity guarantee); the hard result is "
                       "the negative, a physically impossible writer-site pairing is rejected."}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
