"""Unit tests for pen_stack.server.cache.build_caches.

Uses tmp_path to avoid needing real parquets on disk.
Patches module-level Path constants before importing.
"""

import json
import sys

import pandas as pd
import pytest

# ── fixture helpers ───────────────────────────────────────────────────────────


def _scorecard():
    return pd.DataFrame(
        [
            {
                "entity_id": "ISCro4",
                "source": "natural",
                "tier": "TRUE_WRITER",
                "qualifying_passed": 4,
                "has_cell_based": True,
                "g1_dsb_passes": True,
                "g2_prog_passes": True,
                "g3_cargo_passes": True,
                "g4_size_passes": True,
                "g5_evidence_passes": True,
            },
            {
                "entity_id": "IS621",
                "source": "natural",
                "tier": "PROBABLE_WRITER",
                "qualifying_passed": 3,
                "has_cell_based": False,
                "g1_dsb_passes": True,
                "g2_prog_passes": True,
                "g3_cargo_passes": True,
                "g4_size_passes": True,
                "g5_evidence_passes": False,
            },
            {
                "entity_id": "Design1",
                "source": "design",
                "tier": "EMERGING_WRITER",
                "qualifying_passed": 2,
                "has_cell_based": False,
                "g1_dsb_passes": True,
                "g2_prog_passes": True,
                "g3_cargo_passes": False,
                "g4_size_passes": False,
                "g5_evidence_passes": False,
            },
        ]
    )


def _universe():
    return pd.DataFrame(
        [
            {"entity_id": "ISCro4", "source": "natural", "s_dsb": 1.0, "length_aa": 326.0},
            {"entity_id": "IS621", "source": "natural", "s_dsb": 1.0, "length_aa": 342.0},
            {"entity_id": "Design1", "source": "design", "s_dsb": 0.9, "length_aa": 400.0},
        ]
    )


def _discrepancies():
    return pd.DataFrame(
        [
            {
                "entity_id": "IS621",
                "source": "natural",
                "category": "EVIDENCE_GAP",
                "severity": "low",
                "sources_involved": "MECH_CLASS|PEN_SCORE",
                "details": "...",
            },
        ]
    )


@pytest.fixture
def cache_env(tmp_path, monkeypatch):
    """Wire up tmp_path parquet files and redirect CACHE_DIR."""
    sc = _scorecard()
    un = _universe()
    di = _discrepancies()

    sc_path = tmp_path / "truewriter_scorecard_v3.2.parquet"
    un_path = tmp_path / "unified_editor_universe.parquet"
    di_path = tmp_path / "triangulation_discrepancies.parquet"
    cache_dir = tmp_path / "cache"

    sc.to_parquet(sc_path)
    un.to_parquet(un_path)
    di.to_parquet(di_path)

    # Patch module constants before importing (or reload if already imported)
    mod_name = "pen_stack.server.cache"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    import pen_stack.server.cache as cache_mod

    monkeypatch.setattr(cache_mod, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(cache_mod, "_SC", sc_path)
    monkeypatch.setattr(cache_mod, "_UN", un_path)
    monkeypatch.setattr(cache_mod, "_DI", di_path)

    return cache_mod, cache_dir


# ── build_caches tests ────────────────────────────────────────────────────────


class TestBuildCaches:
    def test_returns_dict_with_all_files(self, cache_env):
        cache_mod, _ = cache_env
        result = cache_mod.build_caches()
        expected = {
            "tier_distribution.json",
            "scorecard.json",
            "universe_natural.json",
            "true_writers.json",
            "triangulation_discrepancies.json",
            "summary.json",
        }
        assert set(result.keys()) == expected

    def test_returns_positive_byte_counts(self, cache_env):
        cache_mod, _ = cache_env
        result = cache_mod.build_caches()
        for name, size in result.items():
            assert size > 0, f"{name} has zero bytes"

    def test_creates_cache_dir(self, cache_env):
        cache_mod, cache_dir = cache_env
        assert not cache_dir.exists()
        cache_mod.build_caches()
        assert cache_dir.exists()

    def test_tier_distribution_valid_json(self, cache_env):
        cache_mod, cache_dir = cache_env
        cache_mod.build_caches()
        data = json.loads((cache_dir / "tier_distribution.json").read_text())
        assert isinstance(data, dict)
        assert "TRUE_WRITER" in data
        assert data["TRUE_WRITER"] == 1

    def test_scorecard_valid_json_records(self, cache_env):
        cache_mod, cache_dir = cache_env
        cache_mod.build_caches()
        records = json.loads((cache_dir / "scorecard.json").read_text())
        assert isinstance(records, list)
        assert len(records) == 3

    def test_universe_natural_only_natural_rows(self, cache_env):
        cache_mod, cache_dir = cache_env
        cache_mod.build_caches()
        records = json.loads((cache_dir / "universe_natural.json").read_text())
        assert all(r.get("source") == "natural" for r in records)
        assert len(records) == 2

    def test_true_writers_only_true_writer_rows(self, cache_env):
        cache_mod, cache_dir = cache_env
        cache_mod.build_caches()
        records = json.loads((cache_dir / "true_writers.json").read_text())
        assert len(records) == 1
        assert records[0]["entity_id"] == "ISCro4"

    def test_triangulation_discrepancies_json(self, cache_env):
        cache_mod, cache_dir = cache_env
        cache_mod.build_caches()
        records = json.loads((cache_dir / "triangulation_discrepancies.json").read_text())
        assert isinstance(records, list)
        assert len(records) == 1
        assert records[0]["entity_id"] == "IS621"

    def test_summary_fields(self, cache_env):
        cache_mod, cache_dir = cache_env
        cache_mod.build_caches()
        data = json.loads((cache_dir / "summary.json").read_text())
        assert data["n_entities"] == 3
        assert data["n_natural"] == 2
        assert data["n_designs"] == 1
        assert data["n_discrepancies"] == 1

    def test_idempotent_second_call(self, cache_env):
        cache_mod, cache_dir = cache_env
        r1 = cache_mod.build_caches()
        r2 = cache_mod.build_caches()
        assert r1.keys() == r2.keys()
