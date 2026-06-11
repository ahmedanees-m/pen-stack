"""Anti-PEG immunity axis for PEGylated LNP (v5.6, WS-PEG).

The one delivery-immunology axis missing from v5.1-v5.5: pre-existing / induced anti-PEG antibodies, which
gate RE-DOSING of PEGylated LNP. Anti-PEG is a property of the PEGylation chemistry, not of any encoded
sequence — so, exactly like the v5.5 anti-vector seroprevalence oracle, it is grounded in published serosurvey
DATA (configs/antipeg.yaml, a population prevalence range with DOIs):

    preexisting_antipeg_score = 1 - midpoint(anti_PEG_prevalence_pct) / 100    # 1 = fewest excluded

Answers through the v4.0 OracleResult contract (output_kind="baseline"). ABSTAINS for non-PEGylated vehicles.
HONESTY: a POPULATION prevalence (a range, region/age/assay-dependent), NOT a given patient's anti-PEG titer
(a clinical test, patient-specific -> a known-unknown); induced anti-PEG after dose 1 is a separate, larger
dynamic (noted, not modelled).
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource
from pen_stack.oracles.schema import OracleResult, Provenance

_SCOPE_CARD = "antipeg"


@lru_cache(maxsize=1)
def _table() -> dict:
    return yaml.safe_load(resource("configs/antipeg.yaml").read_text(encoding="utf-8"))


def _all_dois() -> list[str]:
    return list((_table().get("prevalence") or {}).get("dois", []) or [])


def _prov(**extra) -> Provenance:
    return Provenance(model="anti_peg_seroprevalence", version=str(_table().get("version", "1.0")),
                      source="cache", extra=extra)


def antipeg_oracle(vehicle_name: str, pegylated: bool | None = None) -> OracleResult:
    """Anti-PEG pre-existing immunity for a vehicle, as an OracleResult (v4.0 contract).

    - PEGylated vehicle -> preexisting_antipeg_score = 1 - midpoint(prevalence)/100 (gates RE-DOSING).
    - non-PEGylated vehicle -> ABSTAINS (available=False, value=None): the anti-PEG axis is not applicable.
    `pegylated` overrides the config's vehicle list when given. Never fabricates a patient titer."""
    t = _table()
    is_peg = pegylated if pegylated is not None else (vehicle_name in (t.get("pegylated_vehicles") or []))
    if not is_peg:
        return OracleResult(oracle="genome", value=None, provenance=_prov(), scope_card=_SCOPE_CARD,
                            in_scope=False, available=False, output_kind="baseline",
                            note=f"non-PEGylated vehicle {vehicle_name!r}: anti-PEG axis not applicable (abstains).")

    rec = t["prevalence"]
    lo, hi = rec["anti_peg_prevalence_pct"]
    mid = (lo + hi) / 2.0
    score = max(0.0, min(1.0, 1.0 - mid / 100.0))
    return OracleResult(
        oracle="genome",
        value={"preexisting_antipeg_score": round(score, 3), "anti_peg_prevalence_pct": [lo, hi],
               "midpoint_pct": mid, "gates": "re-dosing", "dois": rec.get("dois", [])},
        provenance=_prov(dois=rec.get("dois", [])), native_uncertainty=round((hi - lo) / 200.0, 4),
        scope_card=_SCOPE_CARD, in_scope=True, extrapolating=False, output_kind="baseline", available=True,
        note=(f"population anti-PEG prevalence {lo}-{hi}% -> preexisting_antipeg_score={score:.3f}; gates "
              "RE-DOSING of PEGylated LNP. A POPULATION range (region/age/assay-dependent) - NOT a patient's "
              "anti-PEG titer (a known-unknown); induced anti-PEG after dose 1 is a separate, larger dynamic "
              "(not modelled)."))


def computed_antipeg_score(vehicle_name: str, pegylated: bool | None = None) -> tuple[float | None, OracleResult]:
    """Convenience: (anti-PEG score or None, full OracleResult). None when the oracle abstains (non-PEG).
    Never fabricates."""
    r = antipeg_oracle(vehicle_name, pegylated)
    val = (r.value or {}).get("preexisting_antipeg_score") if (r.available and r.value) else None
    return val, r
