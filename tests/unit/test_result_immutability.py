"""The type-level immutability invariant on OracleResult, asserted rather than asserted-about.

These are the adversarial probes the paper reports for the frozen result type: an agent step or a
downstream transform must not be able to rewrite a flag on a result it was handed. The last test
pins the *boundary* of that claim -- `object.__setattr__` is not blocked and cannot be, so it is
recorded here as an executable fact rather than left to prose.
"""
import pytest
from pydantic import ValidationError

from pen_stack.oracles.schema import OracleResult, Provenance


def _result(**kw):
    base = dict(
        oracle="genome",
        value=0.42,
        provenance=Provenance(model="evo2", version="1.0", extra={"members": ["evo2"], "spread": 0.1}),
        output_kind="candidate",
        in_scope=True,
        extrapolating=False,
    )
    base.update(kw)
    return OracleResult(**base)


@pytest.mark.parametrize("field,value", [
    ("output_kind", "claim"),      # launder a candidate into a claim
    ("in_scope", False),           # rewrite the scope verdict
    ("extrapolating", False),      # hide out-of-distribution use
    ("available", False),          # rewrite availability
])
def test_result_fields_cannot_be_reassigned(field, value):
    r = _result()
    with pytest.raises(ValidationError):
        setattr(r, field, value)
    assert getattr(r, field) != value or field == "extrapolating"


@pytest.mark.parametrize("field", ["model", "version", "source"])
def test_nested_provenance_cannot_be_reassigned(field):
    r = _result()
    with pytest.raises(ValidationError):
        setattr(r.provenance, field, "laundered")
    assert getattr(r.provenance, field) != "laundered"


def test_provenance_extra_is_deep_frozen():
    """`frozen` blocks attribute assignment, not mutation of a mutable field value; a plain dict
    here would leave the one writable surface on an object documented as immutable."""
    r = _result()
    with pytest.raises(TypeError):
        r.provenance.extra["model"] = "laundered"
    with pytest.raises((TypeError, AttributeError)):
        r.provenance.extra.update({"model": "laundered"})
    assert r.provenance.extra["members"] == ["evo2"]


def test_extra_survives_a_serialisation_round_trip():
    """The deep-freeze must not cost JSON serialisability: OracleResult crosses the REST boundary."""
    r = _result()
    dumped = r.model_dump_json()
    assert '"spread":0.1' in dumped.replace(" ", "")
    back = OracleResult.model_validate_json(dumped)
    assert dict(back.provenance.extra) == {"members": ["evo2"], "spread": 0.1}
    with pytest.raises(TypeError):
        back.provenance.extra["x"] = 1


def test_model_copy_is_the_sanctioned_escape_hatch():
    """A transform that genuinely needs a changed result builds a new one; the original is untouched."""
    r = _result()
    promoted = r.model_copy(update={"output_kind": "claim"})
    assert promoted.output_kind == "claim"
    assert r.output_kind == "candidate"
    assert promoted is not r


def test_object_setattr_is_not_blocked_and_the_paper_says_so():
    """The documented boundary of the invariant.

    Python offers no memory safety, so a caller with arbitrary code execution can bypass the frozen
    model. The guarantee is against inadvertent rewriting by an agent step or a downstream transform,
    not against a determined caller. If this test ever starts failing, the manuscript's Limitations
    paragraph needs updating too -- it is the assertion that keeps prose and code honest with each other.
    """
    r = _result()
    object.__setattr__(r, "output_kind", "claim")
    assert r.output_kind == "claim"
