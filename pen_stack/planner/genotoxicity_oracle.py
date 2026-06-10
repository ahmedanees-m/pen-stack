"""Computed genotoxicity oracle for integrating delivery vectors (v5.2, WS-GENOTOX).

Replaces the hard-coded `genotoxicity` ordinal tier (v5.1, documented prior) with a DATA-COMPUTED signal for
INTEGRATING vehicles: the observed enrichment of a vector class's integration sites near COSMIC Cancer-Gene-
Census oncogenes, from VISDB integration catalogues x the Phase-1 oncogene annotation (configs/
genotoxicity_oracle.yaml, built by scripts/p52_build_genotox_oracle.py on the VM where the data lives).

    genotox_score = min(1, 1 / enrichment)      # 1 = safest; episomal/non-targeting ~ 1.0

This reproduces the lentivirus-safer-than-gammaretrovirus ordering FROM DATA (lentiviral ~2x oncogene-proximity
enrichment vs gammaretroviral ~5-6x — the LMO2 / SCID-X1 pattern), instead of asserting it. It answers through
the v4.0 OracleResult contract (value + provenance + native_uncertainty + scope_card + output_kind) and is an
`output_kind="baseline"` observed-data comparator, NOT a generative claim.

HONESTY: this is a RELATIVE, integration-PREFERENCE signal. The in-vivo clonal-expansion / leukemogenesis
OUTCOME in a patient is NOT modelled and stays a known-unknown; a class with too few catalogued sites is
flagged `extrapolating`; non-integrating vehicles have no insertional mechanism (score 1.0 by mechanism).
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource
from pen_stack.oracles.schema import OracleResult, Provenance
from pen_stack.planner.delivery_vehicles import vehicle

_SCOPE_CARD = "delivery_genotoxicity"


@lru_cache(maxsize=1)
def _artifact() -> dict:
    return yaml.safe_load(resource("configs/genotoxicity_oracle.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _vehicle_to_class() -> dict:
    art = _artifact()
    out: dict[str, str] = {}
    for cls, vehs in (art.get("vehicle_class") or {}).items():
        for v in vehs or []:
            out[v] = cls
    return out


def _prov(source: str, **extra) -> Provenance:
    art = _artifact()
    return Provenance(model="visdb_integration_x_cosmic_cgc", version=str(art.get("version", "1.0")),
                      source=source, extra={"built": art.get("built"),
                                            "provenance_dois": art.get("provenance_dois", []), **extra})


def genotoxicity_oracle(vehicle_name: str) -> OracleResult:
    """Computed genotoxicity for a delivery vehicle, as an OracleResult (v4.0 contract).

    - non-integrating vehicle  -> genotox_score 1.0 by mechanism (episomal/transient; no insertional risk).
    - integrating + computed class -> data-derived score from VISDB x COSMIC; small-n class -> extrapolating.
    - integrating but no computed class / unknown vehicle -> available=False (caller falls back to the
      documented `immune_safety.genotoxicity` tier; no number is fabricated)."""
    rec = vehicle(vehicle_name)
    if rec is None:
        return OracleResult(oracle="genome", value=None, provenance=_prov("cache"),
                            scope_card=_SCOPE_CARD, in_scope=False, available=False, output_kind="baseline",
                            note=f"unknown vehicle {vehicle_name!r}")

    if not rec.get("integrating"):
        return OracleResult(
            oracle="genome",
            value={"genotox_score": 1.0, "enrichment": None, "mechanism": "non-integrating"},
            provenance=_prov("cache"), native_uncertainty=0.0, scope_card=_SCOPE_CARD, in_scope=True,
            extrapolating=False, output_kind="baseline", available=True,
            note="episomal/transient vector: no integration -> no insertional-mutagenesis mechanism (score 1.0).")

    cls = _vehicle_to_class().get(vehicle_name)
    classes = _artifact().get("classes") or {}
    if not cls or cls not in classes:
        return OracleResult(oracle="genome", value=None, provenance=_prov("cache"),
                            scope_card=_SCOPE_CARD, in_scope=False, available=False, output_kind="baseline",
                            note=f"integrating vehicle {vehicle_name!r} has no computed class; "
                                 "fall back to the documented genotoxicity tier.")

    rc = classes[cls]
    enrich = rc.get("enrichment")
    frac, ci95, n = rc.get("frac_oncogene_50kb"), rc.get("ci95"), rc.get("n_sites")
    score = min(1.0, 1.0 / enrich) if enrich else None
    robust = bool(rc.get("robust"))
    # native uncertainty = relative CI on the observed oncogene-proximity fraction (coefficient of variation)
    nu = round(ci95 / frac, 4) if (ci95 and frac) else None
    return OracleResult(
        oracle="genome",
        value={"genotox_score": round(score, 3) if score is not None else None,
               "enrichment": enrich, "frac_oncogene_50kb": frac, "ci95": ci95, "n_sites": n,
               "frac_genotoxic_cis": rc.get("frac_genotoxic_cis"), "vector_class": cls,
               "background_frac": _artifact().get("genome_background_frac_oncogene_50kb")},
        provenance=_prov("cache", virus=rc.get("virus"), vector_class=cls),
        native_uncertainty=nu, scope_card=_SCOPE_CARD, in_scope=True,
        extrapolating=not robust, output_kind="baseline", available=True,
        note=(f"{cls} integration is {enrich}x enriched within "
              f"{_artifact().get('window_bp')} bp of a COSMIC oncogene vs background "
              f"({frac:.3%}, n={n}); genotox_score=min(1,1/enrichment)."
              + ("" if robust else " SMALL-N class: directional only (extrapolating).")
              + " In-vivo clonal outcome is a known-unknown (not modelled).")
    )


def computed_genotox_score(vehicle_name: str) -> tuple[float | None, OracleResult]:
    """Convenience: (genotox_score or None, full OracleResult). None when the oracle abstains (caller then
    uses the documented tier). Never fabricates a number."""
    r = genotoxicity_oracle(vehicle_name)
    val = (r.value or {}).get("genotox_score") if (r.available and r.value) else None
    return val, r
