"""WS-PROTO / WS-INGEST / WS-SIMLAB unit tests (Phase 5.11, the build interface).

CI-safe. Asserts the digital→physical bridge:
  * a cleared, legal design exports a valid protocol DRAFT (>=1 platform) with the v5.6 immune profile in the
    metadata; a safety-REFUSED design and an illegal design both raise ProtocolExportError;
  * ingestion is typed + gated: a result becomes a quarantined measured Candidate, admitted to the curated
    world-model ONLY through the v4.5 gate (no auto-edit); a malformed result raises;
  * the simulated lab returns SIMULATED-labelled results and the loop (export -> sim -> ingest) completes.
"""
from __future__ import annotations

import pytest

from pen_stack.build.ingest import ResultSchemaError, ingest_result
from pen_stack.build.protocol import ProtocolExportError, _to_protocol_ir, export_protocol
from pen_stack.build.simlab import run_simulated

_DESIGN = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
           "cargo_bp": 3000, "cell_type": "k562", "writer_family": "bridge_IS110", "promoter": "ef1a",
           "accessibility": 0.8}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


# --- WS-PROTO --------------------------------------------------------------------------

def test_cleared_design_exports_draft_with_immune_metadata():
    for target in ("opentrons", "pylabrobot", "cloudlab"):
        code = export_protocol(_DESIGN, {"round": 0}, target=target, actor="lab-alice")
        assert "DRAFT" in code and "human/lab review required" in code
        assert "immune_profile" in code # v5.6 profile travels with the protocol


def test_safety_refused_design_blocks_export():
    hazard = {**_DESIGN, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}
    with pytest.raises(ProtocolExportError, match="safety gate"):
        export_protocol(hazard, {}, actor="x")


def test_illegal_design_blocks_export():
    illegal = {**_DESIGN, "cargo_bp": 8000} # oversize for single AAV
    with pytest.raises(ProtocolExportError, match="not legal"):
        export_protocol(illegal, {})


def test_unknown_target_raises():
    with pytest.raises(ProtocolExportError, match="unknown target"):
        export_protocol(_DESIGN, {}, target="magic_robot")


# --- WS-INGEST -------------------------------------------------------------------------

def _result():
    return {"assay": "cassette_expression_readout", "readout": 0.5, "units": "relative",
            "design_id": "design:t", "provenance": {"source": "simlab"}}


def test_ingest_quarantines_result_no_auto_edit():
    cand = ingest_result(_result())
    assert cand.status == "quarantined" and cand.kind == "edge" and cand.evidence == "measured"


def test_ingest_malformed_result_raises():
    with pytest.raises(ResultSchemaError):
        ingest_result({"assay": "x"}) # missing readout / provenance
    with pytest.raises(ResultSchemaError):
        ingest_result({"assay": "x", "readout": 1.0, "provenance": {}}) # provenance without source/doi


def test_admission_only_via_gate():
    from pen_stack.graph.schema import Graph, Node
    g = Graph()
    # the design + outcome nodes already exist in the world-model (an edge needs its endpoints)
    g.add_node(Node(id="design:t", type="design", props={}))
    g.add_node(Node(id="outcome:cassette_expression_readout", type="outcome", props={}))
    # without explicit approval -> still quarantined (no auto-edit), even with a graph + actor
    cand = ingest_result(_result(), admitted_by="human", graph=g, approved=False)
    assert getattr(cand, "status", None) == "quarantined"
    # with approval -> routed through the v4.5 gate; a measured, provenance-bearing edge is admitted
    decision = ingest_result(_result(), admitted_by="human", graph=g, approved=True)
    assert decision["admitted"] is True and decision["admitted_by"] == "human"


# --- WS-SIMLAB -------------------------------------------------------------------------

def test_simlab_round_trip_completes_and_is_labelled():
    ir = _to_protocol_ir(_DESIGN, {"round": 0})
    res = run_simulated(ir, _DESIGN, "k562", seed=1)
    assert res["provenance"]["label"] == "SIMULATED" # never measured truth
    # the loop export -> sim -> ingest completes; the sim result quarantines like any candidate
    code = export_protocol(_DESIGN, {"round": 0}, actor="lab-alice")
    cand = ingest_result(res)
    assert code and cand.status == "quarantined" and cand.evidence == "measured"
