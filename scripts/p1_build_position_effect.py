"""Build the v6.7 PEN-EXPRESS position-effect model + trained-conformal artifact (WS-M + WS-U).

Runs the chromosome-blocked CV (learned factored model vs the context-only durability head + cassette-only),
fits the final model, calibrates split-conformal on the OOF residuals, fits the OOD detector, and writes:
  * models/position_effect.pkl (gitignored, the trained model bundle; regenerate with this script)
  * configs/twin/position_effect_conformal.json (committed, the shipped calibration: qhat + N + coverage)
  * out/position_effect_report.json (the real CV metrics, incl. negatives)

Every number is from a real CV run on real TRIP supervision. No fabrication. Gate G-M is evaluated and
printed; the model is still saved (Stage H decides whether to *serve* it based on the gate, see twin/outcome.py).
"""
from __future__ import annotations

import json
import sys

from pen_stack._resources import project_root
from pen_stack.twin.data.position_effect import load_position_effect
from pen_stack.twin.position_effect import (
    PositionEffectModel,
    calibrate_conformal,
    conformal_heldout_coverage,
    evaluate,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception: # noqa: BLE001
    pass

ROOT = project_root()


def main() -> None:
    df = load_position_effect()
    print(f"position-effect table: {df.shape} | datasets={df.attrs.get('datasets')} "
          f"| skipped(not fetched)={df.attrs.get('skipped')}")

    rep = evaluate(df)
    e, s = rep["expression"], rep["silenced"]
    print("\n=== chromosome-blocked CV (real TRIP supervision) ===")
    print(f"expression Spearman: factored={e['rho_factored']:.4f} "
          f"context-only(durability head)={e['rho_context_only_durability_head']:.4f} "
          f"cassette-only={e['rho_cassette_only']:.4f}")
    print(f" delta factored-vs-context: {e['delta_factored_vs_context']}")
    print(f"silenced AUROC: factored={s['auroc_factored']:.4f} "
          f"context-only(durability head)={s['auroc_context_only_durability_head']:.4f}")
    print(f" delta factored-vs-context: {s['delta_factored_vs_context']}")
    print(f"separability (interaction): {rep['separability']}")

    # gate G-M
    beats_expr = e["delta_factored_vs_context"]["excludes_zero"] and e["delta_factored_vs_context"]["delta_mean"] > 0
    beats_sil = s["delta_factored_vs_context"]["excludes_zero"] and s["delta_factored_vs_context"]["delta_mean"] > 0
    gate = {"beats_durability_head_expression": bool(beats_expr),
            "beats_durability_head_silenced": bool(beats_sil),
            "verdict": ("learned model beats the durability head, serve it behind Stage H"
                        if (beats_expr or beats_sil) else
                        "learned model does NOT beat the durability head at this N, retain head/heuristic, "
                        "report negative; v6.7 value rests on trained-conformal intervals + TPE-Bench")}
    print(f"\nGATE G-M: {gate['verdict']}")

    # fit final + conformal + ood
    model = PositionEffectModel().fit(df)
    conf = calibrate_conformal(rep["_oof"], alpha=0.10)
    model.conformal = conf
    cov = conformal_heldout_coverage(rep["_oof"], alpha=0.10)
    print(f"\nconformal (alpha=0.10): qhat(all-OOF)={conf.qhat:.4f} n_cal={conf.n_cal} | "
          f"HELD-OUT coverage={cov['heldout_coverage']:.3f} (nominal {cov['nominal']}) "
          f"mean_width={cov['mean_width']:.3f} within_tol={cov['within_tol']}")

    # save artifacts
    (ROOT / "models").mkdir(exist_ok=True)
    model.save(ROOT / "models/position_effect.pkl")
    conf_path = ROOT / "configs/twin/position_effect_conformal.json"
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    conf_path.write_text(json.dumps({
        "alpha": conf.alpha, "nominal_coverage": 1 - conf.alpha, "qhat": conf.qhat,
        "qhat_by_group": conf.qhat_by_group, "n_cal": conf.n_cal,
        "heldout_coverage": cov["heldout_coverage"], "mean_width": cov["mean_width"],
        "within_tol": cov["within_tol"],
        "note": "trained split-conformal on chromosome-blocked OOF residuals of the position-effect model "
                "(TRIP supervision). qhat is calibrated on all OOF residuals; heldout_coverage is the "
                "half-chromosome held-out validation. Ships the calibration, not the calibration data.",
    }, indent=2), encoding="utf-8")

    # full report (gitignored out/, mirrored into the execution summary + docs)
    out = {k: v for k, v in rep.items() if k != "_oof"}
    out["gate_G_M"] = gate
    out["conformal"] = {"alpha": conf.alpha, "qhat": conf.qhat, "n_cal": conf.n_cal,
                        "heldout_coverage": cov["heldout_coverage"], "mean_width": cov["mean_width"],
                        "within_tol": cov["within_tol"]}
    out["data"] = {"datasets": df.attrs.get("datasets"), "skipped_not_fetched": df.attrs.get("skipped"),
                   "n": int(len(df)), "cell_types": sorted(df["cell_type"].unique()),
                   "transfer_axis": "data-gated: single available cell type (mESC); held-out-cell-type "
                                    "transfer pending PatchMPRA/MPIRE/lentiMPRA/Leemans acquisition"}
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out/position_effect_report.json").write_text(json.dumps(out, indent=2, default=float),
                                                          encoding="utf-8")
    print(f"\nsaved: models/position_effect.pkl, {conf_path.relative_to(ROOT)}, out/position_effect_report.json")


if __name__ == "__main__":
    main()
