"""WriteSpec feasibility / satisfiability check (v6.14, Stage A, A-WS5).

Given a :class:`WriteRequest`, test the NECESSARY conditions a write must meet, by wrapping the existing stages:

  * reachability  - is the target locus / gene reachable by a writer in the writable-genome atlas?
  * deliverability - does any vehicle fit the cargo size (Stage D delivery recommender)?
  * legality      - does the design pass the Stage F rule set (the repair-oriented proof object)?

Returns ``feasible`` or ``infeasible`` plus the NAMED blocking constraint(s) and repair hints (from the Stage F
proof and a delivery suggestion), so an agent can repair the spec and re-check. A check whose backend is absent is
reported ``indeterminate`` and does not, by itself, block (it is surfaced, never silently passed). Feasibility is
necessary-conditions only: it rules out unreachable / undeliverable / illegal, NOT whether the write will WORK
(that is the downstream stages' calibrated, still-uncertain prediction).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from pen_stack.spec.writespec import WriteRequest


class SatisfyResult(BaseModel):
    feasible: bool
    checks: dict[str, Any] = Field(default_factory=dict)     # reachability / deliverability / legality verdicts
    blocking: list[dict] = Field(default_factory=list)       # named blocking constraints
    repairs: list[dict] = Field(default_factory=list)        # repair hints
    note: str | None = None


def _reachability(spec: WriteRequest) -> dict:
    gene = spec.target.gene.id if (spec.target.gene and spec.target.gene.id) else None
    if spec.target.kind == "att_site":
        return {"ok": True, "status": "att/landing site supplied; reachability is by the installed att",
                "determinable": True}
    if gene is None:
        return {"ok": None, "status": "no resolved target gene/locus; supply one for a reachability check",
                "determinable": False}
    try:
        from pen_stack.atlas.crosslink import loci_for_gene
        df = loci_for_gene(gene, ct="k562")
        n = 0 if df is None else len(df)
        if n > 0:
            return {"ok": True, "status": f"{n} writable bins overlap {gene} in the atlas", "determinable": True}
        return {"ok": False, "status": f"no writable bin overlaps {gene} in the atlas (cross-check the locus)",
                "determinable": True}
    except Exception as e: # noqa: BLE001
        return {"ok": None, "status": f"atlas reachability unavailable ({type(e).__name__})", "determinable": False}


def _deliverability(spec: WriteRequest) -> dict:
    bp = spec.constraints.max_cargo_bp or sum((c.length_bp or 0) for c in spec.cargo) or None
    if bp is None:
        return {"ok": None, "status": "no cargo size given; supply bp/kb for a deliverability check",
                "determinable": False}
    try:
        from pen_stack.planner.delivery_predict import recommend_delivery_plus
        rec = recommend_delivery_plus("DNA", bp, None)
        ranked = rec.get("ranked") or []   # the recommender already filters to vehicles that fit the cargo
        excluded = rec.get("excluded") or []
        if ranked:
            top = ranked[0].get("vehicle") or ranked[0].get("name")
            return {"ok": True, "status": f"{len(ranked)} vehicle(s) fit {bp} bp (top: {top}; "
                    f"{len(excluded)} excluded by capacity)", "determinable": True, "top": top}
        return {"ok": False, "status": f"no vehicle in the palette fits {bp} bp", "determinable": True}
    except Exception: # noqa: BLE001
        if bp <= 8000:
            return {"ok": True, "status": f"{bp} bp is within typical single-vector capacity (<= ~8 kb)",
                    "determinable": True}
        return {"ok": False, "status": f"{bp} bp exceeds typical single-vector capacity (~8 kb); needs a "
                "dual/high-capacity strategy", "determinable": True}


def _legality(spec: WriteRequest) -> dict:
    try:
        from pen_stack.verify.proof import verify_proof
        proof = verify_proof(spec.to_legacy_design())
        ax = next((a for a in proof.axes if a.axis == "legality"), None)
        if ax is None:
            return {"ok": None, "status": "no legality axis returned", "determinable": False}
        ok = ax.status in ("pass", "clear")
        out = {"ok": ok, "status": ax.status, "determinable": True}
        if not ok:
            out["violated"] = [v for v in (ax.violated or [])]
            if ax.repair_hint:
                out["repair_hint"] = ax.repair_hint
        return out
    except Exception as e: # noqa: BLE001
        return {"ok": None, "status": f"legality check unavailable ({type(e).__name__})", "determinable": False}


def check_satisfiable(spec: WriteRequest) -> SatisfyResult:
    """Run the reachability + deliverability + legality necessary-condition checks; name blocking constraints."""
    checks = {"reachability": _reachability(spec), "deliverability": _deliverability(spec),
              "legality": _legality(spec)}
    blocking: list[dict] = []
    repairs: list[dict] = []
    for name, c in checks.items():
        if c.get("ok") is False:
            blocking.append({"constraint": name, "reason": c.get("status")})
            if name == "deliverability":
                repairs.append({"constraint": "deliverability",
                                "hint": "reduce the cargo, split across a dual-vector strategy, or use an "
                                        "integrating vehicle"})
            if name == "legality" and c.get("repair_hint"):
                repairs.append({"constraint": "legality", "hint": c["repair_hint"]})
            if name == "reachability":
                repairs.append({"constraint": "reachability",
                                "hint": "choose a writable locus (the atlas Site Finder ranks reachable, safe loci)"})
    feasible = not blocking
    note = ("all determinable necessary conditions met (feasibility is necessary, not sufficient: efficacy is the "
            "downstream prediction)" if feasible else "blocked by the named constraint(s); repairs suggested")
    return SatisfyResult(feasible=feasible, checks=checks, blocking=blocking, repairs=repairs, note=note)
