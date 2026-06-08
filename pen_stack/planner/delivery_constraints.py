"""Delivery-vehicle sequence constraints (Phase 3.2, WS-MC / MC2).

Cargo Polish scans WHAT is written for silencing triggers; this scans the construct for VEHICLE-specific
sequence problems that hurt the chosen delivery vector: lentiviral internal poly(A) signals (truncate the
genomic RNA), AAV ITR-interfering inverted repeats / homopolymer slippage, recombinogenic direct repeats,
and packaging-hostile GC extremes. Output is a soft ``delivery_constraint_risk`` in [0,1] with a band and a
concrete fix per flag.

These are LABELED HEURISTIC penalties (config: configs/delivery_constraints.yaml), validated only
directionally — a construct carrying a known problematic element scores higher than a clean one — not a
predictor of titre. Vehicles that deliver the effector as RNA/protein (mRNA-RNP, LNP-mRNA) have no DNA-vector
packaging constraints on the cargo here.
"""
from __future__ import annotations

import re
from functools import lru_cache

import yaml

from pen_stack._resources import resource


@lru_cache(maxsize=1)
def _cfg() -> dict:
    return yaml.safe_load(resource("configs/delivery_constraints.yaml").read_text(encoding="utf-8"))


def _clean(seq: str) -> str:
    return re.sub(r"[^ACGT]", "", (seq or "").upper())


def _rc(s: str) -> str:
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def _gc(s: str) -> float:
    return (s.count("G") + s.count("C")) / len(s) if s else 0.0


def _longest_homopolymer(s: str) -> int:
    best = run = 1
    for i in range(1, len(s)):
        run = run + 1 if s[i] == s[i - 1] else 1
        best = max(best, run)
    return best if s else 0


def _has_direct_repeat(s: str, unit: int) -> bool:
    """A >= `unit`-nt substring that occurs at least twice (non-overlapping-ish) → recombinogenic direct repeat."""
    seen = {}
    for i in range(len(s) - unit + 1):
        sub = s[i:i + unit]
        if sub in seen and i - seen[sub] >= unit:
            return True
        seen.setdefault(sub, i)
    return False


def _has_inverted_repeat(s: str, arm: int) -> bool:
    """A >= `arm`-nt substring whose reverse-complement also occurs → hairpin / ITR-like inverted repeat."""
    kmers = {s[i:i + arm] for i in range(len(s) - arm + 1)}
    for i in range(len(s) - arm + 1):
        if _rc(s[i:i + arm]) in kmers:
            return True
    return False


def scan_delivery(seq: str, vehicle: str) -> dict:
    """Vehicle-specific construct scan → soft risk + per-flag suggestions. Unknown/RNA vehicles → no checks."""
    cfg = _cfg()
    s = _clean(seq)
    checks = cfg["vehicles"].get(vehicle, [])
    flags, risk = [], 0.0

    for name in checks:
        c = cfg["checks"][name]
        if name == "internal_polyA":
            n = len(re.findall(c["pattern"], s))
            if n:
                risk += min(c["cap"], c["risk_per_hit"] * n)
                flags.append({"check": name, "detail": f"{n} internal poly(A) signal(s)",
                              "suggestion": c["suggestion"]})
        elif name == "homopolymer_run":
            if _longest_homopolymer(s) >= c["min_len"]:
                risk += c["risk_per_run"]
                flags.append({"check": name, "detail": f"homopolymer run >= {c['min_len']} nt",
                              "suggestion": c["suggestion"]})
        elif name == "direct_repeat":
            if _has_direct_repeat(s, c["unit_len"]):
                risk += c["risk"]
                flags.append({"check": name, "detail": f">= {c['unit_len']} nt direct repeat",
                              "suggestion": c["suggestion"]})
        elif name == "inverted_repeat":
            if _has_inverted_repeat(s, c["arm_len"]):
                risk += c["risk"]
                flags.append({"check": name, "detail": f">= {c['arm_len']} nt inverted repeat (hairpin)",
                              "suggestion": c["suggestion"]})
        elif name == "gc_extreme":
            gc = _gc(s)
            if s and (gc < c["gc_low"] or gc > c["gc_high"]):
                risk += c["risk"]
                flags.append({"check": name, "detail": f"GC={gc:.2f}", "suggestion": c["suggestion"]})

    risk = round(min(1.0, risk), 4)
    b = cfg["bands"]
    band = "low" if risk < b["low"] else ("moderate" if risk < b["moderate"] else "high")
    return {"vehicle": vehicle, "delivery_constraint_risk": risk, "band": band,
            "checks_applied": checks, "n_flags": len(flags), "flags": flags,
            "scope": "labeled heuristic vehicle-packaging penalties (directional), not a titre predictor"}
