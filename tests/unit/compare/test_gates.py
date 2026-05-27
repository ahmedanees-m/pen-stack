"""Unit tests for the 5 TrueWriterScore gate functions."""

from pen_stack.compare.gates import (
    GateRole,
    gate_1_dsb,
    gate_2_programmability,
    gate_3_native_cargo,
    gate_4_deliverability,
    gate_5_evidence,
)


class TestGate1DSB:
    def test_passes_at_threshold(self):
        assert gate_1_dsb(0.95).passes is True

    def test_passes_above_threshold(self):
        assert gate_1_dsb(1.0).passes is True

    def test_fails_just_below(self):
        assert gate_1_dsb(0.9499).passes is False

    def test_fails_at_zero(self):
        assert gate_1_dsb(0.0).passes is False

    def test_role_is_necessary(self):
        assert gate_1_dsb(1.0).role == GateRole.NECESSARY

    def test_custom_threshold(self):
        assert gate_1_dsb(0.90, threshold=0.85).passes is True
        assert gate_1_dsb(0.84, threshold=0.85).passes is False

    # Calibration anchors
    def test_iscro4_perfect_dsb(self):
        assert gate_1_dsb(1.0).passes is True

    def test_is621_perfect_dsb(self):
        assert gate_1_dsb(1.0).passes is True

    def test_spcas9_fails_categorically(self):
        assert gate_1_dsb(0.0).passes is False


class TestGate2Programmability:
    def test_passes_at_threshold(self):
        assert gate_2_programmability(0.95).passes is True

    def test_fails_below(self):
        assert gate_2_programmability(0.94).passes is False

    def test_role_is_qualifying(self):
        assert gate_2_programmability(1.0).role == GateRole.QUALIFYING

    def test_bxb1_fails(self):
        # Bxb1: site-specific, S_Prog=0.0
        assert gate_2_programmability(0.0).passes is False

    def test_custom_threshold(self):
        assert gate_2_programmability(0.90, threshold=0.85).passes is True


class TestGate3NativeCargo:
    def test_iscro4_passes(self):
        assert gate_3_native_cargo(0.95, intrinsic_cargo_mechanism=True).passes is True

    def test_at_threshold(self):
        assert gate_3_native_cargo(0.90, intrinsic_cargo_mechanism=True).passes is True

    def test_fails_below_threshold(self):
        assert gate_3_native_cargo(0.89, intrinsic_cargo_mechanism=True).passes is False

    def test_fails_without_intrinsic(self):
        assert gate_3_native_cargo(0.99, intrinsic_cargo_mechanism=False).passes is False

    def test_spcas9_fails_hdr_template(self):
        assert gate_3_native_cargo(0.95, intrinsic_cargo_mechanism=False).passes is False

    def test_role_is_qualifying(self):
        assert gate_3_native_cargo(0.95, True).role == GateRole.QUALIFYING


class TestGate4Deliverability:
    def test_small_editor_passes(self):
        assert gate_4_deliverability(326).passes is True

    def test_at_limit(self):
        assert gate_4_deliverability(900).passes is True

    def test_just_over_limit(self):
        assert gate_4_deliverability(901).passes is False

    def test_large_editor_with_split_aav(self):
        assert gate_4_deliverability(1400, split_aav_eligible=True).passes is True

    def test_none_length_no_split(self):
        assert gate_4_deliverability(None, split_aav_eligible=False).passes is False

    def test_none_length_with_split(self):
        assert gate_4_deliverability(None, split_aav_eligible=True).passes is True

    def test_role_is_qualifying(self):
        assert gate_4_deliverability(326).role == GateRole.QUALIFYING

    def test_custom_size_max(self):
        assert gate_4_deliverability(700, size_max=750).passes is True
        assert gate_4_deliverability(800, size_max=750).passes is False


class TestGate5Evidence:
    def test_two_sources_passes(self):
        assert gate_5_evidence(["biochemical", "structural"]).passes is True

    def test_four_sources_passes(self):
        sources = ["biochemical", "structural", "computational", "cell_based"]
        assert gate_5_evidence(sources).passes is True

    def test_one_source_fails(self):
        assert gate_5_evidence(["computational"]).passes is False

    def test_empty_fails(self):
        assert gate_5_evidence([]).passes is False

    def test_unknown_source_ignored(self):
        # Only 1 eligible → fails even though 2 strings provided
        assert gate_5_evidence(["biochemical", "rumor"]).passes is False

    def test_role_is_qualifying(self):
        assert gate_5_evidence(["biochemical", "structural"]).role == GateRole.QUALIFYING

    # Calibration anchors
    def test_iscro4_three_sources(self):
        assert gate_5_evidence(["biochemical", "computational", "cell_based"]).passes is True

    def test_is621_three_sources(self):
        assert gate_5_evidence(["biochemical", "structural", "computational"]).passes is True
