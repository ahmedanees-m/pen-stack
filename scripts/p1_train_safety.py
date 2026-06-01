"""Train + evaluate the Phase-1 safety layer on a cell type (Step 1.6).

Joins chromatin + safety annotations, trains the calibrated genotoxicity model with chromosome-block
CV, and reports model-vs-baseline AUROC/AUPRC. Writes the model + a JSON report.

    python scripts/p1_train_safety.py --ct k562
"""
import argparse
import json
import pickle
from pathlib import Path

from pen_stack.wgenome.features import assemble_matrix
from pen_stack.wgenome.safety import train_safety


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ct", default="k562")
    ap.add_argument("--feat-dir", default="/data/features")
    ap.add_argument("--out-dir", default="/data/out")
    ap.add_argument("--label", default="genotoxic_cis")
    a = ap.parse_args()

    integ = Path(a.feat_dir) / f"integration_{a.ct}.parquet"
    m = assemble_matrix(
        f"{a.feat_dir}/chromatin_{a.ct}.parquet",
        f"{a.feat_dir}/safety_annot.parquet",
        str(integ) if integ.exists() else None,
    )
    res = train_safety(m, label=a.label)

    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    with open(f"{a.out_dir}/safety_{a.ct}.pkl", "wb") as fh:
        pickle.dump(res["model"], fh)
    report = {k: res[k] for k in ("n", "n_pos", "features", "auroc_model", "auprc_model",
                                  "auroc_baseline", "auprc_baseline", "auroc_delta",
                                  "feature_importance")}
    Path(f"{a.out_dir}/safety_{a.ct}_report.json").write_text(json.dumps(report, indent=2))
    print(f"[safety {a.ct}] n={report['n']} n_pos={report['n_pos']}")
    print(f"  AUROC model={report['auroc_model']:.4f}  baseline={report['auroc_baseline']:.4f}  "
          f"delta={report['auroc_delta']:+.4f}")
    print(f"  AUPRC model={report['auprc_model']:.4f}  baseline={report['auprc_baseline']:.4f}")
    top = list(report["feature_importance"].items())[:6]
    print(f"  top features: {top}")


if __name__ == "__main__":
    main()
