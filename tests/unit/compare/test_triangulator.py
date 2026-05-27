"""Unit tests for pen_compare.triangulation.triangulator."""

import textwrap

import pandas as pd
import pytest

from pen_stack.compare.triangulation.triangulator import (
    DiscrepancyRecord,
    Triangulator,
    _float,
)

# ── fixtures ──────────────────────────────────────────────────────────────────

RULES_YAML = textwrap.dedent("""\
    discrepancy_categories:
      AXIS_VS_TIER:
        severity: high
        description: S_DSB contradicts mech-class tier_a_gate for natural editors.
      MECH_VS_PFAM:
        severity: high
        description: PFAM-based atlas classification disagrees with mech-class tier.
      CARGO_INCONSISTENCY:
        severity: medium
        description: intrinsic_cargo=True but S_Cargo < 0.60.
      EVIDENCE_GAP:
        severity: low
        description: IS110 confirmed but no cell-based evidence.
      SIZE_INCONSISTENCY:
        severity: medium
        description: atlas entry present but length_aa unknown.
""")


@pytest.fixture
def rules_file(tmp_path):
    p = tmp_path / "triangulation_rules.yaml"
    p.write_text(RULES_YAML)
    return p


@pytest.fixture
def tri(rules_file):
    return Triangulator(rules_path=rules_file)


def _row(**kwargs):
    defaults = dict(
        entity_id="E1",
        source="natural",
        s_dsb=0.5,
        s_prog=0.5,
        s_cargo=0.7,
        tier_a_gate=False,
        atlas_system_present=False,
        intrinsic_cargo_mechanism=False,
        cell_based_evidence=False,
        length_aa=300.0,
    )
    defaults.update(kwargs)
    return pd.Series(defaults)


# ── _float helper ─────────────────────────────────────────────────────────────


class TestFloat:
    def test_numeric(self):
        assert _float(pd.Series({"x": 0.5}), "x") == pytest.approx(0.5)

    def test_none(self):
        assert _float(pd.Series({"x": None}), "x") is None

    def test_nan(self):
        assert _float(pd.Series({"x": float("nan")}), "x") is None

    def test_missing_key(self):
        assert _float(pd.Series({"y": 1.0}), "x") is None

    def test_string_number(self):
        assert _float(pd.Series({"x": "0.9"}), "x") == pytest.approx(0.9)

    def test_non_numeric_string(self):
        assert _float(pd.Series({"x": "abc"}), "x") is None


# ── AXIS_VS_TIER rule ─────────────────────────────────────────────────────────


class TestAxisVsTier:
    def test_high_dsb_not_tier_a_triggers(self, tri):
        row = _row(s_dsb=0.97, tier_a_gate=False)
        recs = list(tri._rule_axis_vs_tier(row))
        assert len(recs) == 1
        assert recs[0].category == "AXIS_VS_TIER"
        assert recs[0].severity == "high"

    def test_tier_a_low_dsb_triggers(self, tri):
        row = _row(s_dsb=0.70, tier_a_gate=True)
        recs = list(tri._rule_axis_vs_tier(row))
        assert len(recs) == 1
        assert recs[0].category == "AXIS_VS_TIER"

    def test_consistent_case_no_trigger(self, tri):
        row = _row(s_dsb=0.97, tier_a_gate=True)
        assert list(tri._rule_axis_vs_tier(row)) == []

    def test_design_source_skipped(self, tri):
        row = _row(source="design", s_dsb=0.97, tier_a_gate=False)
        assert list(tri._rule_axis_vs_tier(row)) == []

    def test_no_trigger_when_dsb_below_threshold_and_tier_a_false(self, tri):
        row = _row(s_dsb=0.50, tier_a_gate=False)
        assert list(tri._rule_axis_vs_tier(row)) == []


# ── MECH_VS_PFAM rule ─────────────────────────────────────────────────────────


class TestMechVsPfam:
    def test_atlas_no_tier_a_high_dsb_triggers(self, tri):
        row = _row(atlas_system_present=True, tier_a_gate=False, s_dsb=0.97)
        recs = list(tri._rule_mech_vs_pfam(row))
        assert len(recs) == 1
        assert recs[0].category == "MECH_VS_PFAM"

    def test_tier_a_no_atlas_high_dsb_triggers(self, tri):
        row = _row(atlas_system_present=False, tier_a_gate=True, s_dsb=0.97)
        recs = list(tri._rule_mech_vs_pfam(row))
        assert len(recs) == 1
        assert recs[0].category == "MECH_VS_PFAM"

    def test_consistent_no_trigger(self, tri):
        row = _row(atlas_system_present=True, tier_a_gate=True, s_dsb=0.97)
        assert list(tri._rule_mech_vs_pfam(row)) == []

    def test_design_source_skipped(self, tri):
        row = _row(source="design", atlas_system_present=True, tier_a_gate=False, s_dsb=0.97)
        assert list(tri._rule_mech_vs_pfam(row)) == []


# ── CARGO_INCONSISTENCY rule ──────────────────────────────────────────────────


class TestCargoInconsistency:
    def test_intrinsic_cargo_low_s_cargo_triggers(self, tri):
        row = _row(intrinsic_cargo_mechanism=True, s_cargo=0.40)
        recs = list(tri._rule_cargo_inconsistency(row))
        assert len(recs) == 1
        assert recs[0].category == "CARGO_INCONSISTENCY"
        assert recs[0].severity == "medium"

    def test_intrinsic_cargo_high_s_cargo_no_trigger(self, tri):
        row = _row(intrinsic_cargo_mechanism=True, s_cargo=0.70)
        assert list(tri._rule_cargo_inconsistency(row)) == []

    def test_no_intrinsic_cargo_no_trigger(self, tri):
        row = _row(intrinsic_cargo_mechanism=False, s_cargo=0.30)
        assert list(tri._rule_cargo_inconsistency(row)) == []

    def test_applies_to_design_source(self, tri):
        row = _row(source="design", intrinsic_cargo_mechanism=True, s_cargo=0.40)
        recs = list(tri._rule_cargo_inconsistency(row))
        assert len(recs) == 1


# ── EVIDENCE_GAP rule ─────────────────────────────────────────────────────────


class TestEvidenceGap:
    def test_is110_no_cell_based_triggers(self, tri):
        row = _row(tier_a_gate=True, s_dsb=0.97, cell_based_evidence=False)
        recs = list(tri._rule_evidence_gap(row))
        assert len(recs) == 1
        assert recs[0].category == "EVIDENCE_GAP"
        assert recs[0].severity == "low"

    def test_is110_with_cell_based_no_trigger(self, tri):
        row = _row(tier_a_gate=True, s_dsb=0.97, cell_based_evidence=True)
        assert list(tri._rule_evidence_gap(row)) == []

    def test_non_is110_no_trigger(self, tri):
        row = _row(tier_a_gate=False, s_dsb=0.97, cell_based_evidence=False)
        assert list(tri._rule_evidence_gap(row)) == []

    def test_design_source_skipped(self, tri):
        row = _row(source="design", tier_a_gate=True, s_dsb=0.97, cell_based_evidence=False)
        assert list(tri._rule_evidence_gap(row)) == []


# ── SIZE_INCONSISTENCY rule ───────────────────────────────────────────────────


class TestSizeInconsistency:
    def test_atlas_nan_length_triggers(self, tri):
        row = _row(atlas_system_present=True, length_aa=float("nan"))
        recs = list(tri._rule_size_inconsistency(row))
        assert len(recs) == 1
        assert recs[0].category == "SIZE_INCONSISTENCY"

    def test_atlas_none_length_triggers(self, tri):
        row = _row(atlas_system_present=True, length_aa=None)
        recs = list(tri._rule_size_inconsistency(row))
        assert len(recs) == 1

    def test_atlas_known_length_no_trigger(self, tri):
        row = _row(atlas_system_present=True, length_aa=300.0)
        assert list(tri._rule_size_inconsistency(row)) == []

    def test_no_atlas_no_trigger(self, tri):
        row = _row(atlas_system_present=False, length_aa=float("nan"))
        assert list(tri._rule_size_inconsistency(row)) == []

    def test_design_source_skipped(self, tri):
        row = _row(source="design", atlas_system_present=True, length_aa=float("nan"))
        assert list(tri._rule_size_inconsistency(row)) == []


# ── audit + run_full public API ───────────────────────────────────────────────


class TestPublicAPI:
    def test_audit_unknown_entity_returns_empty(self, tri):
        universe = pd.DataFrame([_row(entity_id="E1").to_dict()])
        assert tri.audit("UNKNOWN", universe) == []

    def test_audit_returns_list(self, tri):
        universe = pd.DataFrame([_row(entity_id="E1").to_dict()])
        result = tri.audit("E1", universe)
        assert isinstance(result, list)

    def test_run_full_returns_dataframe(self, tri):
        universe = pd.DataFrame([_row(entity_id="E1").to_dict()])
        df = tri.run_full(universe)
        assert isinstance(df, pd.DataFrame)

    def test_run_full_empty_universe_returns_empty_df(self, tri):
        df = tri.run_full(pd.DataFrame())
        assert len(df) == 0

    def test_run_full_columns(self, tri):
        row = _row(entity_id="E1", atlas_system_present=True, length_aa=float("nan"))
        universe = pd.DataFrame([row.to_dict()])
        df = tri.run_full(universe)
        assert "entity_id" in df.columns
        assert "category" in df.columns
        assert "severity" in df.columns

    def test_discrepancy_record_fields(self, tri):
        row = _row(entity_id="E1", atlas_system_present=True, length_aa=float("nan"))
        universe = pd.DataFrame([row.to_dict()])
        recs = tri.audit("E1", universe)
        assert len(recs) >= 1
        rec = recs[0]
        assert isinstance(rec, DiscrepancyRecord)
        assert rec.entity_id == "E1"
        assert rec.severity in ("high", "medium", "low")
