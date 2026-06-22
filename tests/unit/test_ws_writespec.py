"""WS-WRITESPEC (v6.14 Stage A) unit tests: the typed WriteRequest, grounded resolvers + extractor,
feasibility check, and the WriteSpec-Bench gates."""
from __future__ import annotations

import pytest

from pen_stack.spec import CargoComponent, Resolved, Target, WriteRequest
from pen_stack.spec.extract import extract_writespec
from pen_stack.spec.resolvers import (
    resolve_cell,
    resolve_chem,
    resolve_feature,
    resolve_gene,
    resolve_locus,
    resolve_phenotype,
)
from pen_stack.spec.satisfy import check_satisfiable
from pen_stack.spec.service import parse_request


def _example() -> WriteRequest:
    return WriteRequest(
        write_type="insertion",
        cargo=[CargoComponent(name="GFP", role=Resolved(text="CDS", id="SO:0000316", ontology="SO"),
                              sequence="ATGGTGAGC", length_bp=720)],
        target=Target(kind="gene", gene=Resolved(text="AAVS1", id="PPP1R12C", ontology="HGNC")),
        cell_type=Resolved(text="HEK293T", id="CVCL_0063", ontology="Cellosaurus"),
    )


def test_json_round_trip_lossless():
    wr = _example()
    assert WriteRequest.from_json(wr.to_json()) == wr


def test_ontology_validation_flags_bad_ids():
    wr = _example()
    assert wr.ontology_validation()["all_valid"] is True
    wr.cell_type = Resolved(text="x", id="not-a-cvcl", ontology="Cellosaurus")
    v = wr.ontology_validation()
    assert v["all_valid"] is False and any(b["field"] == "cell_type" for b in v["invalid"])


def test_legacy_design_adapter():
    d = _example().to_legacy_design()
    assert d["write_type"] == "insertion" and d["gene"] == "PPP1R12C" and d["cell_type"] == "CVCL_0063"


def test_genbank_export_only_with_sequence():
    assert "LOCUS" in (_example().to_genbank() or "")
    intent_only = WriteRequest(write_type="excision", target=Target(kind="gene", gene=Resolved(id="CCR5", ontology="HGNC")))
    assert intent_only.to_genbank() is None


def test_sbol3_round_trip_when_installed():
    sbol3 = pytest.importorskip("sbol3")  # the [spec] extra
    assert sbol3 is not None
    wr = _example()
    assert WriteRequest.from_sbol3(wr.to_sbol3()) == wr


def test_resolvers_ground_or_abstain():
    assert resolve_gene("AAVS1").id == "PPP1R12C"
    assert resolve_gene("the").id is None          # jargon / stop token: unresolved, not invented
    assert resolve_cell("HEK293T").id == "CVCL_0063"
    assert resolve_cell("zog cells").id is None
    assert resolve_feature("promoter").id == "SO:0000167"
    assert resolve_phenotype("sickle cell").id == "MONDO:0011382"
    assert resolve_chem("doxycycline").id == "CHEBI:50845"
    assert resolve_locus("CFTR").id.startswith("chr7:")


def test_extractor_labels_inferred_and_never_fabricates():
    s = extract_writespec("I want to edit some cells")
    assert s.provenance["write_type"] == "inferred"           # the only defaulted field, labelled
    assert s.assumptions                                       # with a rationale
    assert s.target.kind == "unspecified" and s.clarifications  # asks rather than guesses
    # a fully specified request resolves with no clarification and no unresolved term
    s2 = extract_writespec("Knock out CCR5 in primary T cells")
    assert s2.write_type == "excision" and s2.target.gene.id == "CCR5"
    assert s2.cell_type.id == "CL:0000084" and not s2.clarifications and not s2.unresolved


def test_satisfiability_feasible_and_infeasible():
    feasible = check_satisfiable(extract_writespec("Insert a 3 kb cassette at AAVS1 in HEK293T"))
    assert feasible.feasible is True
    infeasible = check_satisfiable(extract_writespec("Insert an 8 kb cassette at AAVS1 in HEK293T using a single AAV"))
    assert infeasible.feasible is False
    assert any(b["constraint"] == "legality" for b in infeasible.blocking)
    assert infeasible.repairs  # a repair hint is offered


def test_parse_request_service():
    out = parse_request("Knock out CCR5 in primary T cells")
    assert out["actionable"] is True and out["no_fabrication"] is True
    assert out["writespec"]["target"]["gene"]["id"] == "CCR5"
    assert out["feasibility"]["feasible"] in (True, False)


def test_writespec_bench_gates_pass():
    from benchmarks.writespec.harness import run
    r = run()
    assert r["all_gates_pass"] is True
    assert r["test_sealed"]["structural_fidelity"] >= 0.8
    assert r["beats_baseline_on_test"] is True
    assert r["inferred_field_labelling_recall"] == 1.0
