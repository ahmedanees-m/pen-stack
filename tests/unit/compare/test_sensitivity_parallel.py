"""Tests for sensitivity.run_sensitivity_parallel."""

import pandas as pd

from pen_stack.compare.sensitivity import run_sensitivity_parallel


def _make_frames():
    universe = pd.DataFrame(
        [
            {
                "entity_id": "ISCro4",
                "source": "natural",
                "s_dsb": 1.0,
                "s_prog": 1.0,
                "s_cargo": 1.0,
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


class TestRunSensitivityParallel:
    def test_returns_dataframe(self):
        u, s = _make_frames()
        small_grid = {
            "g1_threshold": [0.90],
            "g2_threshold": [0.90],
            "g3_threshold": [0.85],
            "g4_size_max": [900],
        }
        df = run_sensitivity_parallel(u, s, n_jobs=1, grid=small_grid)
        assert isinstance(df, pd.DataFrame)

    def test_one_row_per_entity(self):
        u, s = _make_frames()
        small_grid = {
            "g1_threshold": [0.90],
            "g2_threshold": [0.90],
            "g3_threshold": [0.85],
            "g4_size_max": [900],
        }
        df = run_sensitivity_parallel(u, s, n_jobs=1, grid=small_grid)
        assert len(df) == 1
        assert df.iloc[0]["entity_id"] == "ISCro4"

    def test_has_robustness_column(self):
        u, s = _make_frames()
        small_grid = {
            "g1_threshold": [0.90],
            "g2_threshold": [0.90],
            "g3_threshold": [0.85],
            "g4_size_max": [900],
        }
        df = run_sensitivity_parallel(u, s, n_jobs=1, grid=small_grid)
        assert "robustness" in df.columns
