"""Delivery recommendation (Phase 3, Step 3.3).

Recommend a delivery modality from the total payload (writer effector + cargo) and the target cell type,
using the documented rule table in configs/delivery_rules.yaml (no hidden constants).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_CFG = Path(__file__).resolve().parents[2] / "configs" / "delivery_rules.yaml"


@lru_cache(maxsize=1)
def _rules(path: str | Path = _CFG) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def recommend_delivery(effector_bp: int, cargo_bp: int, ct: str) -> dict:
    """Return {delivery, total_bp, rationale}. effector_bp ~= writer length_aa * 3."""
    cfg = _rules()
    total = int(effector_bp) + int(cargo_bp)
    for rule in cfg["rules"]:
        if total <= rule["max_total_bp"]:
            return {"delivery": rule["delivery"], "total_bp": total,
                    "rationale": f"total payload {total} bp <= {rule['max_total_bp']} bp"}
    fallback = (cfg["ex_vivo_fallback"] if ct in cfg.get("ex_vivo_cell_types", [])
                else cfg["in_vivo_fallback"])
    return {"delivery": fallback, "total_bp": total,
            "rationale": f"total payload {total} bp exceeds dual-AAV; cell type {ct}"}
