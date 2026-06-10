"""Computed capsid/envelope T-cell epitope-load oracle for viral delivery vectors (v5.3, WS-EPITOPE).

Refines the documented `adaptive_immune` (CD8 T-cell) tier with a DATA-COMPUTED signal for VIRAL vectors: the
fraction of the capsid/envelope antigen that is presentable across a frequent HLA-I panel (MHCflurry %rank
<= 0.5), from configs/capsid_epitope_oracle.yaml (built by scripts/p53_build_epitope_oracle.py in the dedicated
`penstack:mhcflurry` image over UniProt-sourced sequences).

    capsid_immune_score = 1 - epitope_fraction_strong      # 1 = least presentable / least immunogenic

This is the NetMHC-style calculation the user asked for, made population-level (averaged over a frequent-allele
panel) so it is NOT a patient-HLA-specific magnitude. Answers through the v4.0 OracleResult contract
(output_kind="baseline").

Coverage of the whole palette: VIRAL vectors (AAV, lentivirus[VSV-G], HDAd, HSV) get a computed score;
NON-VIRAL vectors (LNP-mRNA, eVLP, electroporation) have no foreign capsid protein -> score 1.0 by mechanism;
a viral vector with no committed antigen sequence -> ABSTAINS (never fabricates).

HONESTY: this is a population-level, sequence-intrinsic PRESENTATION signal (does the capsid contain HLA
binders), NOT the realized in-vivo / patient-HLA-specific T-cell response (a known-unknown); it is also CD8
(MHC-I) only - it does not model antibody / neutralizing-antibody (B-cell) immunity.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import resource
from pen_stack.oracles.schema import OracleResult, Provenance
from pen_stack.planner.delivery_vehicles import vehicle

_SCOPE_CARD = "capsid_epitope"
# non-viral vehicles have no foreign capsid/envelope protein -> no capsid CD8 epitope load (1.0 by mechanism).
_NON_VIRAL = {"lnp_mrna", "evlp", "electroporation"}


@lru_cache(maxsize=1)
def _artifact() -> dict:
    return yaml.safe_load(resource("configs/capsid_epitope_oracle.yaml").read_text(encoding="utf-8"))


def _prov(**extra) -> Provenance:
    art = _artifact()
    return Provenance(model="mhcflurry_capsid_epitope", version=str(art.get("version", "1.0")), source="cache",
                      extra={"built": art.get("built"), "predictor": art.get("method", {}).get("predictor"),
                             "provenance_dois": art.get("provenance_dois", []), **extra})


def capsid_epitope_oracle(vehicle_name: str) -> OracleResult:
    """Computed capsid CD8 epitope load for a delivery vehicle, as an OracleResult (v4.0 contract).

    - viral vehicle with a committed antigen -> computed `capsid_immune_score` from MHCflurry x HLA panel.
    - non-viral vehicle -> 1.0 by mechanism (no foreign capsid protein).
    - unknown vehicle / viral-without-sequence -> available=False (caller falls back to the documented
      adaptive_immune tier; no number fabricated)."""
    rec = vehicle(vehicle_name)
    if rec is None:
        return OracleResult(oracle="protein_design", value=None, provenance=_prov(), scope_card=_SCOPE_CARD,
                            in_scope=False, available=False, output_kind="baseline",
                            note=f"unknown vehicle {vehicle_name!r}")

    vehs = _artifact().get("vehicles") or {}
    if vehicle_name in vehs:
        v = vehs[vehicle_name]
        ef = v["epitope_fraction_strong"]
        return OracleResult(
            oracle="protein_design",
            value={"capsid_immune_score": v["capsid_immune_score"], "epitope_fraction_strong": ef,
                   "antigens": v.get("antigens"),
                   "hla_panel_size": len(_artifact().get("method", {}).get("hla_panel", []))},
            provenance=_prov(antigens=v.get("antigens")), native_uncertainty=None,
            scope_card=_SCOPE_CARD, in_scope=True, extrapolating=False, output_kind="baseline", available=True,
            note=(f"{ef:.1%} of the {'/'.join(v.get('antigens', []))} antigen is presentable (MHCflurry "
                  f"%rank<=0.5) across a frequent HLA-I panel; capsid_immune_score=1-epitope_fraction. "
                  "Patient-HLA-specific T-cell response is a known-unknown (not modelled); CD8/MHC-I only "
                  "(not antibody/NAb)."))

    if vehicle_name in _NON_VIRAL:
        return OracleResult(
            oracle="protein_design",
            value={"capsid_immune_score": 1.0, "epitope_fraction_strong": 0.0, "mechanism": "non-viral"},
            provenance=_prov(), native_uncertainty=0.0, scope_card=_SCOPE_CARD, in_scope=True,
            extrapolating=False, output_kind="baseline", available=True,
            note="non-viral vehicle: no foreign capsid/envelope protein -> no capsid CD8 epitope load (1.0).")

    return OracleResult(oracle="protein_design", value=None, provenance=_prov(), scope_card=_SCOPE_CARD,
                        in_scope=False, available=False, output_kind="baseline",
                        note=f"viral vehicle {vehicle_name!r} has no committed antigen sequence; "
                             "fall back to the documented adaptive_immune tier.")


def computed_capsid_immune_score(vehicle_name: str) -> tuple[float | None, OracleResult]:
    """Convenience: (capsid_immune_score or None, full OracleResult). None when the oracle abstains (caller
    then uses the documented adaptive_immune tier). Never fabricates."""
    r = capsid_epitope_oracle(vehicle_name)
    val = (r.value or {}).get("capsid_immune_score") if (r.available and r.value) else None
    return val, r
