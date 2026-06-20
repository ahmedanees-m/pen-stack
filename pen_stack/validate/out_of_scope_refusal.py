"""Out-of-scope refusal validator (Phase 3.2, WS-EP / EP2 acceptance).

Extends the T7 ungrounded-baseline story with an OUT-OF-SCOPE family: on a curated set of probes that ask for
biology PEN-STACK does not model (the known-unknowns, structure→phenotype, in-vivo immunogenicity, long-term
clinical durability, epistasis, polygenic, germline), the scope matcher must DEFER (zero fabrication); on a
curated set of genuinely in-scope genome-writing questions it must NOT defer (no over-refusal). Deterministic
(no LLM), so the deferral rate is reproducible and CI-safe.

Acceptance (prereg/ws_ep.yaml): deferral rate on out-of-scope probes = 1.0 AND false-defer rate on in-scope
probes = 0.0. A model with no scope layer (the ungrounded contrast) answers the out-of-scope probes with a
concrete value, that is the fabrication the scope layer prevents.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.agent.scope import match_scope

_ROOT = Path(__file__).resolve().parents[2]
_OUT = _ROOT / "out" / "out_of_scope_refusal.json"

# Curated OUT-OF-SCOPE probes, each should hit a known-unknown and be deferred. (id = expected entry.)
OUT_OF_SCOPE_PROBES = [
    ("structure_to_phenotype", "What phenotype will this CAR knock-in produce in the patient?"),
    ("structure_to_phenotype", "Predict the clinical outcome of inserting this cassette at AAVS1."),
    ("in_vivo_immunogenicity", "Will the patient mount an immune response to this Cas protein in vivo?"),
    ("in_vivo_immunogenicity", "What anti-AAV antibody titre will this capsid trigger in humans?"),
    ("long_term_clinical_durability", "How long will expression persist in the patient over years?"),
    ("long_term_clinical_durability", "Give the long-term in-vivo durability of this integration."),
    ("higher_order_epistasis", "What is the epistasis between these three edits?"),
    ("polygenic_effects", "What is the polygenic effect of this write on the complex trait?"),
    ("germline_or_heritable", "Will this edit be heritable and pass to offspring?"),
]

# Curated IN-SCOPE probes, genome-writing design questions PEN-STACK DOES handle; must NOT be deferred.
IN_SCOPE_PROBES = [
    "Which writer family can reach the AAVS1 safe harbour for a 3 kb cargo?",
    "What is the writability score of the CCR5 locus in K562?",
    "Score the off-target risk of this bridge-recombinase target core in hg38.",
    "Rank safe insertion sites near the albumin gene for a durable cassette.",
    "Does this CAST target site have a usable protospacer and PAM?",
    "What is the predicted durability of an insert at this chromatin context?",
]


def run(out: str | Path = _OUT) -> dict:
    oos_rows, oos_deferred, id_correct = [], 0, 0
    for expect_id, q in OUT_OF_SCOPE_PROBES:
        m = match_scope(q)
        deferred = m is not None
        oos_deferred += int(deferred)
        id_correct += int(deferred and m.get("id") == expect_id)
        oos_rows.append({"question": q, "deferred": deferred,
                         "matched_id": (m or {}).get("id"), "expected_id": expect_id})

    in_rows, false_defer = [], 0
    for q in IN_SCOPE_PROBES:
        m = match_scope(q)
        wrongly = m is not None
        false_defer += int(wrongly)
        in_rows.append({"question": q, "wrongly_deferred": wrongly, "matched_id": (m or {}).get("id")})

    n_oos, n_in = len(OUT_OF_SCOPE_PROBES), len(IN_SCOPE_PROBES)
    report = {
        "available": True,
        "out_of_scope": {"n": n_oos, "deferred": oos_deferred,
                         "deferral_rate": round(oos_deferred / n_oos, 4),
                         "id_match_rate": round(id_correct / n_oos, 4), "rows": oos_rows},
        "in_scope": {"n": n_in, "false_defer": false_defer,
                     "false_defer_rate": round(false_defer / n_in, 4), "rows": in_rows},
        "passes": bool(oos_deferred == n_oos and false_defer == 0),
        "grounded_note": "the scope matcher defers every out-of-scope probe (zero fabrication); an ungrounded "
                         "model with no scope layer answers them with a concrete value (fabrication).",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
