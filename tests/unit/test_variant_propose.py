"""Phase 2, Step 2.4 — DMS-grounded variant proposal framework.

Asserts the structural criteria: only point substitutions are proposed (NO chimeras), the model is
pluggable, and the retrospective-recovery harness functions. The headline "recover the published
enhanced variant blind" criterion is evaluated when the Phase-1.5 DMS model is supplied.
"""
from __future__ import annotations

from pen_stack.atlas.variant_propose import (
    BaselinePhysicoChemical,
    propose_variants,
    retrospective_recovery,
)


def test_proposals_are_point_substitutions_only():
    seq = "MSEQNKIACDEF"
    props = propose_variants(seq, BaselinePhysicoChemical(), top=15)
    assert len(props) == 15
    # each proposal is a single substitution at a valid position; wt matches the sequence
    for _, r in props.iterrows():
        assert r["wt"] == seq[r["pos"]]
        assert r["mut"] != r["wt"]
        assert len(r["variant"]) >= 3   # e.g. M1A — never a chimera/multi-segment string


def test_model_is_pluggable():
    class Dummy:
        name = "dummy"

        def predict(self, seq, variants):
            return [float(i) for i, _, _ in variants]   # rank by position

    props = propose_variants("ACDEF", Dummy(), top=3)
    assert props["model"].iloc[0] == "dummy"
    assert props["pos"].iloc[0] >= props["pos"].iloc[-1]   # highest position first


def test_retrospective_recovery_harness():
    seq = "ACDEFGHIKL"
    props = propose_variants(seq, BaselinePhysicoChemical(), top=50)
    known = [props.iloc[0]["variant"]]            # plant a known hit -> must be recovered
    res = retrospective_recovery(props, known, k=50)
    assert res["any_recovered"] is True
    res_miss = retrospective_recovery(props, ["Z999Z"], k=5)
    assert res_miss["any_recovered"] is False
