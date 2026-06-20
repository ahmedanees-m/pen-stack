"""Build the v6.8 Stage C writer-efficiency artifacts (C-WS1 + C-WS2).

Builds the curated dataset parquet, runs the held-out-family + held-out-locus evaluation vs the KB family-mean
baseline (the gate C-G2), calibrates a family-blocked split-conformal interval, fits the final model, and
writes:
  * data/writer_efficiency.parquet (committed, the curated dataset, the contribution)
  * models/writer_eff.pkl (gitignored, regenerate with this script)
  * configs/atlas/writer_eff_conformal.json (committed, the shipped calibration)
  * out/writer_eff_report.json (the real CV report, incl. the negative)

Every efficiency is a real published number with a DOI + verbatim quote (see atlas/writer_efficiency.py). No
fabrication. The gate result is reported verbatim, a non-both-axes win retains the KB ranking.
"""
from __future__ import annotations

import json
import sys

from pen_stack._resources import project_root
from pen_stack.atlas import writer_efficiency as we
from pen_stack.atlas import writer_predict as wp

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception: # noqa: BLE001
    pass

ROOT = project_root()


def main() -> None:
    ds = we.build_parquet()
    prov = we.provenance_summary()
    print(f"curated dataset: {prov['n_records']} records ({prov['n_human']} human-cell), "
          f"{prov['n_dois']} DOIs, families={prov['by_family']}, access={prov['by_source_access']}")

    rep = wp.evaluate()
    for axis in ("held_out_family", "held_out_locus"):
        a = rep[axis]
        print(f"\n{axis}: MAE model={a['mae_model']:.2f} vs KB family-mean={a['mae_baseline_family_mean']:.2f} "
              f"| Spearman model={a['spearman_model']:.3f} vs baseline={a['spearman_baseline']:.3f}")
        print(f" MAE-reduction CI: {a['delta']['ci95']} excludes0={a['delta']['model_beats_baseline']}")
    print(f"\nGATE C-G2: {rep['gate_C_G2']['verdict']}")

    conf = wp.calibrate(alpha=0.10)
    model = wp.WriterEfficiencyModel().fit()
    model.conformal = conf
    model.save(ROOT / "models/writer_eff.pkl")
    conf_path = ROOT / "configs/atlas/writer_eff_conformal.json"
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    conf_path.write_text(json.dumps({"alpha": conf.alpha, "qhat": conf.qhat, "n_cal": conf.n_cal,
                                     "units": "percent_integration",
                                     "note": "family-blocked LOO OOF split-conformal on the curated writer-"
                                             "efficiency dataset; candidate-flagged interval."}, indent=2),
                         encoding="utf-8")
    print(f"\nconformal: qhat={conf.qhat:.2f}% (alpha=0.10, n_cal={conf.n_cal})")

    rep["dataset"] = prov
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out/writer_eff_report.json").write_text(json.dumps(rep, indent=2, default=float), encoding="utf-8")
    print(f"\nsaved: {ds.relative_to(ROOT)}, models/writer_eff.pkl, {conf_path.relative_to(ROOT)}, "
          f"out/writer_eff_report.json")


if __name__ == "__main__":
    main()
