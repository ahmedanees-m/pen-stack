"""Computed capsid/envelope T-cell epitope-load oracle for viral delivery vectors (v5.3, WS-EPITOPE;
v6.9.2 re-grounded on **NetMHCpan-4.1**).

Refines the documented `adaptive_immune` (CD8 T-cell) tier with a DATA-COMPUTED signal for VIRAL vectors: the
fraction of the capsid/envelope antigen presentable across a frequent HLA-I panel. **As of v6.9.2 the PRIMARY
predictor is the gold-standard licensed NetMHCpan-4.1** (eluted-ligand %Rank_EL <= 0.5, residue coverage union
over a 12-allele frequent-HLA panel), computed on the VM and cached as derived fractions in
`configs/mhc_epitope_oracle.yaml` (`mhc1`). The earlier MHCflurry %rank<=0.5 cache
(`configs/capsid_epitope_oracle.yaml`) is retained as an explicit, reported **cross-check** (same residue-coverage
metric, same panel), never silently substituted.

    capsid_immune_score = 1 - epitope_fraction_strong # 1 = least presentable / least immunogenic

Population-level (averaged over a frequent-allele panel) so it is NOT a patient-HLA-specific magnitude. Answers
through the v4.0 OracleResult contract (output_kind="baseline"). The vehicle -> antigen(s) mapping lives in
`configs/capsid_epitope_oracle.yaml` (`vehicles`); the strong-binder fractions come from the NetMHCpan-4.1 cache.

Coverage of the whole palette: VIRAL vectors (AAV, lentivirus[VSV-G], HDAd, HSV) get a computed score;
NON-VIRAL vectors (LNP-mRNA, eVLP, electroporation) have no foreign capsid protein -> score 1.0 by mechanism;
a viral vector with no committed antigen sequence -> ABSTAINS (never fabricates).

SCOPE: this is a population-level, sequence-intrinsic PRESENTATION signal (does the capsid contain HLA
binders), NOT the realized in-vivo / patient-HLA-specific T-cell response (a known-unknown); it is also CD8
(MHC-I) only - it does not model antibody / neutralizing-antibody (B-cell) immunity. NetMHCpan-4.1 and MHCflurry
are different models and disagree on absolute load (both agree AAV is the least CD8-immunogenic capsid); the
cross-check makes that disagreement visible rather than hiding it.
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
def _mhcflurry_artifact() -> dict:
    """The MHCflurry capsid cache, used for the vehicle->antigen mapping AND as the reported cross-check."""
    return yaml.safe_load(resource("configs/capsid_epitope_oracle.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _netmhcpan_mhc1() -> dict:
    """The REAL NetMHCpan-4.1 MHC-I residue-coverage cache (configs/mhc_epitope_oracle.yaml `mhc1`), keyed by
    antigen. Only derived fractions are shipped (the licensed binary is never distributed). {} if absent."""
    try:
        art = yaml.safe_load(resource("configs/mhc_epitope_oracle.yaml").read_text(encoding="utf-8")) or {}
        return art.get("mhc1") or {}
    except Exception: # noqa: BLE001
        return {}


def _netmhc_version() -> str:
    try:
        art = yaml.safe_load(resource("configs/mhc_epitope_oracle.yaml").read_text(encoding="utf-8")) or {}
        return str(art.get("version", "6.9.2"))
    except Exception: # noqa: BLE001
        return "6.9.2"


def _prov(**extra) -> Provenance:
    fl = _mhcflurry_artifact()
    return Provenance(model="netmhcpan4.1_capsid_epitope", version=_netmhc_version(), source="cache",
                      extra={"primary_predictor": "NetMHCpan-4.1 (%Rank_EL<=0.5, residue coverage, 12-allele panel)",
                             "cross_check_predictor": fl.get("method", {}).get("predictor"),
                             "provenance_dois": ["10.1093/nar/gkac1029", *fl.get("provenance_dois", [])], **extra})


def _antigens_for(vehicle_name: str) -> list[str] | None:
    rec = (_mhcflurry_artifact().get("vehicles") or {}).get(vehicle_name)
    return rec.get("antigens") if rec else None


def capsid_epitope_oracle(vehicle_name: str) -> OracleResult:
    """Computed capsid CD8 epitope load for a delivery vehicle, as an OracleResult (v4.0 contract).

    - viral vehicle with committed antigen(s) -> computed `capsid_immune_score` from **NetMHCpan-4.1** x HLA
      panel (primary), with the MHCflurry value reported as a cross-check.
    - non-viral vehicle -> 1.0 by mechanism (no foreign capsid protein).
    - unknown vehicle / viral-without-sequence -> available=False (caller falls back to the documented
      adaptive_immune tier; no number fabricated)."""
    rec = vehicle(vehicle_name)
    if rec is None:
        return OracleResult(oracle="protein_design", value=None, provenance=_prov(), scope_card=_SCOPE_CARD,
                            in_scope=False, available=False, output_kind="baseline",
                            note=f"unknown vehicle {vehicle_name!r}")

    antigens = _antigens_for(vehicle_name)
    mhc1 = _netmhcpan_mhc1()
    if antigens and all(a in mhc1 for a in antigens):
        fracs = [mhc1[a]["epitope_fraction_strong"] for a in antigens]
        ef = round(sum(fracs) / len(fracs), 4)
        score = round(1.0 - ef, 4)
        # MHCflurry cross-check (same vehicle, from its dedicated cache)
        fl_veh = (_mhcflurry_artifact().get("vehicles") or {}).get(vehicle_name, {})
        cross = {"predictor": "MHCflurry 2.0 (%rank<=0.5)",
                 "epitope_fraction_strong": fl_veh.get("epitope_fraction_strong"),
                 "capsid_immune_score": fl_veh.get("capsid_immune_score")}
        return OracleResult(
            oracle="protein_design",
            value={"capsid_immune_score": score, "epitope_fraction_strong": ef, "antigens": antigens,
                   "predictor": "NetMHCpan-4.1", "hla_panel_size": 12, "cross_check_mhcflurry": cross},
            provenance=_prov(antigens=antigens), native_uncertainty=None,
            scope_card=_SCOPE_CARD, in_scope=True, extrapolating=False, output_kind="baseline", available=True,
            note=(f"{ef:.1%} of the {'/'.join(antigens)} antigen is presentable (NetMHCpan-4.1 %Rank_EL<=0.5, "
                  f"residue coverage over a 12-allele frequent HLA-I panel); capsid_immune_score=1-epitope_fraction. "
                  f"MHCflurry cross-check capsid_immune_score={cross['capsid_immune_score']}. Patient-HLA-specific "
                  "T-cell response is a known-unknown (not modelled); CD8/MHC-I only (not antibody/NAb)."))

    if vehicle_name in _NON_VIRAL:
        return OracleResult(
            oracle="protein_design",
            value={"capsid_immune_score": 1.0, "epitope_fraction_strong": 0.0, "mechanism": "non-viral"},
            provenance=_prov(), native_uncertainty=0.0, scope_card=_SCOPE_CARD, in_scope=True,
            extrapolating=False, output_kind="baseline", available=True,
            note="non-viral vehicle: no foreign capsid/envelope protein -> no capsid CD8 epitope load (1.0).")

    return OracleResult(oracle="protein_design", value=None, provenance=_prov(), scope_card=_SCOPE_CARD,
                        in_scope=False, available=False, output_kind="baseline",
                        note=f"viral vehicle {vehicle_name!r} has no committed antigen sequence in the NetMHCpan-4.1 "
                             "cache; fall back to the documented adaptive_immune tier.")


def computed_capsid_immune_score(vehicle_name: str) -> tuple[float | None, OracleResult]:
    """Convenience: (capsid_immune_score or None, full OracleResult). None when the oracle abstains (caller
    then uses the documented adaptive_immune tier). Never fabricates."""
    r = capsid_epitope_oracle(vehicle_name)
    val = (r.value or {}).get("capsid_immune_score") if (r.available and r.value) else None
    return val, r
