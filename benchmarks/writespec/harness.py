"""WriteSpec-Bench (v6.14 Stage A, A-WS4): score the grounded extractor against the gold corpus.

SO-Bench-style decomposition, reported VERBATIM (including failures), never tuned to the sealed test:
  * schema adherence   - the output validates as a typed WriteRequest;
  * structural fidelity - write_type + target_kind match the gold;
  * value accuracy     - canonical id match for gene / phenotype / cell + the cargo role set + key constraints;
  * grounding          - on the ambiguity subset: clarifying questions fire, the inferred write_type is labelled,
                          and inferred-field labelling recall is 100% (no field is set without provenance).
The baseline is the legacy keyword dict (``web.tools.parse_goal``), which emits raw tokens, not canonical ids;
the extractor beats it precisely because it resolves to verified ontology ids.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent


def _corpus() -> dict:
    return json.loads((_HERE / "corpus.json").read_text(encoding="utf-8"))


def _extracted_fields(spec) -> dict:
    return {
        "write_type": spec.write_type,
        "target_kind": spec.target.kind,
        "gene": spec.target.gene.id if (spec.target.gene and spec.target.gene.id) else None,
        "phenotype": spec.target.phenotype.id if (spec.target.phenotype and spec.target.phenotype.id) else None,
        "cell": spec.cell_type.id if (spec.cell_type and spec.cell_type.id) else None,
        "cargo_roles": sorted(c.role.id for c in spec.cargo if c.role and c.role.id),
        "constraints": {k: v for k, v in spec.constraints.model_dump().items()
                        if v is not None and k != "inducer"} | (
            {"inducer": spec.constraints.inducer.id} if spec.constraints.inducer and spec.constraints.inducer.id else {}),
    }


def _value_score(got: dict, gold: dict) -> tuple[int, int]:
    """Matched fields / scored fields over gene, phenotype, cell, cargo_roles, and the listed gold constraints."""
    matched = scored = 0
    for f in ("gene", "phenotype", "cell"):
        scored += 1
        if got.get(f) == gold.get(f):
            matched += 1
    scored += 1
    if sorted(got.get("cargo_roles", [])) == sorted(gold.get("cargo_roles", [])):
        matched += 1
    gold_cons = gold.get("constraints", {})
    for k, v in gold_cons.items():
        scored += 1
        if got.get("constraints", {}).get(k) == v:
            matched += 1
    return matched, scored


def _baseline_fields(prose: str) -> dict:
    from pen_stack.web.tools import parse_goal
    d = parse_goal(prose)
    return {"gene": d.get("gene"), "cell": d.get("cell_type"), "cargo_roles": [], "phenotype": None,
            "constraints": ({"max_cargo_bp": d.get("cargo_bp")} if d.get("cargo_bp") else {})}


def run() -> dict[str, Any]:
    from pen_stack.spec.clarify import clarifying_questions
    from pen_stack.spec.extract import extract_writespec
    corpus = _corpus()
    pairs = corpus["pairs"]
    rows = []
    for p in pairs:
        spec = extract_writespec(p["prose"])
        got = _extracted_fields(spec)
        gm, gs = _value_score(got, p["gold"])
        bm, bs = _value_score(_baseline_fields(p["prose"]), p["gold"])
        struct = (got["write_type"] == p["gold"]["write_type"]) and (got["target_kind"] == p["gold"]["target_kind"])
        # grounding: every set field is in provenance; any field that is inferred is in assumptions
        set_fields = {"write_type"} | ({"target.gene"} if got["gene"] else set()) \
            | ({"target.phenotype"} if got["phenotype"] else set()) | ({"cell_type"} if got["cell"] else set())
        labelled = all(f in spec.provenance for f in set_fields)
        # inferred-field labelling: a field whose provenance is "inferred" must appear in an assumption line
        inferred_fields = [f for f, k in spec.provenance.items() if k == "inferred"]
        inferred_labelled = all(any(f.split(".")[-1] in a or f in a for a in spec.assumptions) for f in inferred_fields)
        rows.append({
            "id": p["id"], "split": p["split"], "subset": p["subset"],
            "schema_ok": isinstance(spec.write_type, str),
            "structural_ok": struct,
            "value_matched": gm, "value_scored": gs,
            "baseline_matched": bm, "baseline_scored": bs,
            "clarifies": bool(clarifying_questions(spec)),
            "expect_clarification": bool(p["gold"].get("expect_clarification")),
            "expect_inferred_write_type": bool(p["gold"].get("expect_inferred_write_type")),
            "write_type_inferred": spec.provenance.get("write_type") == "inferred",
            "fields_labelled": labelled, "inferred_labelled": inferred_labelled,
        })

    def _agg(subset_rows):
        n = len(subset_rows)
        if n == 0:
            return {}
        vs = sum(r["value_scored"] for r in subset_rows)
        bs = sum(r["baseline_scored"] for r in subset_rows)
        return {
            "n": n,
            "schema_adherence": round(sum(r["schema_ok"] for r in subset_rows) / n, 4),
            "structural_fidelity": round(sum(r["structural_ok"] for r in subset_rows) / n, 4),
            "value_accuracy": round(sum(r["value_matched"] for r in subset_rows) / vs, 4) if vs else None,
            "baseline_value_accuracy": round(sum(r["baseline_matched"] for r in subset_rows) / bs, 4) if bs else None,
        }

    test_rows = [r for r in rows if r["split"] == "test"]
    train_rows = [r for r in rows if r["split"] == "train"]
    amb_rows = [r for r in rows if r["subset"] == "ambiguity"]
    test = _agg(test_rows)
    train = _agg(train_rows)
    # grounding gates
    clar_fire = all(r["clarifies"] for r in amb_rows if r["expect_clarification"])
    inferred_wt = all(r["write_type_inferred"] for r in amb_rows if r["expect_inferred_write_type"])
    labelling_recall = round(sum(r["inferred_labelled"] and r["fields_labelled"] for r in rows) / len(rows), 4)
    beats_baseline = (test.get("value_accuracy") or 0) > (test.get("baseline_value_accuracy") or 0)

    gate_pass = bool(
        test.get("structural_fidelity", 0) >= 0.8
        and beats_baseline
        and labelling_recall == 1.0
        and clar_fire and inferred_wt
    )
    return {
        "bench": "WriteSpec-Bench (Stage A)",
        "n_pairs": len(pairs),
        "test_sealed": test,
        "train": train,
        "beats_baseline_on_test": beats_baseline,
        "ambiguity": {"n": len(amb_rows), "clarifying_questions_fire": clar_fire,
                      "inferred_write_type_labelled": inferred_wt},
        "inferred_field_labelling_recall": labelling_recall,
        "all_gates_pass": gate_pass,
        "rows": rows,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, default=str))
