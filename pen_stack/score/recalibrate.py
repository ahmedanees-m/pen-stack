"""Re-ground the scoring axes (Phase 0, Step 0.3).

The prior `prog`/`cargo` axes were effectively hand-set flags (`s_prog=1.0` for everything) that
required per-enzyme overrides to pass any gate. Here each axis is a documented, continuous function
of a *measured* input read from ``configs/score_axes.yaml``. There are NO per-enzyme override
constants in this module - that invariant is checked by ``tests/unit/test_no_overrides.py``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_CFG_PATH = Path(__file__).resolve().parents[2] / "configs" / "score_axes.yaml"


def load_axes_config(path: str | Path = _CFG_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def recalibrate_cargo(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """S_Cargo from measured cargo bp (monotone); fall back to upstream s_cargo if bp unknown."""
    cap = float(cfg["cargo"]["cap_bp"])
    out = df.copy()
    if "cargo_capacity_bp" in out.columns:
        bp = out["cargo_capacity_bp"].astype("float64").clip(0, cap)
        recal = np.log1p(bp) / np.log1p(cap)
        # only override where we actually have a measured bp; otherwise keep upstream s_cargo
        out["S_Cargo"] = np.where(bp.notna() & (bp > 0), recal, out.get("s_cargo"))
    else:
        out["S_Cargo"] = out.get("s_cargo")
    return out


def recalibrate_prog(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """S_Prog from MEASURED targeting modality (documented anchors), not a 0/1 flag."""
    p = cfg["programmability"]
    anchor = p["modality_anchor"]
    bip_fams = set(p.get("bipartite_reprogrammable_families", []))
    bonus = float(p.get("bipartite_bonus_to", 1.0))

    def _prog(row) -> float:
        fam = row.get("family")
        if fam in bip_fams:
            return bonus
        modality = row.get("targeting_modality")
        if modality in anchor:
            return float(anchor[modality])
        # fall back to upstream s_prog if no modality info (documented degradation, not an override)
        return float(row["s_prog"]) if pd.notna(row.get("s_prog")) else np.nan

    out = df.copy()
    out["S_Prog"] = out.apply(_prog, axis=1)
    return out


def backfill_length(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Backfill length_aa from independently-verified UniProt lengths (upstream has all None)."""
    table = cfg["length_aa_backfill"]
    out = df.copy()
    key = "entity_id" if "entity_id" in out.columns else "representative_system"
    filled = out["length_aa"] if "length_aa" in out.columns else pd.Series([None] * len(out))
    out["length_aa"] = [
        (table.get(k) if (pd.isna(v) or v is None) else v)
        for k, v in zip(out[key], filled)
    ]
    return out


def recalibrate_all(df: pd.DataFrame, cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_axes_config()
    out = backfill_length(df, cfg)
    out = recalibrate_cargo(out, cfg)
    out = recalibrate_prog(out, cfg)
    return out
