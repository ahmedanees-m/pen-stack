"""Repair-oriented proof object for verify().

``verify(design)`` already returns legality, a calibrated confidence and a biosecurity verdict as separate
fields. ``verify_proof(design)`` repackages that into a machine-readable proof an agent can repair a design
from: three SEPARATELY-REPORTED axes (legality, confidence, biosecurity), each carrying a status, the rule or
signature that fired, the supporting evidence, and a repair hint. The single collapsed verdict is always
``None`` (the axes are never fused), per the verification-service invariant.

Repair hints are actionable for legality (a structured field edit that an agent, or ``repair_from_proof``, can
apply and re-verify) and for the confidence abstention (which scores to supply). Biosecurity repair hints are
deliberately NON-ACTIONABLE for a hazard: a refused or escalated design is acknowledged and routed to human
biosafety review, never auto-repaired and never given instructions toward the hazard. Generation may be
intractable; verification, and repairing a failed-on-legality design, is tractable, which is the point.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from pen_stack.planner.delivery_vehicles import names as _vehicle_names
from pen_stack.planner.delivery_vehicles import vehicle as _vehicle
from pen_stack.rules import Design
from pen_stack.verify.schema import Verdict
from pen_stack.verify.service import verify

AXES = ("legality", "confidence", "biosecurity")


def _freeze(v: Any) -> Any:
    """Recursively replace mappings with read-only views and sequences with tuples.

    ``frozen`` blocks attribute assignment but not mutation of a mutable field value, so a proof
    carrying plain dicts and lists would stay writable through its own fields: a caller handed a
    failed proof could clear ``violated``, rewrite ``evidence``, or edit the repair hint in place.
    Applied to the nested containers for the same reason ``Provenance.extra`` is deep-frozen."""
    if isinstance(v, Mapping):
        return MappingProxyType({k: _freeze(x) for k, x in v.items()})
    if isinstance(v, (list, tuple)):
        return tuple(_freeze(x) for x in v)
    return v


def _thaw(v: Any) -> Any:
    """Plain JSON types for the serialisers: a mappingproxy is not JSON-serialisable and the proof
    crosses the REST and MCP boundaries."""
    if isinstance(v, Mapping):
        return {k: _thaw(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_thaw(x) for x in v]
    return v


class AxisProof(BaseModel):
    """Immutable (frozen): one axis verdict as the verifier computed it.

    Frozen so an agent step or a downstream transform cannot turn a failing axis into a passing one,
    drop the rule that fired, or edit the repair hint on a proof it was handed."""
    model_config = ConfigDict(frozen=True)

    axis: str # one of AXES
    status: str # pass | fail | abstain | refuse | escalate | flag | deferred
    ok: bool # True when this axis does not block (pass/flag/clear; abstain is ok-but-uncertain for confidence)
    violated: Sequence[Mapping[str, Any]] = Field(default_factory=tuple) # the rule(s)/signature(s) that fired
    evidence: Mapping[str, Any] = Field(default_factory=dict)
    repair_hint: Mapping[str, Any] | None = None # {text, repair?: {field, set_to}} | None

    @field_validator("violated", "evidence", "repair_hint")
    @classmethod
    def _deep_freeze(cls, v: Any) -> Any:
        return _freeze(v)

    @field_serializer("violated", "evidence", "repair_hint")
    def _ser(self, v: Any) -> Any:
        return _thaw(v)


class Proof(BaseModel):
    """Immutable (frozen): the per-axis proof object as returned.

    The same guarantee the oracle result type carries, extended to the verification surface: once
    ``verify_proof`` has returned, ``passable``, ``no_fabrication``, the axes and the provenance
    cannot be rewritten by ordinary attribute assignment. Build a changed copy with
    ``model_copy(update=...)`` if a transform genuinely needs one."""
    model_config = ConfigDict(frozen=True)

    design: Mapping[str, Any]
    write_type: str
    axes: Sequence[AxisProof]
    collapsed: None = None # the three axes are NEVER fused into one verdict
    passable: bool # legality passes AND biosecurity does not refuse/escalate (confidence may abstain)
    no_fabrication: bool = True
    provenance: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("design", "provenance")
    @classmethod
    def _deep_freeze(cls, v: Any) -> Any:
        return _freeze(v)

    @field_validator("axes")
    @classmethod
    def _tuple_axes(cls, v: Any) -> Any:
        return tuple(v)

    @field_serializer("design", "provenance")
    def _ser(self, v: Any) -> Any:
        return _thaw(v)

    @field_serializer("axes")
    def _ser_axes(self, v: Sequence[AxisProof]) -> list[dict[str, Any]]:
        """A list, not the stored tuple, so the REST and MCP payload shape is unchanged by the freeze."""
        return [a.model_dump() for a in v]

    def axis(self, name: str) -> AxisProof:
        return next(a for a in self.axes if a.axis == name)


def _pick_vehicle(cargo_bp: int | None, form: str | None, non_integrating: bool) -> str | None:
    """Smallest-capacity vehicle that carries ``form``, fits ``cargo_bp``, and respects an integration goal.
    Deterministic; used to turn a legality violation into a concrete repair."""
    best: tuple[str, float] | None = None
    for name in _vehicle_names():
        rec = _vehicle(name) or {}
        forms = rec.get("compatible_cargo_form") or []
        if form and form not in forms:
            continue
        if non_integrating and rec.get("integrating"):
            continue
        cap = rec.get("cargo_capacity_bp")
        if cargo_bp is not None and cap is not None and cap < cargo_bp:
            continue
        score = float(cap) if cap is not None else float("inf")
        if best is None or score < best[1]:
            best = (name, score)
    return best[0] if best else None


def _repair_for_violation(d: Design, rule_id: str) -> dict[str, Any] | None:
    """A structured, applyable repair for a repairable legality violation, or None if not auto-repairable."""
    form = d.writer_output_form or ("DNA" if d.write_type in ("insertion", "replacement", "landing_pad") else None)
    if rule_id in ("payload.cargo_within_capacity", "delivery.cargo_form_compatible"):
        veh = _pick_vehicle(d.cargo_bp, form, non_integrating=bool(d.no_integration))
        if veh and veh != d.delivery_vehicle:
            why = ("cargo exceeds the vehicle packaging capacity" if "capacity" in rule_id
                   else "the cargo form is not compatible with the vehicle")
            return {"text": f"{why}; switch to a vehicle that fits ({veh}).",
                    "repair": {"field": "delivery_vehicle", "set_to": veh}}
    if rule_id == "delivery.no_integration_constraint":
        veh = _pick_vehicle(d.cargo_bp, form, non_integrating=True)
        if veh and veh != d.delivery_vehicle:
            return {"text": f"the goal forbids integration but the vehicle integrates; switch to {veh}.",
                    "repair": {"field": "delivery_vehicle", "set_to": veh}}
    if rule_id == "reachability.target_element_available":
        return {"text": "the writer cannot reach the target as specified; declare a pre-installed landing pad "
                        "(installed_att) or choose a writer family whose target element is present.",
                "repair": {"field": "installed_att", "set_to": True}}
    if rule_id == "compliance.germline_prohibition":
        return {"text": "this is a heritable / germline edit, which is out of scope for this somatic-editing "
                        "tool and is broadly prohibited (international moratorium); restrict to SOMATIC editing - "
                        "move to ex vivo (in_vivo = false) and/or a somatic cell type (e.g. hepatocytes / HepG2, "
                        "HSPCs), and drop any germline/heritable intent. (Not auto-repairable: a germline edit is "
                        "a change of intent, not a field fix.)",
                "repair": None}
    return None


_SAFETY_REFUSED_SOURCE = "safety_gate(refused)"  # the exact provenance.source verify.service sets on early-return


def _legality_axis(d: Design, v: Verdict) -> AxisProof:
    if v.provenance.get("source") == _SAFETY_REFUSED_SOURCE:
        # biosecurity refused BEFORE the rules engine ran (verify.service short-circuits on refuse), legality
        # was never evaluated, so no rule fired and there is nothing to cite. Reporting "fail" here would
        # fabricate a legality verdict for an axis that never ran. State: unknown, not itself blocking
        # (biosecurity already blocks `passable`), mirrors the "abstaining is a deferral, not a block" convention
        # already used by the confidence axis.
        return AxisProof(axis="legality", status="not_evaluated", ok=True,
                         evidence={"reason": "biosecurity refused this design before legality was evaluated"},
                         repair_hint={"text": "legality was not evaluated, biosecurity refused this design "
                                              "first. Legality can only be checked once the biosecurity concern "
                                              "is resolved (route to institutional biosafety / IBC review).",
                                      "repair": None})
    if v.deferred:
        return AxisProof(axis="legality", status="deferred", ok=False,
                         evidence={"reason": v.routing.get("reason", "unsupported write type")},
                         repair_hint={"text": "the write type is not yet supported; route to a supported type."})
    if v.legal:
        return AxisProof(axis="legality", status="pass", ok=True,
                         evidence={"rules_version": v.provenance.get("rules_version")})
    first = v.violations[0] if v.violations else None
    hint = _repair_for_violation(d, first["rule_id"]) if first else None
    return AxisProof(axis="legality", status="fail", ok=False,
                     violated=[{"rule_id": x["rule_id"], "reason": x["reason"], "citation": x.get("citation", [])}
                               for x in v.violations],
                     evidence={"n_violations": len(v.violations)}, repair_hint=hint)


def _confidence_axis(v: Verdict) -> AxisProof:
    if v.provenance.get("source") == _SAFETY_REFUSED_SOURCE:
        # same short-circuit: confidence was never computed. The "uncalibrated" repair hint below would be
        # ACTIVELY MISLEADING here, supplying the soft scores would not help, since the block happens before
        # they would ever be read.
        return AxisProof(axis="confidence", status="not_evaluated", ok=True,
                         evidence={"confidence": None, "interval": None,
                                   "reason": "biosecurity refused this design before confidence was evaluated"},
                         repair_hint={"text": "confidence was not evaluated, biosecurity refused this design "
                                              "before reaching the confidence check.", "repair": None})
    if v.confidence is None:
        return AxisProof(axis="confidence", status="abstain", ok=True, # abstaining is a deferral, not a block
                         evidence={"confidence": None, "interval": None},
                         repair_hint={"text": "confidence is uncalibrated for this design; supply the soft "
                                              "per-axis scores (safety, p_durable, writer_activity) to calibrate."})
    return AxisProof(axis="confidence", status="pass", ok=True,
                     evidence={"confidence": v.confidence, "interval": v.interval,
                               "epistemic_status": v.epistemic_status})


def _biosecurity_axis(v: Verdict) -> AxisProof:
    s = v.safety
    if s is None:
        return AxisProof(axis="biosecurity", status="pass", ok=True, evidence={"decision": "clear"})
    blocked = s.decision in ("refuse", "escalate")
    # Carry the same detail Guardian's own /api/safety view shows (which signature, and for a
    # sequence-domain hit, which Pfam accession + bit score) -- Design Studio's Proof was previously
    # stripping this down to a bare signature id with no reason/citation/evidence.
    sigs = [{"signature": h.provenance.get("signature_id"), "kind": h.kind, "severity": h.severity,
             "reason": h.detail, "citation": [c for c in [h.provenance.get("control_ref")] if c],
             **({"pfam_accession": h.evidence.get("pfam_accession"), "bit_score": h.evidence.get("bit_score")}
                if h.kind == "sequence_homology" else {})}
            for h in (s.hits or [])]
    # repair hints for a hazard are deliberately NON-actionable: acknowledge and route to human review.
    hint = None
    if blocked:
        hint = {"text": "this design matches a controlled-hazard signature; it is not auto-repairable. "
                        "Route to institutional biosafety / IBC review. (No actionable repair is provided.)",
                "repair": None}
    # "clear" carries two different meanings: screened and nothing found, or nothing screenable was
    # declared so nothing ran. The verdict distinguishes them through provenance.declared_signal, which
    # a caller branching on a status cannot see, so the second case gets its own status here.
    # `ok` stays True because it does not block: a design whose cargo is not yet declared is a normal
    # intermediate state, and no hazard was found. What changes is that the axis no longer reports a
    # clearance it did not make.
    unassessed = s.decision == "clear" and s.provenance.get("declared_signal") is False
    if unassessed:
        return AxisProof(
            axis="biosecurity", status="unassessed", ok=True,
            evidence={"decision": s.decision, "reason": s.reason, "declared_signal": False,
                      "is_clearance": False},
            repair_hint={"text": "nothing screenable was declared, so no screen ran. Declare the cargo "
                                 "function, cargo sequence, domain tags or source taxon and re-verify. "
                                 "This is not a clearance.",
                         "repair": None})
    return AxisProof(axis="biosecurity", status=s.decision, ok=not blocked,
                     violated=sigs, evidence={"decision": s.decision, "reason": s.reason}, repair_hint=hint)


def verify_proof(design: Design | dict, question: str | None = None, *, actor: str = "anonymous") -> Proof:
    """Verify a design and return the per-axis proof object. The three axes are reported separately and the
    collapsed verdict is always None. ``passable`` is True when legality passes and biosecurity does not
    refuse/escalate (an abstaining confidence axis does not block)."""
    d = Design(**dict(design)) if isinstance(design, dict) else design
    v = verify(design, question=question, actor=actor)
    axes = [_legality_axis(d, v), _confidence_axis(v), _biosecurity_axis(v)]
    legality_ok = axes[0].ok
    biosec_ok = axes[2].ok
    return Proof(design=d.model_dump(exclude_none=True), write_type=d.write_type, axes=axes,
                 passable=bool(legality_ok and biosec_ok),
                 provenance={"source": "verify_proof", "rules_version": v.provenance.get("rules_version")})


def repair_from_proof(design: Design | dict, proof: Proof) -> Design:
    """Apply the structured repairs carried by the proof's axes (legality first) and return the repaired
    Design. Uses ONLY the proof object, never re-inspecting the engine, so it demonstrates the proof is
    agent-repairable. Biosecurity hazards are never auto-repaired (their repair is None)."""
    d = Design(**dict(design)) if isinstance(design, dict) else Design(**design.model_dump())
    patch: dict[str, Any] = {}
    for ax in proof.axes:
        hint = ax.repair_hint
        if not hint:
            continue
        rep = hint.get("repair")
        if rep and rep.get("field") is not None:
            patch[rep["field"]] = rep["set_to"]
    if not patch:
        return d
    data = d.model_dump()
    data.update(patch)
    return Design(**data)
