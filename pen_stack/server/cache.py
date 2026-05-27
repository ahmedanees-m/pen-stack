"""Build JSON caches from parquets for Streamlit Community Cloud cold-start."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"
_SC = (
    Path(__file__).resolve().parent.parent.parent / "results" / "truewriter_scorecard_v3.2.parquet"
)
_UN = Path(__file__).resolve().parent.parent.parent / "data" / "unified_editor_universe.parquet"
_DI = (
    Path(__file__).resolve().parent.parent.parent
    / "results"
    / "triangulation_discrepancies.parquet"
)


def build_caches() -> dict[str, int]:
    """Build all JSON caches from parquets. Returns {filename: bytes} mapping."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    written: dict[str, int] = {}

    scorecard = pd.read_parquet(_SC)
    universe = pd.read_parquet(_UN)
    disc = pd.read_parquet(_DI)

    def _write(name: str, data: str) -> None:
        p = CACHE_DIR / name
        p.write_text(data)
        written[name] = p.stat().st_size

    # 1. Tier distribution
    _write(
        "tier_distribution.json", json.dumps(scorecard["tier"].value_counts().to_dict(), indent=2)
    )

    # 2. Full scorecard
    _write("scorecard.json", scorecard.to_json(orient="records"))

    # 3. Natural editors merged with scorecard
    sc_cols = [
        "entity_id",
        "tier",
        "qualifying_passed",
        "has_cell_based",
        "g1_dsb_passes",
        "g2_prog_passes",
        "g3_cargo_passes",
        "g4_size_passes",
        "g5_evidence_passes",
    ]
    sc_avail = [c for c in sc_cols if c in scorecard.columns]
    nat_un = universe[universe["source"] == "natural"].copy()
    nat_merged = nat_un.merge(scorecard[sc_avail], on="entity_id", how="left")
    _write("universe_natural.json", nat_merged.to_json(orient="records"))

    # 4. TRUE_WRITER list
    tw = scorecard[scorecard["tier"] == "TRUE_WRITER"]
    _write("true_writers.json", tw.to_json(orient="records"))

    # 5. Triangulation discrepancies
    _write("triangulation_discrepancies.json", disc.to_json(orient="records"))

    # 6. Summary
    summary = {
        "n_entities": int(len(scorecard)),
        "n_natural": int((scorecard["source"] == "natural").sum()),
        "n_designs": int((scorecard["source"] == "design").sum()),
        "tier_distribution": scorecard["tier"].value_counts().to_dict(),
        "n_discrepancies": int(len(disc)),
    }
    _write("summary.json", json.dumps(summary, indent=2))

    return written
