"""Writer recommender, the surface that ties writer selection together.

Given a write request `(write-type, cargo size, cell type, optional target/donor sequences)`, returns ranked
writer families with:
  * the **KB readiness** (PRIMARY ranking, the curated Writer Atlas; retained per the pre-registered gate),
  * a **predicted efficiency + conformal interval**, candidate-flagged (the learned predictor, an advisory, NOT
    the authoritative ranking, because at N=42/4-families it does not beat the KB baseline on held-out family),
  * **cargo-capacity fit** (does the family carry this cargo?),
  * an **auto-designed guide** (bridge RNA / pegRNA+attB) when sequences are supplied.

Scope: efficiency predictions are candidates with intervals; the KB ranking is the grounded primary. No
fabricated efficiency is ever emitted (the predictor is trained only on the curated real dataset).
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from pen_stack._resources import project_root


@lru_cache(maxsize=1)
def _wtkb() -> pd.DataFrame:
    return pd.read_parquet(project_root() / "pen_stack/atlas/wtkb.parquet")


@lru_cache(maxsize=1)
def _eff_model():
    """Load the learned efficiency model artifact if present; else None (KB-only recommendation)."""
    from pen_stack.atlas.writer_predict import WriterEfficiencyModel
    p = project_root() / "models/writer_eff.pkl"
    try:
        return WriterEfficiencyModel.load(p) if p.exists() else None
    except Exception: # noqa: BLE001
        return None


def _kb_readiness(row) -> float:
    """A transparent KB readiness in [0,1] from the curated atlas fields: DSB-free (writing-relevant) + measured
    human-cell activity + cargo headroom. PRIMARY ranking signal (grounded, not learned)."""
    dsb_free = 1.0 if bool(row.get("dsb_free")) else 0.0
    measured = 1.0 if str(row.get("confidence")) == "measured" else (0.5 if str(row.get("confidence")) == "inferred" else 0.25)
    act = str(row.get("human_cell_activity") or "").lower()
    human = 1.0 if ("%" in act or "high" in act) and "not measured" not in act and "low" not in act else (
        0.3 if "low" in act or "not measured" in act else 0.6)
    return round(0.4 * dsb_free + 0.35 * measured + 0.25 * human, 3)


# Mechanism-grounded write-type suitability. A cargo write (insertion / landing-pad) NEEDS a cargo-carrying writer;
# an excision NEEDS a programmable cutter. This is molecular MECHANISM (a cargo installer vs a cutter), NOT an
# efficacy prediction -- a transparent, labelled tier so the write-type selector actually shapes the ranking.
_CARGO_WRITES = frozenset({"insertion", "knock_in_with_disruption", "landing_pad_insertion", "high_durability_insertion"})
_EXCISION_WRITES = frozenset({"excision", "repeat_excision", "regulatory_element_excision", "regulatory_excision"})
WRITE_TYPES = _CARGO_WRITES | _EXCISION_WRITES | frozenset({"inversion"})


# Families that catalyse site-specific INVERSION (reversible recombination between two inverted sites): the serine
# integrases (invert between inverted att) and the IS110/IS1111 bridge recombinases (Durrant 2024); a PE-installed
# att inherits the serine mechanism. The CAST transposase is unidirectional INSERTION only, and DSB nucleases invert
# only imprecisely via dual cuts -- so those are not the mechanism for a clean inversion.
_INVERSION_RECOMBINASES = frozenset({"serine_integrase", "PE_integrase", "bridge_IS110", "seek_IS1111"})


def _write_type_suitability(write_type: str, family: str, carries_cargo: bool) -> int:
    """Mechanism suitability TIER (1 = the right mechanism class for this write type, 0 = a poorer fit). Grounded
    in mechanism, never an efficacy claim: a cargo write needs a cargo carrier; an excision needs a programmable
    cutter; an inversion needs a site-specific recombinase."""
    if write_type in _CARGO_WRITES:
        return 1 if carries_cargo else 0             # nucleases can knock-in via HDR but do not deliver large cargo
    if write_type in _EXCISION_WRITES:
        return 0 if carries_cargo else 1             # a cut/excise favours a programmable cutter, not an installer
    if write_type == "inversion":
        return 1 if family in _INVERSION_RECOMBINASES else 0  # only site-specific recombinases invert cleanly
    return 1                                         # other: neutral (no grounded reweight)


def recommend_writers(request: dict, top_k: int = 5) -> dict:
    """Rank writer families for a write request. KB readiness is primary; learned efficiency is a candidate
    advisory; guide design attached when sequences are supplied."""
    cargo_bp = float(request.get("cargo_bp") or 0)
    cell_type = request.get("cell_type") or "HEK293T"
    # `write_type` is the documented key; `intent` is accepted as a synonym because the planner CLI names the same
    # idea `--intent`, so a request that uses it is honoured instead of silently falling back to the default
    # insertion. An unrecognized value still ranks neutrally, but says so via `write_type_recognized` below rather
    # than looking like a shaped ranking.
    write_type = request.get("write_type") or request.get("intent") or "insertion"
    target_seq, donor_seq = request.get("target_seq"), request.get("donor_seq")
    model = _eff_model()
    rows = []
    for _, r in _wtkb().iterrows():
        cap = float(r["cargo_capacity_bp"]) if pd.notna(r.get("cargo_capacity_bp")) else 0.0
        cargo_fit = (cap >= cargo_bp) if (cargo_bp and cap) else None
        rec = {
            "family": r["family"], "representative_system": r["representative_system"],
            "kb_readiness": _kb_readiness(r), "dsb_free": bool(r.get("dsb_free")),
            "write_type_suitability": _write_type_suitability(write_type, r["family"], cap > 0),  # mechanism fit
            "cargo_capacity_bp": int(cap) if cap else None,
            "cargo_fit": cargo_fit, "confidence": str(r.get("confidence")),
            "key_dois": [str(x) for x in r.get("key_dois")] if r.get("key_dois") is not None else [],
        }
        # learned efficiency (candidate advisory), ONLY for families present in the curated dataset (never
        # extrapolate an efficiency to an unseen family; KB-only for those, no fabrication).
        if model is not None and r["family"] in model.meta.get("families", []):
            try:
                df = pd.DataFrame([{"family": r["family"], "variant": "engineered",
                                    "cargo_bp": max(cargo_bp, 1000), "cell_type": cell_type,
                                    "delivery": "plasmid"}])
                iv = model.predict_interval(df)
                if iv.get("lo") is not None:
                    rec["predicted_efficiency_pct"] = round(float(iv["yhat"][0]), 1)
                    rec["efficiency_interval_pct"] = [round(float(iv["lo"][0]), 1), round(float(iv["hi"][0]), 1)]
                    rec["efficiency_kind"] = "candidate (learned; interval = trained split-conformal)"
            except Exception: # noqa: BLE001 - family unseen by the model -> KB-only, never fabricate
                pass
        # guide design when sequences supplied
        if target_seq:
            from pen_stack.atlas.guide_design import design_guide_for_writer
            g = design_guide_for_writer(r["family"], target_seq, donor_seq)
            if g.get("available"):
                # surface the DESIGNED sequences (spacer / attB / bridge loops), not just a bare flag
                rec["guide_design"] = {"type": g["design_type"], "feasible": g.get("feasible"),
                                       "design": g.get("design")}
        rows.append(rec)

    # rank by mechanism suitability for the write type FIRST (grounded tier), then the grounded KB readiness within
    # tier, then cargo fit. For the default insertion this is unchanged (cargo carriers already lead); an excision
    # promotes programmable cutters over cargo installers.
    rows.sort(key=lambda x: (x["write_type_suitability"], x["kb_readiness"], x.get("cargo_fit") is True), reverse=True)
    if cargo_bp:
        rows = [x for x in rows if x["cargo_fit"] is not False] + [x for x in rows if x["cargo_fit"] is False]
    wt_note = None
    if write_type in _EXCISION_WRITES:
        wt_note = (f"Ranking shaped for a {write_type.replace('_', ' ')}: programmable cutters are favoured over "
                   "cargo-installing integrases, which are the tool for insertion, not excision. Mechanism-based "
                   "modifier, not an efficacy claim.")
    elif write_type in _CARGO_WRITES:
        wt_note = (f"Ranking shaped for a {write_type.replace('_', ' ')}: cargo-carrying writers (integrases / "
                   "transposons) are favoured; nucleases can knock in via HDR but do not deliver a large cargo.")
    elif write_type == "inversion":
        wt_note = ("Ranking shaped for an inversion: site-specific recombinases (serine integrases, IS110/IS1111 "
                   "bridge recombinases) that invert between inverted sites are favoured; the CAST transposase is "
                   "insertion-only and DSB nucleases invert only imprecisely via dual cuts. Mechanism-based "
                   "modifier, not an efficacy claim.")
    # Cargo-capacity check: when a cargo is requested that NO cargo-carrying writer in the atlas can hold, the
    # top of the ranking is nucleases (which don't deliver cargo, cargo_fit=n/a) or over-capacity integrases --
    # surface that explicitly so Cas9 does not read as a silent #1 recommendation for an impossible payload.
    cargo_warning = None
    if cargo_bp:
        caps = [x["cargo_capacity_bp"] for x in rows if x["cargo_capacity_bp"]]
        max_cap = max(caps) if caps else 0
        if max_cap and cargo_bp > max_cap:
            cargo_warning = (
                f"No writer in the atlas carries a {int(cargo_bp):,} bp cargo -- the largest cargo capacity is "
                f"{int(max_cap):,} bp. Families marked 'over capacity' exceed their limit; nucleases (cargo fit "
                f"n/a) do not deliver cargo at all. Consider splitting the payload or a dual-vector strategy.")
    return {
        "request": {"write_type": write_type, "write_type_recognized": write_type in WRITE_TYPES,
                    "cargo_bp": cargo_bp or None, "cell_type": cell_type},
        "ranking_basis": "mechanism suitability for the write type, then KB readiness (grounded); predicted "
                         "efficiency is a candidate advisory",
        "recommendations": rows[:top_k],
        "n_families": len(rows),
        "write_type_note": wt_note,
        "cargo_capacity_warning": cargo_warning,
        "no_fabrication": True,
        "note": "Writer Atlas KB ranking is the grounded primary; learned efficiencies are candidates with "
                "conformal intervals (the learned model does not beat the KB baseline on held-out family "
                "at this N). Guide designs are candidates requiring empirical validation.",
    }
