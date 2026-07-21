"""Acquisition functions for the experiment designer.

Score each candidate experiment by the information it is expected to yield, computed from the calibrated
twin's predictive uncertainty (never fabricated). Three signals:
  * expected_information_gain, reducible predictive uncertainty (entropy now - expected posterior entropy),
  * predictive_entropy, the twin's current uncertainty (from its interval width),
  * immune_voi, value of information for VALIDATING an immune PROXY axis (turns proxy -> validated).
The acquisition is only as good as the twin and the labels it queries; it chooses informative
experiments, it does not run them.
"""
from __future__ import annotations

import math

# a measurement does not resolve uncertainty perfectly: a noise floor on the post-experiment entropy.
_MEASUREMENT_NOISE_SD = 0.05
_TWO_PI_E = 2.0 * math.pi * math.e


def _interval_sd(outcome: dict) -> float:
    """Std-dev implied by the twin's (approx 95%) interval: sd ~ width / (2 * 1.96)."""
    lo, hi = outcome.get("interval", [0.0, 0.0])
    return max(1e-6, (float(hi) - float(lo)) / (2.0 * 1.96))


def _gaussian_entropy(sd: float) -> float:
    return 0.5 * math.log(_TWO_PI_E * sd * sd)


def predictive_entropy(outcome: dict) -> float:
    """Differential entropy of the twin's predictive distribution, from its interval width."""
    return _gaussian_entropy(_interval_sd(outcome))


def _expected_posterior_entropy(outcome: dict) -> float:
    """Entropy expected AFTER running the experiment: the measurement collapses predictive sd toward the
    measurement noise floor (cannot go below it)."""
    post_sd = max(_MEASUREMENT_NOISE_SD, min(_interval_sd(outcome), _MEASUREMENT_NOISE_SD * 2))
    return _gaussian_entropy(post_sd)


def _effective_sd(outcome: dict, cell_state: str) -> float:
    """Predictive SD the experiment could reduce. The twin's mechanistic interval is a FIXED heuristic band, so
    it understates how much LESS the model knows in an under-characterised regime, an UNMEASURED cell type (no
    writability atlas there) and an OUT-OF-DISTRIBUTION design genuinely carry more reducible uncertainty. Widen
    the base SD by those real signals so EIG reflects them (fixes EIG reading a constant ~0.02 for
    every candidate, it was blind to cell-type coverage). Not fabrication: we DO know less where we have no data."""
    return _interval_sd(outcome) * (1.0 + coverage_novelty(cell_state) + _ood_signal(outcome))


def _eig_from_outcome(outcome: dict, cell_state: str) -> float:
    """EIG ~ reducible uncertainty = entropy now - expected posterior entropy, on the coverage/OOD-aware SD."""
    sd = _effective_sd(outcome, cell_state)
    post_sd = max(_MEASUREMENT_NOISE_SD, min(sd, _MEASUREMENT_NOISE_SD * 2))
    return max(0.0, _gaussian_entropy(sd) - _gaussian_entropy(post_sd))


def expected_information_gain(candidate: dict, cell_state: str, model_ctx: dict | None = None) -> float:
    """EIG ~ reducible uncertainty from the calibrated twin, widened for cell-type coverage + OOD; >= 0 (a
    measurement never increases expected uncertainty). The experiment's own cell type wins over the batch cell."""
    from pen_stack.twin.outcome import predict_outcome
    cs = candidate.get("cell_type") or candidate.get("cell_state") or cell_state or ""
    return _eig_from_outcome(predict_outcome(candidate, cs), cs)


def immune_voi(candidate: dict, cell_state: str = "") -> float:
    """Value of information for validating an immune PROXY axis: an IN-SCOPE axis still labelled a proxy
    that this experiment would MEASURE is high-VOI (turns proxy -> outcome-validated). Reads the validation
    labels. Requires the axis to be IN SCOPE, an abstaining axis (e.g. anti-PEG on a non-PEG vehicle,
    innate with no cargo sequence) cannot be validated by running the experiment, so it does not count. This is
    what makes the VOI vary by vehicle (LNP has anti-PEG in scope; AAV does not), a real design signal."""
    from pen_stack.twin.outcome import predict_outcome
    prof = predict_outcome(candidate, cell_state or candidate.get("cell_state", "")).get("immune_outcome") or {}
    measures = {str(a).strip().lower() for a in (candidate.get("measures_immune_axes") or [])}
    voi = 0.0
    for axis, rec in prof.get("axes", {}).items():
        label = (rec.get("validation") or "").lower()
        # any axis still labelled a "proxy" is an unvalidated validation target (no axis is outcome-validated yet;
        # a validated one would drop the "proxy" label). The earlier "+ not outcome-validated" clause was
        # over-strict, it dropped the population proxies (pre-existing NAb, anti-PEG) whose labels instead say
        # "not calibrated", which are exactly the vehicle-specific axes that make VOI vary (anti-PEG applies to a
        # PEGylated LNP, not to AAV).
        is_proxy = "proxy" in label
        in_scope = rec.get("in_scope") is not False  # abstaining axis (in_scope False) can't be validated here
        if is_proxy and in_scope and (not measures or axis.lower() in measures):
            voi += 1.0
    return voi


# --- design-specific informativeness signals: the mechanistic twin's interval is a fixed heuristic band,
# so EIG alone is near-constant across designs (it barely reflects which experiment teaches the most). These add
# REAL, design-varying signals, feasibility, cell-type coverage novelty, out-of-distribution, so the acquisition
# genuinely differentiates experiments. None is fabricated: feasibility is the capacity rule, coverage is the
# measured-atlas roster, OOD is the twin's own extrapolation/widen flags.

# measured writability atlases (the roster Site Finder / celltypes report); an UNMEASURED cell type carries more
# reducible uncertainty (running an experiment there characterises a regime we have no data for -> higher novelty).
_CELL_COVERAGE = {"k562": "full", "hepg2": "full", "hspc": "partial"}
_COVERAGE_NOVELTY = {"full": 0.0, "partial": 0.5}  # unmeasured -> 1.0 (default)


def coverage_novelty(cell_state: str) -> float:
    """How under-characterised a cell type is (0 = full measured atlas, 1 = no atlas). An experiment in an
    unmeasured cell type is genuinely more informative, there is no measured data there yet."""
    return _COVERAGE_NOVELTY.get(_CELL_COVERAGE.get(str(cell_state or "").lower(), "none"), 1.0)


def feasibility_factor(candidate: dict) -> float:
    """A multiplicative gate in (0, 1]: an experiment that cannot be BUILT as specified (cargo overflows the
    vehicle, or a non-positive size) has little information value for the intended construct. 1.0 buildable,
    0.2 not, kept non-zero because it is still a (poor) data point, not literally worthless."""
    veh = candidate.get("delivery_vehicle") or candidate.get("vehicle")
    cargo = candidate.get("cargo_bp")
    if cargo is not None and int(cargo) <= 0:
        return 0.2
    if veh and cargo is not None:
        from pen_stack.planner.delivery_vehicles import vehicle as _veh
        cap = (_veh(veh) or {}).get("cargo_capacity_bp")
        if cap is not None and int(cargo) > int(cap):
            return 0.2
    return 1.0


def _ood_signal(outcome: dict) -> float:
    """0..1 novelty from the twin's OWN out-of-distribution flags: 1.0 if the response oracle extrapolates,
    else the expression head's ood_widen mapped from [1, 3] to [0, 1] (0 when neither is available)."""
    if outcome.get("extrapolating"):
        return 1.0
    pe = outcome.get("position_effect") or {}
    widen = pe.get("ood_widen")
    return max(0.0, min(1.0, (float(widen) - 1.0) / 2.0)) if widen is not None else 0.0


def acquisition_components(candidate: dict, cell_state: str, model_ctx: dict | None = None,
                          *, w_eig: float = 1.0, w_imm: float = 0.4) -> dict:
    """The full, traceable acquisition breakdown for one candidate experiment. Every term is a real quantity
    (twin uncertainty / proxy labels / capacity rule / measured-atlas roster); the composite is
    feasibility-gated. Returned so the UI can show WHY one experiment out-ranks another, not just a number.

    EIG now already folds cell-type coverage + OOD into its effective uncertainty (see `_effective_sd`),
    so those are NOT added a second time here, the acquisition is EIG (coverage/OOD-aware) + immune-VOI, gated by
    feasibility. `coverage_novelty` / `ood_signal` are still returned as breakdown diagnostics (their EFFECT is in
    EIG); this also makes EIG itself vary by design, fixing the "constant 0.02 EIG" the tester found."""
    from pen_stack.twin.outcome import predict_outcome
    # the experiment's OWN cell type wins (it is run in that cell), then the batch-level cell_state as a fallback,
    # so a pool that spans cell types is scored per-cell (coverage novelty varies), not collapsed to one context.
    cs = candidate.get("cell_type") or candidate.get("cell_state") or cell_state or ""
    o = predict_outcome(candidate, cs)
    eig = _eig_from_outcome(o, cs)
    voi = immune_voi(candidate, cs)
    feas = feasibility_factor(candidate)
    buildable = (o.get("feasibility") or {}).get("buildable", True)
    informativeness = w_eig * eig + w_imm * voi
    return {"acquisition": round(feas * informativeness, 6),
            "expected_info_gain": round(eig, 6), "immune_voi": voi,
            "coverage_novelty": coverage_novelty(cs), "ood_signal": round(_ood_signal(o), 4),
            "feasibility_factor": feas, "buildable": bool(buildable)}


def acquisition_score(candidate: dict, cell_state: str, model_ctx: dict | None = None,
                      *, w_eig: float = 1.0, w_unc: float = 0.3, w_imm: float = 0.4) -> float:
    """Composite acquisition (feasibility-gated information value). Fully traceable to twin quantities +
    labels + the capacity rule + the measured-atlas roster (no fabricated values); deterministic given inputs.
    `w_unc` is retained for backward compatibility (the raw-uncertainty term folded into the richer breakdown)."""
    return acquisition_components(candidate, cell_state, model_ctx, w_eig=w_eig, w_imm=w_imm)["acquisition"]
