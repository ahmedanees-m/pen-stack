"""Acquire / load the bridge-recombinase training data (Phase 1.5, Step 1.5.1).

Three tables supervise the engine: the measured **off-target profile** (per-position mismatch tolerance),
the **DMS** (variant→activity), and the **72-system human-cell activity screen**. The Perry 2025
supplementary (Science adz0276) is paywalled and not bulk-downloadable from the build environment; the
loaders below read the real tables when supplied, and otherwise fall back to the literature-grounded
position-weight profile (`configs/bridge_offtarget_profile.yaml`) so the engine runs end-to-end.

Outputs (when real tables are present): features/bridge_offtarget_profile.parquet, bridge_dms.parquet,
bridge_screen.parquet.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

_CFG = Path(__file__).resolve().parents[2] / "configs" / "bridge_offtarget_profile.yaml"


@lru_cache(maxsize=1)
def load_profile_config(path: str | Path = _CFG) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def protective_weights() -> dict[int, float]:
    """Per-position protective weight (1 = mismatch abolishes recombination; 0 = fully tolerated)."""
    cfg = load_profile_config()
    return {int(k): float(v) for k, v in cfg["protective_weight"].items()}


def load_offtarget_profile(supp_xlsx: str | Path | None = None, sheet: str | None = None) -> pd.DataFrame:
    """Measured off-target profile if supplied (cols: position, ref_base, alt_base, rel_recombination);
    else the literature-grounded position weights as a tidy frame (rel_recombination = 1 - weight)."""
    if supp_xlsx and Path(supp_xlsx).exists():
        return pd.read_excel(supp_xlsx, sheet_name=sheet)
    w = protective_weights()
    return pd.DataFrame({"position": list(w), "rel_recombination": [1 - v for v in w.values()],
                         "source": "literature_position_weights"})


def load_dms(supp_xlsx: str | Path | None = None, sheet: str | None = None) -> pd.DataFrame:
    """DMS variant→activity table (cols: aa_position, wt, mut, activity). Empty if the supp is absent."""
    if supp_xlsx and Path(supp_xlsx).exists():
        return pd.read_excel(supp_xlsx, sheet_name=sheet)
    return pd.DataFrame(columns=["aa_position", "wt", "mut", "activity"])


def load_screen(supp_csv: str | Path | None = None) -> pd.DataFrame:
    """72-system activity screen (cols: system_id, family, human_cell_activity, target_core). Empty if absent."""
    if supp_csv and Path(supp_csv).exists():
        return pd.read_csv(supp_csv)
    return pd.DataFrame(columns=["system_id", "family", "human_cell_activity", "target_core"])
