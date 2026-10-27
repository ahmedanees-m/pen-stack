"""Where the typed contract holds, and where it stops.

`test_result_immutability.py` pins the invariant on the oracle result type. This file does the same
for the verification surface, and then states the boundary in executable form rather than in prose:
which outputs are protected, where enforcement sits, and what survives serialisation to an external
client. The last two tests record properties that do NOT hold, so the claim stays tied to what is
enforced.
"""
import json

import pytest
from pydantic import ValidationError

from pen_stack.verify.proof import AxisProof, Proof, verify_proof

HAZARD = {"write_type": "insertion", "cargo_function": "ricin-like RIP",
          "pfam_domains": ["PF00161"], "source_taxon": "Ricinus communis",
          "delivery_vehicle": "AAV"}
OVER_CAPACITY = {"write_type": "insertion", "cargo_bp": 8000, "delivery_vehicle": "aav",
                 "target_locus": "AAVS1", "cell_type": "k562"}


@pytest.mark.parametrize("field,value", [
    ("passable", True),         # turn a blocked design into a passing one
    ("no_fabrication", False),  # rewrite the contract flag itself
    ("write_type", "edit"),
])
def test_proof_fields_cannot_be_reassigned(field, value):
    p = verify_proof(OVER_CAPACITY)
    with pytest.raises(ValidationError):
        setattr(p, field, value)
    assert getattr(p, field) != value


@pytest.mark.parametrize("field,value", [
    ("status", "pass"),  # a failing axis reported as passing
    ("ok", True),        # a blocking axis reported as non-blocking
])
def test_axis_verdicts_cannot_be_reassigned(field, value):
    p = verify_proof(OVER_CAPACITY)
    leg = p.axis("legality")
    assert leg.status == "fail" and leg.ok is False
    with pytest.raises(ValidationError):
        setattr(leg, field, value)
    assert getattr(leg, field) != value


def test_the_rule_that_fired_cannot_be_dropped_or_edited():
    """A caller handed a failed proof must not be able to empty the violation list, or edit the
    rule inside it, and then present the design as clean."""
    p = verify_proof(OVER_CAPACITY)
    leg = p.axis("legality")
    assert leg.violated and leg.violated[0]["rule_id"]
    with pytest.raises((AttributeError, TypeError)):
        leg.violated.clear()
    with pytest.raises(TypeError):
        leg.violated[0]["rule_id"] = "payload.ok"
    with pytest.raises(TypeError):
        leg.evidence["cargo_bp"] = 1
    assert leg.violated[0]["rule_id"] == "payload.cargo_within_capacity"


def test_a_hazard_verdict_and_its_non_actionable_hint_cannot_be_rewritten():
    """The biosecurity axis is the one whose repair hint is deliberately non-actionable; an agent
    must not be able to replace it with an actionable one."""
    p = verify_proof(HAZARD)
    bio = p.axis("biosecurity")
    assert bio.ok is False and bio.status in {"refuse", "escalate", "flag"}
    with pytest.raises(ValidationError):
        bio.repair_hint = {"text": "swap the vehicle", "repair": {"field": "cargo_function",
                                                                  "set_to": "benign"}}
    with pytest.raises(TypeError):
        bio.repair_hint["repair"] = {"field": "cargo_function", "set_to": "benign"}
    assert bio.repair_hint["repair"] is None


def test_axes_cannot_be_added_removed_or_reordered():
    p = verify_proof(HAZARD)
    assert [a.axis for a in p.axes] == ["legality", "confidence", "biosecurity"]
    with pytest.raises((AttributeError, TypeError)):
        p.axes.append(AxisProof(axis="legality", status="pass", ok=True))
    with pytest.raises((AttributeError, TypeError)):
        p.axes.pop()
    with pytest.raises(ValidationError):
        p.axes = ()
    assert len(p.axes) == 3


def test_model_copy_is_the_sanctioned_escape_hatch():
    """A transform that genuinely needs a changed proof builds a new one; the original is untouched."""
    p = verify_proof(OVER_CAPACITY)
    forced = p.model_copy(update={"passable": True})
    assert forced.passable is True
    assert p.passable is False
    assert forced is not p


def test_the_wire_shape_is_unchanged_by_the_freeze():
    """The proof crosses the REST and MCP boundaries via `model_dump()`. The freeze must not change
    the payload a published client already parses: plain JSON types, axes as an array."""
    p = verify_proof(OVER_CAPACITY)
    dumped = p.model_dump()
    assert isinstance(dumped["design"], dict)
    assert isinstance(dumped["axes"], list)
    assert isinstance(dumped["axes"][0]["violated"], list)
    assert isinstance(dumped["axes"][0]["evidence"], dict)
    assert dumped["collapsed"] is None and dumped["no_fabrication"] is True
    round_tripped = json.loads(p.model_dump_json())
    assert round_tripped["axes"][0]["violated"][0]["rule_id"] == "payload.cargo_within_capacity"


def test_the_guarantee_does_not_survive_the_rest_boundary():
    """The documented limit of the contract across serialisation.

    Over REST or MCP the proof is delivered as ordinary JSON. The frozen type is an in-process
    Python property; an external client receives a mutable object and the type system has no reach
    into it. This is asserted rather than described so the manuscript cannot drift from it: the
    claim is that a *downstream Python caller* holding the returned object cannot rewrite it, not
    that a verdict is tamper-proof once it has left the process.
    """
    p = verify_proof(OVER_CAPACITY)
    payload = json.loads(p.model_dump_json())
    payload["passable"] = True
    payload["axes"][0]["status"] = "pass"
    payload["axes"][0]["violated"] = []
    assert payload["passable"] is True          # nothing stops this
    assert p.passable is False                  # the in-process object is unaffected
    revalidated = Proof.model_validate(payload)
    assert revalidated.passable is True         # and a re-validated copy carries the edit
    assert revalidated is not p


def test_object_setattr_is_not_blocked_and_the_paper_says_so():
    """The same boundary the oracle result type records, restated for the proof.

    Python offers no memory safety, so a caller running arbitrary code bypasses the frozen model.
    The guarantee is against inadvertent rewriting by an agent step or a downstream transform, not
    against a determined caller. If this test starts failing, the Limitations paragraph needs
    updating with it.
    """
    p = verify_proof(OVER_CAPACITY)
    object.__setattr__(p, "passable", True)
    assert p.passable is True
