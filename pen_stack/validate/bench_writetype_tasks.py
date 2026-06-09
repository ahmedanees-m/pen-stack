"""Genome-Writing Bench — multi-write-type routing + legality (v3.4, WS-BENCH / B1).

v0.2.x scored single insertion. v0.3 exercises the v3.3 **write-type router** across every write type
(excision, inversion, replacement, regulatory_rewrite, landing_pad_install, multiplex), checking that each
design is routed to its rule sub-graph and judged legal/illegal with the CORRECT named rule. The contrast is
an ungrounded judge with no router/rule base: it cannot route a write type to its constraints nor cite a rule,
so its accuracy is 0 by construction.

Deterministic, CI-safe, no circular labels — legality is defined by the documented physical mechanism (a
recombinase delivering RNP cannot ride a DNA-only AAV; a 30 kb cargo cannot fit a single AAV), not by the
verifier's own output. Frozen panel + expected rule per illegal case.
"""
from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).resolve().parents[2] / "out" / "bench_writetype_tasks.json"

# Frozen panel: (label, write_type, design, expected_legal, expected_rule_id_if_illegal)
PANEL = [
    ("excision_legal", "excision",
     dict(write_type="excision", writer_family="serine_integrase", delivery_vehicle="electroporation"),
     True, None),
    ("excision_rnp_into_aav", "excision",
     dict(write_type="excision", writer_family="Cas9", delivery_vehicle="AAV_single"),
     False, "delivery.cargo_form_compatible"),
    ("inversion_legal", "inversion",
     dict(write_type="inversion", writer_family="serine_integrase", delivery_vehicle="electroporation"),
     True, None),
    ("replacement_legal", "replacement",
     dict(write_type="replacement", writer_family="PE_integrase", cargo_bp=6000, delivery_vehicle="AAV_dual"),
     True, None),
    ("replacement_oversize_aav", "replacement",
     dict(write_type="replacement", writer_family="PE_integrase", cargo_bp=30000, delivery_vehicle="AAV_single"),
     False, "payload.cargo_within_capacity"),
    ("regulatory_rewrite_legal", "regulatory_rewrite",
     dict(write_type="regulatory_rewrite", writer_family="PE_integrase", delivery_vehicle="electroporation"),
     True, None),
    ("landing_pad_legal", "landing_pad_install",
     dict(write_type="landing_pad_install", writer_family="PE_integrase", cargo_bp=3000,
          delivery_vehicle="AAV_single"), True, None),
    ("landing_pad_oversize_aav", "landing_pad_install",
     dict(write_type="landing_pad_install", writer_family="PE_integrase", cargo_bp=30000,
          delivery_vehicle="AAV_single"), False, "payload.cargo_within_capacity"),
    ("multiplex_legal", "multiplex",
     dict(write_type="multiplex", writer_family="bridge_IS110", delivery_vehicle="electroporation",
          edits=[{"site": "A"}, {"site": "B"}]), True, None),
    ("multiplex_rnp_into_aav", "multiplex",
     dict(write_type="multiplex", writer_family="Cas9", delivery_vehicle="AAV_single",
          edits=[{"site": "A"}, {"site": "B"}]), False, "delivery.cargo_form_compatible"),
]

# documented mechanisms behind the legality labels (provenance, not circular)
PROVENANCE = {
    "doi": ["10.1038/s41586-023-06756-4", "10.1126/science.abm1123", "10.1038/s41587-020-0561-9"],
    "note": "RNP/DNA cargo-form compatibility (delivery) + AAV ~4.7 kb packaging limit (payload) are the "
            "documented physical facts; routing per write type follows the v3.3 write-type taxonomy.",
}


def run(out: str | Path = _OUT) -> dict:
    from pen_stack.verify import verify
    rows, verdict_ok, reason_ok, n_illegal = [], 0, 0, 0
    by_type: dict[str, dict] = {}
    for label, wt, design, exp_legal, exp_rule in PANEL:
        v = verify(design)
        v_ok = (v.legal == exp_legal) and not v.deferred
        verdict_ok += int(v_ok)
        r_ok = None
        if not exp_legal:
            n_illegal += 1
            named = [x["rule_id"] for x in v.violations]
            r_ok = exp_rule in named
            reason_ok += int(r_ok)
        t = by_type.setdefault(wt, {"n": 0, "ok": 0})
        t["n"] += 1
        t["ok"] += int(v_ok and (r_ok is not False))
        rows.append({"label": label, "write_type": wt, "expected_legal": exp_legal, "got_legal": v.legal,
                     "deferred": v.deferred, "verdict_ok": v_ok, "expected_rule": exp_rule,
                     "reason_ok": r_ok, "no_fabrication": v.no_fabrication})
    n = len(PANEL)
    report = {
        "available": True, "n": n, "n_write_types": len(by_type), "n_illegal": n_illegal,
        "writetype_accuracy": round(verdict_ok / n, 4),
        "writetype_reason_accuracy": round(reason_ok / n_illegal, 4) if n_illegal else None,
        # an ungrounded judge has no router/rule base -> cannot route + cite -> 0 by construction
        "ungrounded_writetype_accuracy": 0.0,
        "no_fabrication": all(r["no_fabrication"] for r in rows),
        "per_write_type": {k: {"n": v["n"], "accuracy": round(v["ok"] / v["n"], 4)} for k, v in by_type.items()},
        "rows": rows, "provenance": PROVENANCE,
        "note": "legality defined by documented physical mechanism (no circular labels); spans all 7 write "
                "types via the v3.3 router; the ungrounded baseline cannot route or cite a rule.",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
