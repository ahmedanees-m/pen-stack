"""Rule evaluators — the bridge from rules-as-data to the existing validated code (Phase 3.3, WS-R).

Each evaluator runs ONE rule against a ``Design`` and returns a ``RuleResult``. Crucially, evaluators
**delegate to the functions that already implement the logic** (``planner.target_site``, ``bridge.fold_qc``,
``planner.delivery_constraints``, ``planner.multiplex``, and the delivery-vehicle table) — so lifting the
rules into data changes no decision (the WS-R parity test proves it). An evaluator whose required inputs are
absent returns ``not_applicable`` (never a spurious violate), so a partial design is still checkable.

Evaluators are registered by name; a rule's ``evaluator`` field names the function. To add a rule you add a
YAML record + (if new) one evaluator here — never scattered ``if`` checks in the planner.
"""
from __future__ import annotations

from collections.abc import Callable

from pen_stack.rules.schema import Design, Rule, RuleResult

_REGISTRY: dict[str, Callable[[Design, Rule], RuleResult]] = {}


def evaluator(name: str):
    def deco(fn):
        _REGISTRY[name] = fn
        return fn
    return deco


def get_evaluator(name: str) -> Callable[[Design, Rule], RuleResult]:
    if name not in _REGISTRY:
        raise KeyError(f"no rule evaluator registered as {name!r}")
    return _REGISTRY[name]


def _result(rule: Rule, status: str, reason: str, value=None) -> RuleResult:
    return RuleResult(rule_id=rule.id, kind=rule.kind, category=rule.category, status=status,
                      reason=reason, citation=list(rule.provenance.get("doi", [])), value=value)


def _na(rule: Rule, why: str) -> RuleResult:
    return _result(rule, "not_applicable", f"not applicable: {why}")


# writer output form (what the vehicle must carry) when the design does not state it explicitly.
_WRITER_FORM = {"bridge_is110": "DNA", "seek_is1111": "DNA", "cast_vk": "DNA",
                "serine_integrase": "DNA", "pe_integrase": "DNA",
                "cas9": "RNP", "cas12a": "RNP"}


def writer_output_form(design: Design) -> str | None:
    if design.writer_output_form:
        return design.writer_output_form
    return _WRITER_FORM.get(str(design.writer_family or "").lower())


# --------------------------------------------------------------------------------------------------
# reachability / target-site  (delegates to planner.target_site — the v3.2 MC1 hard filter)
# --------------------------------------------------------------------------------------------------
@evaluator("reachability_target_site")
def reachability_target_site(design: Design, rule: Rule) -> RuleResult:
    if not design.writer_family or not design.site_seq:
        return _na(rule, "no writer_family + site_seq")
    from pen_stack.planner.target_site import target_site_available
    v = target_site_available(design.writer_family, design.site_seq, installed_att=design.installed_att)
    if not v.get("checked", True):
        return _na(rule, v.get("reason", "family has no target-site rule"))
    return _result(rule, "pass" if v["available"] else "violate", v["reason"])


# --------------------------------------------------------------------------------------------------
# fold legality  (delegates to bridge.fold_qc cross-loop screen — soft penalty / flag)
# --------------------------------------------------------------------------------------------------
@evaluator("fold_cross_loop")
def fold_cross_loop(design: Design, rule: Rule) -> RuleResult:
    if not design.target_guide or not design.donor_guide:
        return _na(rule, "no bridge-RNA target_guide + donor_guide")
    from pen_stack.bridge.fold_qc import cross_loop_risk
    thr = float(rule.param.get("cross_loop_threshold", 0.6))
    xl = cross_loop_risk(design.target_guide, design.donor_guide)
    worst = max(xl.values())
    flagged = [k for k, val in xl.items() if val >= thr]
    if flagged:
        return _result(rule, "flag", f"cross-loop complementarity {flagged} >= {thr} "
                       "(self/TBL-DBL recombination risk)", value=round(worst, 3))
    return _result(rule, "pass", f"cross-loop complementarity below {thr}", value=round(worst, 3))


# --------------------------------------------------------------------------------------------------
# payload capacity  (cargo_bp <= vehicle capacity — hard reject)  +  split-AAV penalty (soft)
# --------------------------------------------------------------------------------------------------
@evaluator("payload_capacity")
def payload_capacity(design: Design, rule: Rule) -> RuleResult:
    if design.cargo_bp is None or not design.delivery_vehicle:
        return _na(rule, "no cargo_bp + delivery_vehicle")
    from pen_stack.planner.delivery_vehicles import vehicle
    veh = vehicle(design.delivery_vehicle)
    if veh is None:
        return _na(rule, f"unknown vehicle {design.delivery_vehicle!r}")
    cap = veh.get("cargo_capacity_bp")
    if cap is None:
        return _na(rule, "vehicle has no capacity (e.g. physical delivery)")
    if design.cargo_bp > cap:
        return _result(rule, "violate", f"cargo {design.cargo_bp} bp exceeds {design.delivery_vehicle} "
                       f"capacity {cap} bp", value=design.cargo_bp)
    return _result(rule, "pass", f"cargo {design.cargo_bp} bp within {design.delivery_vehicle} "
                   f"capacity {cap} bp", value=design.cargo_bp)


@evaluator("split_aav_penalty")
def split_aav_penalty(design: Design, rule: Rule) -> RuleResult:
    if design.cargo_bp is None or not design.delivery_vehicle:
        return _na(rule, "no cargo_bp + delivery_vehicle")
    v = str(design.delivery_vehicle).lower()
    single_cap = int(rule.param.get("single_aav_cap_bp", 4700))
    if "aav" in v and design.cargo_bp > single_cap:
        return _result(rule, "flag", f"cargo {design.cargo_bp} bp needs split/dual AAV "
                       "(efficiency drops sharply)", value=design.cargo_bp)
    return _result(rule, "pass", "no split-AAV efficiency penalty")


# --------------------------------------------------------------------------------------------------
# delivery compatibility  (writer output-form <-> vehicle; integration constraint — hard reject)
# --------------------------------------------------------------------------------------------------
@evaluator("delivery_cargo_form")
def delivery_cargo_form(design: Design, rule: Rule) -> RuleResult:
    form = writer_output_form(design)
    if form is None or not design.delivery_vehicle:
        return _na(rule, "no writer output-form + delivery_vehicle")
    from pen_stack.planner.delivery_vehicles import vehicle
    veh = vehicle(design.delivery_vehicle)
    if veh is None:
        return _na(rule, f"unknown vehicle {design.delivery_vehicle!r}")
    forms = veh.get("compatible_cargo_form", [])
    if form not in forms:
        return _result(rule, "violate", f"{design.writer_family} delivers {form}, but "
                       f"{design.delivery_vehicle} carries {forms}")
    return _result(rule, "pass", f"{form} payload compatible with {design.delivery_vehicle}")


@evaluator("delivery_no_integration")
def delivery_no_integration(design: Design, rule: Rule) -> RuleResult:
    if not design.delivery_vehicle:
        return _na(rule, "no delivery_vehicle")
    if not design.no_integration:
        return _result(rule, "pass", "no non-integration constraint declared")
    from pen_stack.planner.delivery_vehicles import vehicle
    veh = vehicle(design.delivery_vehicle)
    if veh is None:
        return _na(rule, f"unknown vehicle {design.delivery_vehicle!r}")
    if veh.get("integrating"):
        return _result(rule, "violate", f"goal forbids integration but {design.delivery_vehicle} integrates")
    return _result(rule, "pass", f"{design.delivery_vehicle} is non-integrating, as required")


@evaluator("delivery_aav_packaging")
def delivery_aav_packaging(design: Design, rule: Rule) -> RuleResult:
    """v4.0 delivery-oracle refinement: AAV packaging EFFICIENCY drops sharply as the cargo approaches the
    capsid limit (a computable property of cargo_bp vs the vehicle capacity), even when still under capacity.
    Soft flag when within the margin; not a titre predictor."""
    if design.cargo_bp is None or not design.delivery_vehicle:
        return _na(rule, "no cargo_bp + delivery_vehicle")
    v = str(design.delivery_vehicle).lower()
    if "aav" not in v:
        return _result(rule, "pass", "not an AAV vehicle; packaging-margin check n/a")
    from pen_stack.planner.delivery_vehicles import vehicle
    veh = vehicle(design.delivery_vehicle) or {}
    cap = veh.get("cargo_capacity_bp")
    if not cap:
        return _na(rule, "vehicle has no capacity")
    margin = float(rule.param.get("margin_frac", 0.9))       # within 90-100% of capacity -> efficiency penalty
    frac = design.cargo_bp / cap
    if frac >= margin:
        return _result(rule, "flag", f"cargo {design.cargo_bp} bp is {frac:.0%} of {design.delivery_vehicle} "
                       f"capacity {cap} bp (packaging efficiency / titre drops near the limit)",
                       value=round(frac, 3))
    return _result(rule, "pass", f"cargo {frac:.0%} of capacity (comfortable packaging margin)",
                   value=round(frac, 3))


@evaluator("delivery_sequence_constraints")
def delivery_sequence_constraints(design: Design, rule: Rule) -> RuleResult:
    if not design.cargo_seq or not design.delivery_vehicle:
        return _na(rule, "no cargo_seq + delivery_vehicle")
    from pen_stack.planner.delivery_constraints import scan_delivery
    from pen_stack.planner.delivery_vehicles import vehicle
    veh = vehicle(design.delivery_vehicle) or {}
    key = veh.get("constraint_key", design.delivery_vehicle)
    r = scan_delivery(design.cargo_seq, key)
    if r["flags"]:
        return _result(rule, "flag", "; ".join(f["detail"] for f in r["flags"]),
                       value=r["delivery_constraint_risk"])
    return _result(rule, "pass", "no vehicle-specific sequence flags", value=r["delivery_constraint_risk"])


@evaluator("delivery_immunogenicity_scope")
def delivery_immunogenicity_scope(design: Design, rule: Rule) -> RuleResult:
    if not design.delivery_vehicle:
        return _na(rule, "no delivery_vehicle")
    return _result(rule, "scope", "immunogenicity MAGNITUDE and precise in-vivo tropism are not modeled "
                   "(declared out of scope, never predicted)")


# --------------------------------------------------------------------------------------------------
# multiplex translocation  (delegates to planner.multiplex — soft penalty)
# --------------------------------------------------------------------------------------------------
@evaluator("multiplex_translocation")
def multiplex_translocation(design: Design, rule: Rule) -> RuleResult:
    if not design.edits or len(design.edits) < 2:
        return _na(rule, "fewer than 2 edits")
    from pen_stack.planner.multiplex import translocation_risk
    r = translocation_risk(design.edits)
    risk = r.get("translocation_risk", 0.0)
    thr = float(rule.param.get("risk_threshold", 0.2))
    if risk >= thr:
        return _result(rule, "flag", f"pairwise translocation risk {risk} >= {thr} "
                       "(concurrent DSBs may mis-join)", value=risk)
    return _result(rule, "pass", f"translocation risk {risk} < {thr} "
                   "(DSB-free writers carry ~zero by construction)", value=risk)
