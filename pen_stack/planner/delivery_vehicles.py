"""Delivery-vehicle palette loader (Phase 3.3, WS-D). Reads configs/delivery_vehicles.yaml (>=6 vehicles:
AAV single/dual, lentivirus, helper-dependent adenovirus, HSV amplicon, LNP-mRNA, eVLP, electroporation).
Replaces the single dual-AAV assumption with a queryable palette the rule engine constrains."""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource


@lru_cache(maxsize=1)
def load_vehicles(path=None) -> dict:
    p = resource("configs/delivery_vehicles.yaml") if path is None else path
    return yaml.safe_load(open(p, encoding="utf-8").read())["vehicles"]


def vehicle(name: str) -> dict | None:
    """Vehicle record by name (case-insensitive; tolerant of aliases like 'aav'->AAV_single, 'lvv')."""
    if not name:
        return None
    veh = load_vehicles()
    if name in veh:
        return veh[name]
    low = name.lower()
    alias = {"aav": "AAV_single", "aav_single": "AAV_single", "dual_aav": "AAV_dual",
             "aav_dual": "AAV_dual", "lvv": "lentivirus", "lenti": "lentivirus",
             "hdad": "helper_dependent_adenovirus", "hsv": "hsv_amplicon",
             "lnp": "lnp_mrna", "mrna": "lnp_mrna", "vlp": "evlp", "ep": "electroporation",
             "nucleofection": "electroporation"}
    key = alias.get(low) or next((k for k in veh if k.lower() == low), None)
    return veh.get(key) if key else None


def names() -> list[str]:
    return list(load_vehicles().keys())
