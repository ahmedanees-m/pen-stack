"""Calibration anchor tests — these MUST pass for v3.2 framework integrity.

The 4 calibration anchors are defined in config/gates_v3.yaml and must produce
their pre-registered expected tiers.  Any failure here is a framework bug,
not a scientific finding.
"""

from pen_stack.compare.certify import certify


def test_iscro4_is_true_writer():
    """ISCro4: canonical TRUE_WRITER anchor (D2TGM5, C. rodentium ICC168, 326 aa)."""
    result = certify(
        editor_id="ISCro4",
        s_dsb=1.0,
        s_prog=1.0,
        s_cargo=0.95,
        length_aa=326,
        evidence_sources=["biochemical", "structural", "computational", "cell_based"],
        intrinsic_cargo_mechanism=True,
    )
    assert result.tier == "TRUE_WRITER", f"Expected TRUE_WRITER, got {result.tier}"
    assert result.has_cell_based_evidence is True
    assert result.qualifying_gates_passed == 4
    assert result.auto_demoted is False


def test_is621_is_probable_writer_no_cell_data():
    """IS621: PROBABLE_WRITER — passes all 4 qualifying gates but lacks cell_based evidence."""
    result = certify(
        editor_id="IS621",
        s_dsb=1.0,
        s_prog=1.0,
        s_cargo=0.95,
        length_aa=342,
        evidence_sources=["biochemical", "structural", "computational"],  # no cell_based
        intrinsic_cargo_mechanism=True,
    )
    assert result.tier == "PROBABLE_WRITER", f"Expected PROBABLE_WRITER, got {result.tier}"
    assert result.has_cell_based_evidence is False
    assert result.qualifying_gates_passed == 4


def test_bxb1_is_probable_writer_fails_programmability():
    """Bxb1: PROBABLE_WRITER — fails G2 (site-specific serine integrase, fixed att sites)."""
    result = certify(
        editor_id="Bxb1",
        s_dsb=1.0,
        s_prog=0.0,  # site-specific → not RNA-programmable
        s_cargo=0.95,
        length_aa=500,
        evidence_sources=["biochemical", "structural", "cell_based"],
        intrinsic_cargo_mechanism=True,
    )
    assert result.tier == "PROBABLE_WRITER", f"Expected PROBABLE_WRITER, got {result.tier}"
    assert result.qualifying_gates_passed == 3  # G2 fails


def test_spcas9_is_not_writer_auto_demote():
    """SpCas9: NOT_WRITER via necessary-gate auto-fail (S_DSB=0.0, makes DSBs)."""
    result = certify(
        editor_id="SpCas9",
        s_dsb=0.0,  # makes DSBs → necessary gate fails
        s_prog=1.0,
        s_cargo=0.90,
        length_aa=1368,
        evidence_sources=["biochemical", "structural", "cell_based"],
        intrinsic_cargo_mechanism=False,
        split_aav_eligible=True,
    )
    assert result.tier == "NOT_WRITER", f"Expected NOT_WRITER, got {result.tier}"
    assert result.auto_demoted is True
    assert "Necessary gate" in result.auto_demote_reason


def test_design_capped_no_cell_based():
    """Computational design: caps at EMERGING_WRITER without cell_based (G5 fails with 1 source)."""
    result = certify(
        editor_id="IS621_deimmunized_v2",
        s_dsb=1.0,
        s_prog=1.0,
        s_cargo=0.97,
        length_aa=342,
        evidence_sources=["computational"],  # only 1 source → G5 fails
        intrinsic_cargo_mechanism=True,
    )
    # 3/4 qualifying (G5 fails) + no cell_based → EMERGING_WRITER
    assert result.tier == "EMERGING_WRITER"
    assert result.qualifying_gates_passed == 3


def test_necessary_gate_overrides_all_qualifying():
    """Even if all qualifying gates pass, G1 fail → NOT_WRITER."""
    result = certify(
        editor_id="AsCas12a",
        s_dsb=0.0,
        s_prog=1.0,
        s_cargo=0.95,
        length_aa=600,
        evidence_sources=["biochemical", "structural", "computational", "cell_based"],
        intrinsic_cargo_mechanism=True,
    )
    assert result.tier == "NOT_WRITER"
    assert result.auto_demoted is True
