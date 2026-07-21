"""Typed, gated result-ingestion API, the digital→physical bridge.

An experimental result enters PEN-STACK as CANDIDATE evidence, never auto-merged: it is turned into a measured
edge Candidate and quarantined. The ONLY path into the curated world-model is the gate (`gate_admit`) with
automated checks AND explicit human approval, inheriting Principle 1 (no process auto-edits the world-model).
Immune-measurement results can begin validating the proxies on a later pass.
"""
from __future__ import annotations

from typing import Any

from pen_stack.graph.ingest import Candidate, gate_admit


class ResultSchemaError(ValueError):
    """Raised when an ingested result is missing required fields (assay / readout / provenance)."""


def _validate_result_schema(result: dict) -> dict:
    for k in ("assay", "readout", "provenance"):
        if result.get(k) is None:
            raise ResultSchemaError(f"result missing required field {k!r}")
    prov = result["provenance"]
    if not (prov.get("source") or prov.get("doi") or prov.get("europepmc")):
        raise ResultSchemaError("result provenance must carry source / doi / europepmc id")
    return result


def _as_candidate(result: dict) -> Candidate:
    """A measured outcome -> a quarantined measured EDGE candidate (design --measured_outcome--> outcome)."""
    src = result.get("design_id", "design:anon")
    payload = {"src": src, "dst": f"outcome:{result['assay']}", "etype": "measured_outcome",
               "confidence": result.get("confidence"), "scope": result.get("scope"),
               "readout": result["readout"], "units": result.get("units")}
    return Candidate(kind="edge", payload=payload, provenance=result["provenance"], evidence="measured",
                     note="ingested experimental result (quarantined; admit only via the gate)")


def ingest_result(result: dict, *, admitted_by: str | None = None, graph: Any = None,
                  approved: bool = False) -> Any:
    """Validate + quarantine an experimental result as a measured Candidate. With `admitted_by` + a `graph` +
    explicit `approved=True`, route it through the gate (the ONLY path into the curated world-model);
    otherwise return the quarantined Candidate (never auto-merged)."""
    cand = _as_candidate(_validate_result_schema(result))
    if admitted_by is not None and graph is not None and approved:
        return gate_admit(graph, cand, approved=True, admitted_by=admitted_by)
    return cand # quarantined; no auto-edit of curated truth
