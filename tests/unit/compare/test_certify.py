"""Unit tests for pen_compare.core.certify — tier classifier."""

import pytest

from pen_stack.compare.certify import TrueWriterResult, certify

# ── helpers ──────────────────────────────────────────────────────────────────


def _certify(
    editor_id="X",
    s_dsb=1.0,
    s_prog=1.0,
    s_cargo=1.0,
    length_aa=300,
    evidence_sources=None,
    intrinsic_cargo_mechanism=True,
    split_aav_eligible=False,
    **kwargs,
):
    if evidence_sources is None:
        evidence_sources = ["biochemical", "structural", "computational", "cell_based"]
    return certify(
        editor_id=editor_id,
        s_dsb=s_dsb,
        s_prog=s_prog,
        s_cargo=s_cargo,
        length_aa=length_aa,
        evidence_sources=evidence_sources,
        intrinsic_cargo_mechanism=intrinsic_cargo_mechanism,
        split_aav_eligible=split_aav_eligible,
        **kwargs,
    )


# ── TrueWriterResult structure ────────────────────────────────────────────────


class TestTrueWriterResultFields:
    def test_frozen_dataclass(self):
        r = _certify()
        with pytest.raises((AttributeError, TypeError)):
            r.tier = "OTHER"  # type: ignore[misc]

    def test_has_five_gate_results(self):
        r = _certify()
        assert len(r.gate_results) == 5

    def test_editor_id_preserved(self):
        r = _certify(editor_id="ISCro4")
        assert r.editor_id == "ISCro4"


# ── NOT_WRITER auto-demote path (G1 fails) ───────────────────────────────────


class TestNotWriterAutoDemote:
    def test_zero_dsb_is_not_writer(self):
        r = _certify(s_dsb=0.0)
        assert r.tier == "NOT_WRITER"
        assert r.auto_demoted is True
        assert r.auto_demote_reason is not None

    def test_below_g1_threshold_is_not_writer(self):
        r = _certify(s_dsb=0.94)
        assert r.tier == "NOT_WRITER"
        assert r.auto_demoted is True

    def test_auto_demote_reason_mentions_gate(self):
        r = _certify(s_dsb=0.0)
        reason_lower = r.auto_demote_reason.lower()
        assert "necessary" in reason_lower or "gate" in reason_lower

    def test_no_auto_demote_when_g1_passes(self):
        r = _certify(s_dsb=1.0)
        assert r.auto_demoted is False
        assert r.auto_demote_reason is None


# ── TRUE_WRITER path ──────────────────────────────────────────────────────────


class TestTrueWriter:
    def test_all_gates_pass_with_cell_based(self):
        r = _certify()
        assert r.tier == "TRUE_WRITER"

    def test_qualifying_passed_is_four(self):
        r = _certify()
        assert r.qualifying_gates_passed == 4

    def test_has_cell_based_evidence_true(self):
        r = _certify()  # default evidence_sources includes cell_based
        assert r.has_cell_based_evidence is True

    def test_iscro4_calibration(self):
        r = certify(
            editor_id="ISCro4",
            s_dsb=1.0,
            s_prog=0.9997,
            s_cargo=0.9862,
            length_aa=326,
            evidence_sources=["biochemical", "structural", "computational", "cell_based"],
            intrinsic_cargo_mechanism=True,
        )
        assert r.tier == "TRUE_WRITER"


# ── PROBABLE_WRITER paths ──────────────────────────────────────────────────────


class TestProbableWriter:
    def test_four_qualifying_no_cell_based(self):
        r = certify(
            editor_id="X",
            s_dsb=1.0,
            s_prog=1.0,
            s_cargo=1.0,
            length_aa=300,
            evidence_sources=["biochemical", "structural", "computational"],
            intrinsic_cargo_mechanism=True,
        )
        assert r.tier == "PROBABLE_WRITER"

    def test_three_qualifying_with_cell_based(self):
        # G1 passes (s_dsb=1.0), G5 passes (cell_based + biochemical ≥2)
        # G2 passes (s_prog=1.0), G3 passes (s_cargo=1.0), G4 fails (large)
        r = certify(
            editor_id="X",
            s_dsb=1.0,
            s_prog=1.0,
            s_cargo=1.0,
            length_aa=2000,
            evidence_sources=["cell_based", "biochemical"],
            intrinsic_cargo_mechanism=True,
            split_aav_eligible=False,
        )
        assert r.qualifying_gates_passed == 3
        assert r.tier == "PROBABLE_WRITER"

    def test_is621_calibration(self):
        r = certify(
            editor_id="IS621",
            s_dsb=1.0,
            s_prog=1.0,
            s_cargo=0.95,
            length_aa=342,
            evidence_sources=["biochemical", "structural", "computational"],
            intrinsic_cargo_mechanism=True,
        )
        assert r.tier == "PROBABLE_WRITER"
        assert r.qualifying_gates_passed == 4


# ── EMERGING_WRITER paths ─────────────────────────────────────────────────────


class TestEmergingWriter:
    def test_one_qualifying_is_emerging(self):
        # G1 passes; G5 passes (2 sources ≥2); G2/G3/G4 all fail → qualifying=1
        r = certify(
            editor_id="X",
            s_dsb=1.0,
            s_prog=0.0,
            s_cargo=0.0,
            length_aa=2000,
            evidence_sources=["biochemical", "structural"],
            intrinsic_cargo_mechanism=False,
            split_aav_eligible=False,
        )
        assert r.tier == "EMERGING_WRITER"
        assert r.qualifying_gates_passed == 1

    def test_two_qualifying_is_emerging(self):
        # G2 passes (s_prog=1.0), G5 passes (2 sources), G3 fails, G4 fails → qualifying=2
        r = certify(
            editor_id="X",
            s_dsb=1.0,
            s_prog=1.0,
            s_cargo=0.0,
            length_aa=2000,
            evidence_sources=["biochemical", "structural"],
            intrinsic_cargo_mechanism=False,
            split_aav_eligible=False,
        )
        assert r.qualifying_gates_passed == 2
        assert r.tier == "EMERGING_WRITER"


# ── NOT_WRITER via zero qualifying ───────────────────────────────────────────


class TestNotWriterZeroQualifying:
    def test_g1_passes_zero_qualifying_not_writer(self):
        r = certify(
            editor_id="X",
            s_dsb=1.0,
            s_prog=0.0,
            s_cargo=0.0,
            length_aa=2000,
            evidence_sources=[],
            intrinsic_cargo_mechanism=False,
            split_aav_eligible=False,
        )
        assert r.tier == "NOT_WRITER"
        assert r.auto_demoted is False


# ── Threshold override params ─────────────────────────────────────────────────


class TestThresholdOverrides:
    def test_custom_g1_threshold_allows_lower_dsb(self):
        r = _certify(s_dsb=0.88, g1_threshold=0.85)
        assert r.tier != "NOT_WRITER" or r.auto_demoted is False

    def test_custom_g1_threshold_blocks_lower_dsb(self):
        r = _certify(s_dsb=0.88, g1_threshold=0.90)
        assert r.tier == "NOT_WRITER"
        assert r.auto_demoted is True

    def test_custom_g2_threshold(self):
        # Default g2 threshold = 0.95; s_prog=0.90 fails default but passes with 0.85
        r_default = _certify(s_prog=0.90)
        r_custom = _certify(s_prog=0.90, g2_threshold=0.85)
        g2_default = next(g for g in r_default.gate_results if "programmability" in g.gate_id)
        g2_custom = next(g for g in r_custom.gate_results if "programmability" in g.gate_id)
        assert g2_default.passes is False
        assert g2_custom.passes is True

    def test_custom_g4_size_max(self):
        # length_aa=1000 fails default g4_size_max=900; passes with size_max=1100
        r_fail = _certify(length_aa=1000, g4_size_max=900)
        r_pass = _certify(length_aa=1000, g4_size_max=1100)
        g4_fail = next(g for g in r_fail.gate_results if "deliverability" in g.gate_id)
        g4_pass = next(g for g in r_pass.gate_results if "deliverability" in g.gate_id)
        assert g4_fail.passes is False
        assert g4_pass.passes is True


# ── Edge cases ────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_length_aa_none_uses_split_aav(self):
        r = certify(
            editor_id="X",
            s_dsb=1.0,
            s_prog=1.0,
            s_cargo=1.0,
            length_aa=None,
            evidence_sources=["cell_based", "biochemical"],
            intrinsic_cargo_mechanism=True,
            split_aav_eligible=True,
        )
        g4 = next(g for g in r.gate_results if "deliverability" in g.gate_id)
        assert g4.passes is True

    def test_empty_evidence_sources(self):
        r = certify(
            editor_id="X",
            s_dsb=1.0,
            s_prog=1.0,
            s_cargo=1.0,
            length_aa=300,
            evidence_sources=[],
            intrinsic_cargo_mechanism=True,
        )
        assert r.has_cell_based_evidence is False

    def test_return_type(self):
        r = _certify()
        assert isinstance(r, TrueWriterResult)
