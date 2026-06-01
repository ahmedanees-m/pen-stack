"""Cross-module universe consistency (Step 0.4) — the headline Phase-0 fix.

One canonical assembly path; the classifier/scorer/scorecard must consume identical metadata.
"""
import pandas as pd

from pen_stack.atlas.universe import assemble, canonical_inputs


def test_assemble_is_deterministic():
    a = assemble()
    b = assemble()
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


def test_universe_size_and_core():
    df = assemble()
    assert len(df) == 1058
    assert (df["source"] == "natural").sum() == 29


def test_length_backfilled_for_verified_ids():
    df = assemble().set_index("entity_id")
    assert df.loc["ISCro4", "length_aa"] == 326
    assert df.loc["SpCas9", "length_aa"] == 1368


def test_prog_is_regrounded_not_flat_flag():
    df = assemble()
    nat = df[df["source"] == "natural"]
    # the old s_prog was a flat 0/1 flag; the re-grounded S_Prog must vary across families
    assert nat["S_Prog"].nunique() >= 3
    # bipartite bridge family gets full programmability; fixed-att integrases get the low anchor
    bridge = nat[nat["family"] == "bridge_IS110"]["S_Prog"]
    serine = nat[nat["family"] == "serine_integrase"]["S_Prog"]
    assert (bridge == 1.0).all()
    assert (serine < 0.5).all()


def test_canonical_inputs_complete_for_natural():
    df = assemble()
    ci = canonical_inputs(df)
    assert set(["S_Prog", "S_Cargo", "length_aa", "family"]).issubset(ci.columns)
    nat = df[df["source"] == "natural"]
    assert nat["S_Prog"].notna().all()              # no NaN axis inputs for the curated core
