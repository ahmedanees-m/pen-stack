"""Unit tests for pen_compare.core.sensitivity."""

import pandas as pd

from pen_stack.compare.core.sensitivity import (
    SENSITIVITY_GRID,
    build_sensitivity_rows,
    sensitivity_for_entity,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _row(
    entity_id="X",
    source="natural",
    default_tier="TRUE_WRITER",
    s_dsb=1.0,
    s_prog=1.0,
    s_cargo=1.0,
    length_aa_int=300,
    evidence_sources=None,
    intrinsic_cargo_mechanism=True,
    split_aav_eligible=True,
):
    if evidence_sources is None:
        evidence_sources = ["biochemical", "structural", "computational", "cell_based"]
    return dict(
        entity_id=entity_id,
        source=source,
        default_tier=default_tier,
        s_dsb=s_dsb,
        s_prog=s_prog,
        s_cargo=s_cargo,
        length_aa_int=length_aa_int,
        evidence_sources=evidence_sources,
        intrinsic_cargo_mechanism=intrinsic_cargo_mechanism,
        split_aav_eligible=split_aav_eligible,
    )


# ── sensitivity_for_entity ────────────────────────────────────────────────────


class TestSensitivityForEntity:
    def test_returns_required_keys(self):
        r = sensitivity_for_entity(_row())
        for key in (
            "entity_id",
            "source",
            "default_tier",
            "modal_tier",
            "robustness",
            "n_combos",
            "tier_dist",
            "is_robust",
            "is_boundary",
        ):
            assert key in r

    def test_iscro4_modal_is_true_writer(self):
        # All scores well above all thresholds in grid → modal tier is TRUE_WRITER
        row = _row(entity_id="ISCro4", s_dsb=1.0, s_prog=1.0, s_cargo=1.0)
        r = sensitivity_for_entity(row)
        assert r["modal_tier"] == "TRUE_WRITER"
        assert r["robustness"] == 1.0
        assert r["is_boundary"] is False

    def test_n_combos_matches_grid(self):
        import itertools

        expected = len(list(itertools.product(*SENSITIVITY_GRID.values())))
        r = sensitivity_for_entity(_row())
        assert r["n_combos"] == expected

    def test_not_writer_entity_robustness(self):
        row = _row(
            entity_id="SpCas9",
            source="natural",
            default_tier="NOT_WRITER",
            s_dsb=0.0,
            s_prog=0.0,
            s_cargo=0.0,
            evidence_sources=[],
            intrinsic_cargo_mechanism=False,
        )
        r = sensitivity_for_entity(row)
        assert r["modal_tier"] == "NOT_WRITER"
        assert r["robustness"] == 1.0

    def test_small_grid(self):
        small_grid = {
            "g1_threshold": [0.90],
            "g2_threshold": [0.90],
            "g3_threshold": [0.85],
            "g4_size_max": [900],
        }
        r = sensitivity_for_entity(_row(), grid=small_grid)
        assert r["n_combos"] == 1
        assert 0.0 <= r["robustness"] <= 1.0

    def test_robustness_fraction_in_range(self):
        r = sensitivity_for_entity(_row())
        assert 0.0 <= r["robustness"] <= 1.0

    def test_is_robust_true_when_robustness_above_80(self):
        r = sensitivity_for_entity(_row())
        assert r["is_robust"] == (r["robustness"] >= 0.80)

    def test_is_boundary_false_when_high_robustness(self):
        r = sensitivity_for_entity(_row(s_dsb=1.0))
        assert r["is_boundary"] is False


# ── build_sensitivity_rows ────────────────────────────────────────────────────


class TestBuildSensitivityRows:
    def _make_frames(self):
        universe = pd.DataFrame(
            [
                {
                    "entity_id": "ISCro4",
                    "source": "natural",
                    "s_dsb": 1.0,
                    "s_prog": 0.9997,
                    "s_cargo": 0.9862,
                    "length_aa": 326.0,
                    "intrinsic_cargo_mechanism": True,
                    "has_biochemical": True,
                    "has_structural": True,
                    "has_computational": True,
                    "has_cell_based": True,
                }
            ]
        )
        scorecard = pd.DataFrame(
            [
                {
                    "entity_id": "ISCro4",
                    "source": "natural",
                    "tier": "TRUE_WRITER",
                }
            ]
        )
        return universe, scorecard

    def test_returns_list_of_dicts(self):
        u, s = self._make_frames()
        rows = build_sensitivity_rows(u, s)
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert isinstance(rows[0], dict)

    def test_evidence_sources_built_correctly(self):
        u, s = self._make_frames()
        rows = build_sensitivity_rows(u, s)
        assert "cell_based" in rows[0]["evidence_sources"]
        assert "biochemical" in rows[0]["evidence_sources"]

    def test_length_aa_null_falls_back_to_450(self):
        u, s = self._make_frames()
        u["length_aa"] = float("nan")
        rows = build_sensitivity_rows(u, s)
        assert rows[0]["length_aa_int"] == 450

    def test_default_tier_from_scorecard(self):
        u, s = self._make_frames()
        rows = build_sensitivity_rows(u, s)
        assert rows[0]["default_tier"] == "TRUE_WRITER"

    def test_no_cell_based_column_collision(self):
        # universe has has_cell_based; after build_sensitivity_rows it must appear in evidence
        u, s = self._make_frames()
        u["has_cell_based"] = True
        rows = build_sensitivity_rows(u, s)
        assert "cell_based" in rows[0]["evidence_sources"]
