"""Writer recommender, the Stage C surface that ties it together (v6.8 PEN-WRITER, C-WS5).

Given a write request `(write-type, cargo size, cell type, optional target/donor sequences)`, returns ranked
writer families with:
  * the **KB readiness** (PRIMARY ranking, the curated Writer Atlas; retained per gate C-G2),
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


def recommend_writers(request: dict, top_k: int = 5) -> dict:
    """Rank writer families for a write request. KB readiness is primary; learned efficiency is a candidate
    advisory; guide design attached when sequences are supplied."""
    cargo_bp = float(request.get("cargo_bp") or 0)
    cell_type = request.get("cell_type") or "HEK293T"
    write_type = request.get("write_type") or "insertion"
    target_seq, donor_seq = request.get("target_seq"), request.get("donor_seq")
    model = _eff_model()
    rows = []
    for _, r in _wtkb().iterrows():
        cap = float(r["cargo_capacity_bp"]) if pd.notna(r.get("cargo_capacity_bp")) else 0.0
        cargo_fit = (cap >= cargo_bp) if (cargo_bp and cap) else None
        rec = {
            "family": r["family"], "representative_system": r["representative_system"],
            "kb_readiness": _kb_readiness(r), "dsb_free": bool(r.get("dsb_free")),
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
                rec["guide_design"] = {"type": g["design_type"], "feasible": g.get("feasible", True)}
        rows.append(rec)

    rows.sort(key=lambda x: (x["kb_readiness"], x.get("cargo_fit") is True), reverse=True)
    if cargo_bp:
        rows = [x for x in rows if x["cargo_fit"] is not False] + [x for x in rows if x["cargo_fit"] is False]
    return {
        "request": {"write_type": write_type, "cargo_bp": cargo_bp or None, "cell_type": cell_type},
        "ranking_basis": "KB readiness (PRIMARY, grounded); predicted efficiency is a candidate advisory",
        "recommendations": rows[:top_k],
        "n_families": len(rows),
        "no_fabrication": True,
        "note": "Writer Atlas KB ranking is the grounded primary; learned efficiencies are candidates with "
                "conformal intervals (gate C-G2: learned model does not beat the KB baseline on held-out family "
                "at this N). Guide designs are candidates requiring empirical validation.",
    }
