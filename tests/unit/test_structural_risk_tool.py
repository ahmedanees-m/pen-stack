"""The structural-risk quantity is reachable from the agent's action space, or says it is not.

The fabrication probe requires six tool-only quantities per goal. Five were reachable through the
agent's tools; `structural_risk_score` was not, so an agent asked for it had no grounded route and
dropped it from the plan silently. Silence is the one outcome the contract does not allow: a value
outside a tool's scope is supposed to come back as an explicit known-unknown. These tests pin the
tool's presence and both of its branches.
"""
import pytest

from pen_stack.agent.tools import REGISTRY, SCHEMAS, dispatch

TOOL = "structural_risk"


def test_the_quantity_is_reachable_from_the_action_space():
    names = [s["function"]["name"] for s in SCHEMAS]
    assert TOOL in names, "the agent cannot ground a quantity it has no tool for"
    assert TOOL in REGISTRY
    schema = next(s["function"] for s in SCHEMAS if s["function"]["name"] == TOOL)
    assert set(schema["parameters"]["required"]) == {"chrom", "pos"}


def test_out_of_scope_returns_a_known_unknown_not_a_guess_and_not_an_error():
    """Shipped configuration, no AlphaGenome key: the tool must abstain explicitly."""
    r = dispatch(TOOL, {"chrom": "chr14", "pos": 22548000})
    assert r["available"] is False
    assert r["structural_risk_score"] is None       # no number invented to fill the gap
    assert r["abstain"] is True                      # and the abstention is machine-readable
    assert r["epistemic_status"] == "not-computable"
    assert r["reason"]                               # with a stated reason
    assert r["tool"] == "wgenome.structure3d"        # and provenance for where it would come from


def test_the_abstention_is_distinguishable_from_a_score_of_zero():
    """A caller must not be able to read the known-unknown as a low-risk verdict."""
    r = dispatch(TOOL, {"chrom": "chr14", "pos": 22548000})
    score = r["structural_risk_score"]
    assert score is None            # absent, not a number
    assert not isinstance(score, (int, float))  # so it can never be read as "zero risk"
    assert r["abstain"] is True


def test_dispatch_rejects_an_unknown_tool_rather_than_improvising():
    with pytest.raises(KeyError):
        dispatch("structural_risk_estimate", {"chrom": "chr14", "pos": 1})


def test_an_undeclared_design_reports_unassessed_not_clear():
    """A "clear" with nothing screenable declared is not a clearance, and now says so.

    The safety verdict has always carried the distinction in `provenance.declared_signal`, but no
    consumer read it: every gate branched on the decision string, so a design that declared no cargo
    function, sequence, domain tag or taxon was handled exactly like a screened benign one. The proof
    axis now reports `unassessed` for that case, and the emitted protocol carries it in provenance.
    """
    from pen_stack.verify.proof import verify_proof

    declared = {"write_type": "insertion", "cargo_function": "human factor IX clotting factor",
                "target_locus": "ALB", "cell_type": "k562", "cargo_bp": 1400,
                "delivery_vehicle": "lentivirus"}
    undeclared = {"write_type": "insertion", "target_locus": "ALB", "cell_type": "k562",
                  "cargo_bp": 1400, "delivery_vehicle": "lentivirus"}

    a = verify_proof(declared).axis("biosecurity")
    b = verify_proof(undeclared).axis("biosecurity")

    assert a.status == "clear"
    assert b.status == "unassessed"              # the two are distinguishable by status
    assert b.evidence["declared_signal"] is False
    assert b.evidence["is_clearance"] is False   # and it does not claim to be one
    assert b.repair_hint and "not a clearance" in b.repair_hint["text"]
    # neither blocks: no hazard was found in either case
    assert a.ok is True and b.ok is True
