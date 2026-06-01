"""Canonical universe assembly (Phase 0, Step 0.4).

THE single entry point that joins the upstream editor universe + the WT-KB + the crosswalk and
applies the re-grounded axes. The classifier, the scorer, and the scorecard must all consume the
output of ``assemble()`` — never re-derive metadata independently (the prior PEN-DISCOVER vs
PEN-COMPARE gate inconsistency must not recur). Cross-module consistency is asserted by
``tests/unit/test_universe_consistency.py``.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from pen_stack.score.recalibrate import load_axes_config, recalibrate_all

_ROOT = Path(__file__).resolve().parents[2]
_UNIVERSE = _ROOT / "data" / "curated" / "unified_editor_universe.parquet"
_WTKB = _ROOT / "pen_stack" / "atlas" / "wtkb.parquet"
_CROSSWALK = _ROOT / "configs" / "universe_crosswalk.yaml"


def _load_crosswalk(path: Path = _CROSSWALK) -> pd.DataFrame:
    cw = yaml.safe_load(path.read_text(encoding="utf-8"))["entity_to_family"]
    return pd.DataFrame(
        [{"entity_id": k, "family": v["family"], "targeting_modality": v["targeting_modality"]}
         for k, v in cw.items()]
    )


def assemble(
    universe_parquet: str | Path = _UNIVERSE,
    wtkb_parquet: str | Path = _WTKB,
    crosswalk_path: str | Path = _CROSSWALK,
    out_parquet: str | Path | None = None,
) -> pd.DataFrame:
    uni = pd.read_parquet(universe_parquet)
    wt = pd.read_parquet(wtkb_parquet)
    cw = _load_crosswalk(Path(crosswalk_path))

    # 1) attach family + modality to natural editors via the crosswalk
    uni = uni.merge(cw, on="entity_id", how="left")

    # 2) designs inherit their parent_editor's family + modality
    if "parent_editor" in uni.columns:
        parent_map = cw.set_index("entity_id")[["family", "targeting_modality"]]
        need = uni["family"].isna() & uni["parent_editor"].notna()
        for col in ("family", "targeting_modality"):
            uni.loc[need, col] = uni.loc[need, "parent_editor"].map(parent_map[col])

    # 3) bring WT-KB measured fields (cargo bp, reachability tier, dsb_free) in by family — single source
    wt_fields = wt[["family", "cargo_capacity_bp", "reachability_tier", "dsb_free"]].drop_duplicates("family")
    uni = uni.merge(wt_fields, on="family", how="left")

    # 4) apply the re-grounded axes (length backfill + cargo + prog); NO per-enzyme overrides
    uni = recalibrate_all(uni, load_axes_config())

    if out_parquet:
        Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
        uni.to_parquet(out_parquet, index=False)
    return uni


# Axis/gate inputs that every downstream module must read from the canonical universe (not re-derive).
CANONICAL_INPUTS = [
    "entity_id", "source", "mechanism_class", "s_dsb", "S_Prog", "S_Cargo",
    "length_aa", "intrinsic_cargo_mechanism", "cell_based_evidence",
    "family", "targeting_modality", "reachability_tier",
]


def canonical_inputs(df: pd.DataFrame) -> pd.DataFrame:
    """The exact metadata slice the classifier/scorer/scorecard must share."""
    return df[[c for c in CANONICAL_INPUTS if c in df.columns]].copy()
