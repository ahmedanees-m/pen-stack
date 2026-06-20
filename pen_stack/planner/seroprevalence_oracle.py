"""Anti-vector neutralizing-antibody seroprevalence oracle (v5.5, WS-SEROPREV).

The last computable delivery-immunology axis: PRE-EXISTING humoral immunity (B-cell / neutralizing antibody)
to a viral capsid. Unlike genotoxicity (v5.2), capsid T-cell epitope load (v5.3) and innate sensing (v5.4),
this CANNOT be computed from sequence - it is the prevalence, in a population, of people who already carry
NAbs against the vector from natural exposure. The grounding is published serosurvey DATA
(configs/seroprevalence.yaml), curated as ranges with provenance.

    preexisting_score = 1 - midpoint(seroprevalence_pct) / 100 # 1 = fewest patients excluded by NAb

Answers through the v4.0 OracleResult contract (output_kind="baseline"). Non-viral vehicles carry no foreign
capsid -> no pre-existing ANTI-VECTOR humoral immunity (score 1.0 by mechanism). SCOPE: a POPULATION
prevalence, NOT a given patient's NAb titer (a known-unknown); region/age/assay-dependent (a range, surfaced);
the humoral (B-cell) axis only - distinct from the T-cell epitope load of v5.3.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource
from pen_stack.oracles.schema import OracleResult, Provenance

_SCOPE_CARD = "seroprevalence"


@lru_cache(maxsize=1)
def _table() -> dict:
    return yaml.safe_load(resource("configs/seroprevalence.yaml").read_text(encoding="utf-8"))


def _all_dois() -> list[str]:
    dois: set[str] = set()
    for rec in (_table().get("serotypes") or {}).values():
        dois.update(rec.get("dois", []) or [])
    return sorted(dois)


def _prov(**extra) -> Provenance:
    return Provenance(model="anti_vector_seroprevalence", version=str(_table().get("version", "1.0")),
                      source="cache", extra=extra)


def seroprevalence_oracle(vehicle_name: str, serotype: str | None = None) -> OracleResult:
    """Pre-existing anti-vector NAb seroprevalence for a vehicle (or an explicit serotype), as an OracleResult.

    - viral vehicle (or serotype) with curated data -> preexisting_score = 1 - midpoint(seroprevalence)/100.
    - non-viral vehicle -> 1.0 by mechanism (no foreign capsid).
    - unknown vehicle / no curated serotype -> available=False (caller falls back to the documented tier).
    Never fabricates a number."""
    t = _table()
    sero = t.get("serotypes") or {}
    key = serotype or (t.get("vehicle_serotype") or {}).get(vehicle_name)

    if key and key in sero:
        rec = sero[key]
        lo, hi = rec["nab_seroprevalence_pct"]
        mid = (lo + hi) / 2.0
        score = max(0.0, min(1.0, 1.0 - mid / 100.0))
        return OracleResult(
            oracle="genome",
            value={"preexisting_score": round(score, 3), "serotype": key,
                   "nab_seroprevalence_pct": [lo, hi], "midpoint_pct": mid, "dois": rec.get("dois", [])},
            provenance=_prov(serotype=key, dois=rec.get("dois", [])), native_uncertainty=round((hi - lo) / 200.0, 4),
            scope_card=_SCOPE_CARD, in_scope=True, extrapolating=False, output_kind="baseline", available=True,
            note=(f"{key}: documented NAb seroprevalence {lo}-{hi}% (population); preexisting_score="
                  f"1-midpoint/100={score:.3f}. " + (rec.get("note", "") + " " if rec.get("note") else "")
                  + "A POPULATION prevalence, region/age/assay-dependent - NOT a given patient's NAb titer "
                  "(a known-unknown)."))

    if vehicle_name in (t.get("non_viral") or []):
        return OracleResult(
            oracle="genome",
            value={"preexisting_score": 1.0, "serotype": None, "mechanism": "non-viral"},
            provenance=_prov(), native_uncertainty=0.0, scope_card=_SCOPE_CARD, in_scope=True,
            extrapolating=False, output_kind="baseline", available=True,
            note="non-viral vehicle: no foreign capsid -> no pre-existing ANTI-VECTOR humoral immunity (1.0). "
                 "Anti-PEG immunity for LNP is an emerging, separate exception (not a vector seroprevalence).")

    return OracleResult(oracle="genome", value=None, provenance=_prov(), scope_card=_SCOPE_CARD,
                        in_scope=False, available=False, output_kind="baseline",
                        note=f"no curated seroprevalence for {vehicle_name!r}; fall back to the documented "
                             "preexisting_immunity tier.")


def computed_preexisting_score(vehicle_name: str, serotype: str | None = None) -> tuple[float | None, OracleResult]:
    """Convenience: (preexisting_score or None, full OracleResult). None when the oracle abstains. Never
    fabricates."""
    r = seroprevalence_oracle(vehicle_name, serotype)
    val = (r.value or {}).get("preexisting_score") if (r.available and r.value) else None
    return val, r
