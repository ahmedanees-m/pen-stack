"""Load the rule base from configs/rules/*.yaml into a validated Ruleset (Phase 3.3, WS-R)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from pen_stack._resources import resource
from pen_stack.rules.schema import Rule, Ruleset

RULES_VERSION = "1.0"
_CATEGORIES = ("reachability", "fold", "payload", "multiplex", "delivery", "compliance")


@lru_cache(maxsize=1)
def load_ruleset(rules_dir: str | None = None) -> Ruleset:
    base = Path(rules_dir) if rules_dir else resource("configs/rules")
    rules: list[Rule] = []
    for cat in _CATEGORIES:
        f = base / f"{cat}.yaml"
        if not f.exists():
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for rec in data.get("rules", []):
            rules.append(Rule(**rec))
    ids = [r.id for r in rules]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate rule ids: {sorted(dupes)}")
    return Ruleset(version=RULES_VERSION, rules=rules)
