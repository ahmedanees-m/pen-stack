"""Deterministic, version-pinned oracle cache + scope-card loader (v4.0, WS-O).

Every oracle call is keyed on (oracle family, model, version, canonicalised inputs) so a cached round-trip
reproduces committed values offline, the substrate's *core stays runnable from cache* even when a heavy
oracle backend (AF3, Evo2, ESM3) is not installed (the v4.0 compute policy). Cache entries are plain JSON
under `oracle_cache/` (committed for offline CI).
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from pen_stack._resources import project_root

_CACHE_DIR = project_root() / "oracle_cache"


def scope_cards_path() -> Path:
    from pen_stack._resources import resource
    return resource("configs/oracles/scope_cards.yaml")


@lru_cache(maxsize=1)
def load_scope_cards() -> dict:
    return yaml.safe_load(scope_cards_path().read_text(encoding="utf-8"))["oracles"]


def scope_card(model: str) -> dict | None:
    return load_scope_cards().get(model)


def cache_key(oracle: str, model: str, version: str, inputs: dict[str, Any]) -> str:
    """A stable key over the oracle family, the pinned model+version, and canonicalised inputs."""
    payload = json.dumps({"oracle": oracle, "model": model, "version": version, "inputs": inputs},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def cache_get(key: str) -> dict | None:
    p = _CACHE_DIR / f"{key}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def cache_put(key: str, value: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_CACHE_DIR / f"{key}.json").write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")
