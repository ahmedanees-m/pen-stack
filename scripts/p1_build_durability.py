"""Build + evaluate the durability conditional model (Phase 1, Step 1.7).

Resolve mouse-ES (ES-Bruce4, mm10) chromatin -> lift TRIP mm9->mm10 -> point-query chromatin at each
integration -> train chromatin->expression. Reports Spearman/AUROC vs simple baselines.

    python scripts/p1_build_durability.py
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from pen_stack.data.encode import resolve_panel
from pen_stack.data.ingest_chromatin import download
from pen_stack.wgenome.durability import (
    extract_chromatin_at,
    liftover_positions,
    save_models,
    train_durability,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trip", default="/data/features/trip_mesc.parquet")
    ap.add_argument("--chain", default="/data/external/mm9ToMm10.over.chain.gz")
    ap.add_argument("--biosample", default="ES-Bruce4")
    ap.add_argument("--raw-dir", default="/data/raw/encode_mes")
    ap.add_argument("--feat-out", default="/data/features/trip_with_chromatin.parquet")
    ap.add_argument("--out-dir", default="/data/out")
    a = ap.parse_args()

    trip = pd.read_parquet(a.trip)
    print(f"TRIP integrations (mm9): {len(trip)}")
    trip = liftover_positions(trip, a.chain)
    print(f"lifted to mm10: {len(trip)}")

    panel = resolve_panel(a.biosample, assembly="mm10")
    print(f"mES panel ({a.biosample}): {list(panel.keys())}")

    Path(a.raw_dir).mkdir(parents=True, exist_ok=True)
    feat = extract_chromatin_at(trip, panel, a.raw_dir, download)
    feat.to_parquet(a.feat_out, index=False)

    res = train_durability(feat)
    save_models(res, a.out_dir)
    report = {k: res[k] for k in ("n", "features", "expr_spearman", "expr_baseline_atac_spearman",
                                  "silenced_auroc", "silenced_baseline_h3k9me3_auroc", "feature_importance")}
    Path(f"{a.out_dir}/durability_report.json").write_text(json.dumps(report, indent=2))
    print("\n=== DURABILITY MODEL ===")
    print(f"n={report['n']} features={report['features']}")
    print(f"  expression Spearman rho:  model={report['expr_spearman']:.3f}  "
          f"baseline(ATAC)={report['expr_baseline_atac_spearman']:.3f}")
    print(f"  silenced/stable AUROC:    model={report['silenced_auroc']:.3f}  "
          f"baseline(H3K9me3)={report['silenced_baseline_h3k9me3_auroc']:.3f}")
    print(f"  top features: {list(report['feature_importance'].items())[:5]}")


if __name__ == "__main__":
    main()
