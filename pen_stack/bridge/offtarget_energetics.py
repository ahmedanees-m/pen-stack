"""Mechanistic off-target energetics model (Phase 3.2, WS-MC / MC3), GATED on beating 0.77.

The shipped off-target ranker (`bridge/offtarget.py`) scores a pseudosite by a POSITION-only protective
weight: ``risk = prod(1 - weight[mismatched position])``. It ignores *which* substitution a mismatch is, but
a bridge-RNA:target duplex is a base-pairing interaction, so the thermodynamic cost of a mismatch depends on
its identity (a G:T wobble is tolerated; a C:C clash is not), not only its position. This module adds that:
a per-(position, substitution) **penalty** learned from the measured off-target frequencies, a mismatch type
seen often among recombining off-targets is tolerated (low penalty), a rare one is costly (high penalty).

``energetic_risk`` sums the penalties over the mismatched positions (a log-additive binding-energy proxy) and
maps to a 0-1 risk. This is the only place v3.2 *adds* mechanism to a model rather than just wrapping it, and
per WS-MC discipline it **ships only if it beats the current 0.77 held-out AUROC** on a leakage-safe train/test
split (penalties fit on train, evaluated on held-out test). If it does not, it is reported as a negative and
the position-weight model stays the default. No mechanism is added that does not earn its place empirically.
"""
from __future__ import annotations

import math
from collections import defaultdict

_BASES = "ACGT"


def fit_penalties(pairs, core_len: int = 14, alpha: float = 1.0) -> dict:
    """Learn per-(position, ref→alt) mismatch penalties from recombining off-targets.

    ``pairs`` = iterable of (offtarget_seq, intended_seq) that DID recombine. For each position, count how
    often each substitution (intended base → observed base) appears; a frequent substitution is tolerated, so
    its penalty is low. penalty = -log((count + alpha) / (matches_at_pos + alpha * 12)). Matches (no mismatch)
    anchor the per-position scale. Returns {"pen": {(pos, ref, alt): penalty}, "pos_match": {...}}.
    """
    sub_count = defaultdict(int) # (pos, ref, alt) -> count of that mismatch among off-targets
    match_count = defaultdict(int) # pos -> count of positions left matched
    for off, intended in pairs:
        if len(off) < core_len or len(intended) < core_len:
            continue
        for p in range(core_len):
            ref, alt = intended[p], off[p]
            if ref not in _BASES or alt not in _BASES:
                continue
            if ref == alt:
                match_count[p] += 1
            else:
                sub_count[(p, ref, alt)] += 1
    pen = {}
    for p in range(core_len):
        denom = match_count[p] + alpha * 12 # 12 = the off-diagonal substitution types
        for ref in _BASES:
            for alt in _BASES:
                if ref == alt:
                    continue
                c = sub_count[(p, ref, alt)]
                pen[(p, ref, alt)] = -math.log((c + alpha) / denom)
    return {"pen": pen, "core_len": core_len,
            "max_pen": max(pen.values()) if pen else 1.0}


def energetic_penalty(off: str, intended: str, model: dict) -> float:
    """Total binding-energy penalty (sum over mismatched positions). Higher = less likely to recombine."""
    pen, L = model["pen"], model["core_len"]
    miss = model["max_pen"]
    total = 0.0
    for p in range(min(L, len(off), len(intended))):
        ref, alt = intended[p], off[p]
        if ref != alt:
            total += pen.get((p, ref, alt), miss)
    return total


def energetic_risk(off: str, intended: str, model: dict) -> float:
    """0-1 recombination risk: high when the total mismatch penalty is low (a perfect match → ~1.0)."""
    total = energetic_penalty(off, intended, model)
    return float(math.exp(-total))


# --- serialization: the fitted penalty table is a DERIVED statistical summary (like the measured position
# profile), committable as data/curated/bridge_offtarget_energetics.json so the model runs without raw data ---
def to_json(model: dict) -> dict:
    """Encode the tuple-keyed penalty table as nested JSON {pos: {ref+alt: penalty}}."""
    nested: dict = {}
    for (p, ref, alt), v in model["pen"].items():
        nested.setdefault(str(p), {})[ref + alt] = round(v, 6)
    return {"core_len": model["core_len"], "max_pen": round(model["max_pen"], 6), "pen": nested}


def from_json(d: dict) -> dict:
    pen = {}
    for p, subs in d["pen"].items():
        for ra, v in subs.items():
            pen[(int(p), ra[0], ra[1])] = float(v)
    return {"pen": pen, "core_len": int(d["core_len"]), "max_pen": float(d["max_pen"])}


def load_penalties(path=None) -> dict | None:
    """Load the committed production penalty table (fit on all measured off-targets), or None if absent."""
    import json
    from pathlib import Path
    if path is None:
        try:
            from pen_stack._resources import resource
            path = resource("data/curated/bridge_offtarget_energetics.json")
        except Exception: # noqa: BLE001 - not present in a bare wheel
            return None
    p = Path(path)
    return from_json(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else None
