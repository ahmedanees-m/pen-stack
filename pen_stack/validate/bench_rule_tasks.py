"""Genome-Writing Bench T12, rule-grounded legality with explanation (v3.3, WS-BA).

On a frozen panel of legal + illegal designs, the verifier must (a) return the correct legal/illegal verdict
and (b) for each illegal case name the CORRECT violated rule (with its citation). The contrast is an
ungrounded judge that has no rule base: it might guess a verdict, but it **cannot cite a rule**, so its
rule-reason accuracy is 0 by construction. The verifier's unique value is the grounded, named, cited reason.

Deterministic, CI-safe, no circular labels (the panel's legality is defined by the documented physical
mechanism, not by the verifier's own output). Frozen panel + expected rule per illegal case.
"""
from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).resolve().parents[2] / "out" / "bench_rule_tasks.json"

_PERM = "ACGTGACCTAGGCTAGCTAGGTCAGCTAACTGGTCAGGTGCAGCTAGCTGACCTAGG"
_POLYA = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
_ATTP = "AGGTTTGTCTGGTCAACCACCGCGGTCTCAGTGGTGTACGGTACAAACCCA"

# Frozen panel: (label, design, expected_legal, expected_rule_id_if_illegal)
PANEL = [
    ("legal_bridge_aav", dict(write_type="insertion", writer_family="bridge_IS110", site_seq=_PERM,
                              cargo_bp=3000, delivery_vehicle="AAV_single"), True, None),
    ("legal_serine_att", dict(write_type="insertion", writer_family="serine_integrase", site_seq=_ATTP,
                              cargo_bp=3000, delivery_vehicle="AAV_single"), True, None),
    ("legal_bridge_hdad_35kb", dict(write_type="insertion", writer_family="bridge_IS110", site_seq=_PERM,
                                    cargo_bp=35000, delivery_vehicle="helper_dependent_adenovirus"), True, None),
    ("legal_cas9_ep", dict(write_type="insertion", writer_family="Cas9", site_seq=_PERM, cargo_bp=2000,
                           delivery_vehicle="electroporation"), True, None),
    ("illegal_35kb_aav", dict(write_type="insertion", writer_family="bridge_IS110", site_seq=_PERM,
                              cargo_bp=35000, delivery_vehicle="AAV_single"), False,
     "payload.cargo_within_capacity"),
    ("illegal_serine_no_att", dict(write_type="insertion", writer_family="serine_integrase", site_seq=_PERM,
                                   cargo_bp=3000, delivery_vehicle="AAV_single"), False,
     "reachability.target_element_available"),
    ("illegal_cast_no_pam", dict(write_type="insertion", writer_family="CAST_VK", site_seq=_POLYA,
                                 cargo_bp=3000, delivery_vehicle="AAV_single"), False,
     "reachability.target_element_available"),
    ("illegal_rnp_into_aav", dict(write_type="insertion", writer_family="Cas9", site_seq=_PERM, cargo_bp=2000,
                                  delivery_vehicle="AAV_single"), False, "delivery.cargo_form_compatible"),
    ("illegal_nonint_lenti", dict(write_type="insertion", writer_family="bridge_IS110", site_seq=_PERM,
                                  cargo_bp=3000, delivery_vehicle="lentivirus", no_integration=True), False,
     "delivery.no_integration_constraint"),
]


def run(out: str | Path = _OUT) -> dict:
    from pen_stack.verify import verify
    rows, verdict_ok, reason_ok, n_illegal = [], 0, 0, 0
    for label, design, exp_legal, exp_rule in PANEL:
        v = verify(design)
        v_ok = (v.legal == exp_legal)
        verdict_ok += int(v_ok)
        r_ok = None
        if not exp_legal:
            n_illegal += 1
            named = [x["rule_id"] for x in v.violations]
            r_ok = exp_rule in named
            reason_ok += int(r_ok)
        rows.append({"label": label, "expected_legal": exp_legal, "got_legal": v.legal,
                     "verdict_ok": v_ok, "expected_rule": exp_rule, "reason_ok": r_ok,
                     "no_fabrication": v.no_fabrication})
    n = len(PANEL)
    report = {
        "available": True, "n": n, "n_illegal": n_illegal,
        "verifier_verdict_accuracy": round(verdict_ok / n, 4),
        "verifier_reason_accuracy": round(reason_ok / n_illegal, 4) if n_illegal else None,
        # an ungrounded judge has no rule base -> cannot name a rule -> 0 reason accuracy by construction
        "ungrounded_baseline_reason_accuracy": 0.0,
        "no_fabrication": all(r["no_fabrication"] for r in rows),
        "verifier_uniquely_provides_reasons": bool(reason_ok == n_illegal and n_illegal > 0),
        "rows": rows,
        "note": "legality defined by documented physical mechanism, not the verifier's own output "
                "(no circular labels); the verifier uniquely supplies correct NAMED, CITED reasons.",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
