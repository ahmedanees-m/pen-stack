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


def _vehicle_of(delivery: str) -> str:
    """Map a delivery-rule label to a constraint-scan vehicle key (configs/delivery_constraints.yaml)."""
    d = (delivery or "").lower()
    if "aav" in d:
        return "AAV"
    if "lenti" in d:
        return "lentiviral"
    if "plasmid" in d:
        return "plasmid"
    return d # mRNA-RNP / LNP-mRNA -> no DNA-vector packaging checks


def recommend_delivery(effector_bp: int, cargo_bp: int, ct: str, cargo_seq: str | None = None) -> dict:
    """Return {delivery, total_bp, rationale}. effector_bp ~= writer length_aa * 3.

    When ``cargo_seq`` is supplied, attaches the WS-MC/MC2 delivery-vehicle sequence-constraint scan
    (vehicle-specific soft penalties + fixes) under ``delivery_constraints``.
    """
    cfg = _rules()
    total = int(effector_bp) + int(cargo_bp)
    chosen = None
    for rule in cfg["rules"]:
        if total <= rule["max_total_bp"]:
            chosen = {"delivery": rule["delivery"], "total_bp": total,
                      "rationale": f"total payload {total} bp <= {rule['max_total_bp']} bp"}
            break
    if chosen is None:
        fallback = (cfg["ex_vivo_fallback"] if ct in cfg.get("ex_vivo_cell_types", [])
                    else cfg["in_vivo_fallback"])
        chosen = {"delivery": fallback, "total_bp": total,
                  "rationale": f"total payload {total} bp exceeds dual-AAV; cell type {ct}"}
    if cargo_seq:
        from pen_stack.planner.delivery_constraints import scan_delivery
        chosen["delivery_constraints"] = scan_delivery(cargo_seq, _vehicle_of(chosen["delivery"]))
    return chosen
