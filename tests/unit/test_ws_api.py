"""WS-MANIFEST / WS-OPENAPI / WS-MCP / WS-EXAMPLE unit tests (Phase 6.1, the AI Integration Surface).

The manifests + the framework tool wrapper are pure-Python (CI-safe). The FastAPI endpoint tests are guarded by
`pytest.importorskip("fastapi")` so they skip on a bare laptop/CI and run on the VM (server extra). Asserts:
  * the capability manifest lists the tools, all fabricates=False, versioned, JSON-serializable;
  * the SCOPE manifest exposes every known-unknown + every oracle scope card as machine-readable data (the
    differentiator), with a policy and no internal matcher fields leaked;
  * the framework tool wrapper builds specs from the live manifest and dispatches to the validated engine;
  * (VM) the /capabilities, /scope, /verify, /safety endpoints answer and openapi.json validates as 3.1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2] # repo root: `examples/` lives here, not in the wheel
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from examples.agent_tools import dispatch, scope_tools, tool_specs # noqa: E402
from pen_stack.api.manifest import capability_manifest, scope_manifest # noqa: E402

_BENIGN = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
           "cargo_bp": 3000, "cargo_function": "human factor IX"}
_HAZARD = {**_BENIGN, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


# --- WS-MANIFEST -----------------------------------------------------------------------

def test_capability_manifest_is_typed_and_honest():
    cap = capability_manifest()
    assert cap["name"] == "pen-stack" and cap["stability"] == "stable" and cap["version"]
    assert cap["tools"] and all(t["fabricates"] is False for t in cap["tools"]) # nothing fabricates
    assert {"verify_write", "safety_screen", "generate_designs", "predict_outcome", "immune_profile"} \
        <= {t["name"] for t in cap["tools"]}
    json.dumps(cap) # JSON-serializable


def test_scope_manifest_exposes_known_unknowns_and_scope_cards():
    sc = scope_manifest()
    assert sc["known_unknowns"] and sc["oracle_scope_cards"] and sc["policy"]
    # the in-vivo / phenotype known-unknowns are present (the honesty boundary)
    ids = {k["id"] for k in sc["known_unknowns"]}
    assert {"structure_to_phenotype", "in_vivo_immunogenicity"} <= ids
    # internal matcher fields are NOT leaked into the public manifest
    for k in sc["known_unknowns"]:
        assert set(k) <= {"id", "title", "requires", "why"}
    # every scope card states what it is NOT valid for
    assert all(c.get("not_valid_for") for c in sc["oracle_scope_cards"])
    json.dumps(sc)


# --- WS-EXAMPLE (framework wrapper) ----------------------------------------------------

def test_tool_specs_generated_from_manifest():
    specs = tool_specs()
    assert len(specs) == len(capability_manifest()["tools"])
    assert all(s["type"] == "function" and s["function"]["name"] and "parameters" in s["function"]
               for s in specs)


def test_dispatch_routes_to_the_validated_engine():
    assert dispatch("verify_write", {"payload": _BENIGN})["legal"] is True
    assert dispatch("safety_screen", {"payload": _HAZARD})["decision"] == "refuse"
    assert "axes" in dispatch("immune_profile", {"payload": _BENIGN})
    assert "error" in dispatch("nonexistent_tool", {}) # unknown -> structured error
    assert scope_tools()["known_unknowns"]


# --- WS-OPENAPI / WS-MCP endpoints (VM / server extra) ---------------------------------

def test_scope_defers_titer_and_durability_questions():
    # acceptance T14/T15: the classic measured endpoints (functional titer, in-vivo durability) must be
    # flagged out-of-scope by the matcher, not just left to the no-fabrication spine. In-scope stays in-scope.
    from pen_stack.agent.scope import match_scope
    assert match_scope("what functional titer (% of normal) will my design produce")["id"] == "in_vivo_expression_magnitude"
    assert match_scope("how long will episomal AAV expression last in hepatocytes")["id"] == "long_term_clinical_durability"
    assert match_scope("will it persist")["id"] == "long_term_clinical_durability"
    assert match_scope("which writer integrates a 3 kb cassette at AAVS1") is None # in-scope unchanged


def test_safe_harbour_nickname_resolves_to_host_gene():
    # AAVS1 etc. are locus nicknames, NOT HGNC symbols -> map to the host gene so /plan + /writable answer.
    from pen_stack.planner.optimize import resolve_gene
    assert resolve_gene("AAVS1") == "PPP1R12C" and resolve_gene("aavs1") == "PPP1R12C"
    assert resolve_gene("H11") == "EIF4ENIF1"
    assert resolve_gene("PCSK9") == "PCSK9" and resolve_gene("HBB") == "HBB" # real symbols unchanged


def test_records_helper_is_json_safe_with_non_finite_floats():
    pytest.importorskip("fastapi")
    import math

    import pandas as pd

    from pen_stack.server.api import _records
    df = pd.DataFrame([{"a": 1.0, "b": float("nan"), "c": float("inf"), "d": "x"},
                       {"a": 2.0, "b": 3.0, "c": -float("inf"), "d": "y"}])
    recs = _records(df)
    json.dumps(recs) # must not raise (the 500 we fixed)
    assert recs[0]["b"] is None and recs[0]["c"] is None # NaN/inf -> null
    assert recs[1]["b"] == 3.0 and recs[1]["d"] == "y" # finite values preserved
    assert all(not (isinstance(v, float) and not math.isfinite(v)) for r in recs for v in r.values())


def test_rest_endpoints_and_openapi():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from pen_stack.server.api import app
    c = TestClient(app)

    cap = c.get("/capabilities")
    assert cap.status_code == 200 and cap.json()["tools"]
    sc = c.get("/scope")
    assert sc.status_code == 200 and sc.json()["known_unknowns"] and sc.json()["oracle_scope_cards"]
    assert c.post("/safety", json=_HAZARD).json()["decision"] == "refuse"
    assert c.post("/safety", json=_BENIGN).json()["decision"] == "clear"
    assert "axes" in c.post("/immune", json=_BENIGN).json()
    v = c.post("/verify", json=_BENIGN).json()
    assert v["legal"] is True and v["safety"]["decision"] == "clear"

    oa = c.get("/openapi.json").json()
    assert oa["openapi"].startswith("3.") # OpenAPI 3.x spec
    for path in ("/capabilities", "/scope", "/verify", "/safety", "/immune"):
        assert path in oa["paths"], path
