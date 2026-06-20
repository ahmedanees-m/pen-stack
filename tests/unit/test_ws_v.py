"""WS-V unit tests (v3.3), the verification service. Pure-logic + REST round-trip (skips if FastAPI absent)."""
from __future__ import annotations

from pen_stack.verify import Verdict, verify

_PERM = "ACGTGACCTAGGCTAGCTAGGTCAGCTAACTGGTCAGGTGCAGCTAGCTGACCTAGG"


def _legal_design(**kw):
    d = {"write_type": "insertion", "writer_family": "bridge_IS110", "site_seq": _PERM,
         "cargo_bp": 3000, "delivery_vehicle": "AAV_single"}
    d.update(kw)
    return d


def test_verdict_carries_all_axes():
    v = verify(_legal_design(safety=0.9, p_durable=0.85, writer_activity=0.8))
    assert isinstance(v, Verdict)
    assert v.legal is True
    assert v.confidence is not None and v.interval is not None
    assert v.epistemic_status and v.no_fabrication
    assert "rules_version" in v.provenance


def test_illegal_named_with_reason_and_citation():
    v = verify(_legal_design(cargo_bp=35000))
    assert v.legal is False
    ids = [x["rule_id"] for x in v.violations]
    assert "payload.cargo_within_capacity" in ids
    assert all("reason" in x for x in v.violations)
    assert any(x["citation"] for x in v.violations) # hard rejects carry a DOI


def test_legality_and_confidence_are_distinct_axes():
    # legal but NO confidence (no axis scores provided) -> legal True, confidence None (abstain)
    v = verify(_legal_design())
    assert v.legal is True and v.confidence is None
    # illegal but we are CERTAIN of illegality (grounded) -> legality False, still no confidence collapse
    v2 = verify(_legal_design(cargo_bp=35000, safety=0.9, p_durable=0.85, writer_activity=0.8))
    assert v2.legal is False
    # the two axes are separate fields, never merged
    assert hasattr(v2, "legal") and hasattr(v2, "confidence")


def test_deferred_write_type():
    v = verify({"write_type": "teleport"})
    assert v.deferred and v.legal is None and v.epistemic_status == "not-computable"


def test_out_of_scope_question_flagged():
    v = verify(_legal_design(), question="what phenotype will this produce in the patient?")
    assert v.epistemic_status == "not-computable"
    assert any(s.get("kind") == "known_unknown" for s in v.scope_flags)


def test_no_fabrication_on_verifier():
    # every verdict's numbers come from tools (rule values, calibrated confidence); none are free-generated
    for d in [_legal_design(), _legal_design(cargo_bp=35000), {"write_type": "teleport"}]:
        assert verify(d).no_fabrication


def test_rest_verify_roundtrip():
    import pytest
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from pen_stack.server.api import app
    c = TestClient(app)
    r = c.post("/verify", json=_legal_design(cargo_bp=35000))
    assert r.status_code == 200
    body = r.json()
    assert body["legal"] is False
    assert "payload.cargo_within_capacity" in [v["rule_id"] for v in body["violations"]]


def test_mcp_tool_registered():
    import pytest
    pytest.importorskip("fastmcp")
    import pen_stack.agent.mcp_server as m
    assert hasattr(m, "verify_write")
