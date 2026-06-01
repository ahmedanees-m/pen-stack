"""Consolidated Phase-1 blind-validation report (Step 1.10).

Gathers the per-layer results (safety concordance, durability transfer, atlas safe-harbour separation
for each cell type) into one report and checks them against the pre-registered Paper-1 criteria.

    python scripts/p1_validation_report.py
"""
import argparse
import json
from pathlib import Path

import yaml


def _load(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/data/out")
    ap.add_argument("--prereg", default="prereg/paper1.yaml")
    ap.add_argument("--cts", nargs="+", default=["k562", "hepg2"])
    a = ap.parse_args()
    o = Path(a.out_dir)
    prereg = yaml.safe_load(Path(a.prereg).read_text()) if Path(a.prereg).exists() else {}

    dur = _load(o / "durability_report.json")
    report = {"durability": None, "atlas": {}, "prereg_checks": {}}

    if dur:
        report["durability"] = {
            "expr_spearman": dur["expr_spearman"],
            "silenced_auroc": dur["silenced_auroc"],
            "silenced_baseline_h3k9me3_auroc": dur["silenced_baseline_h3k9me3_auroc"],
            "beats_baseline": dur["silenced_auroc"] > dur["silenced_baseline_h3k9me3_auroc"],
        }
        crit = prereg.get("durability_layer", {}).get("success", {})
        report["prereg_checks"]["durability_spearman>=0.30"] = dur["expr_spearman"] >= crit.get(
            "function_transfer_spearman_min", 0.30)
        report["prereg_checks"]["durability_beats_baseline"] = report["durability"]["beats_baseline"]

    for ct in a.cts:
        s = _load(o / f"atlas_{ct}_sanity.json")
        if s:
            report["atlas"][ct] = {
                "safe_harbour_writability_mean": s["safe_mean"],
                "genotoxic_cis_writability_mean": s["gtox_mean"],
                "safe_more_writable": s["safe_mean"] > s["gtox_mean"],
                "loci": s["loci"],
            }
            report["prereg_checks"][f"atlas_{ct}_safe>genotoxic"] = s["safe_mean"] > s["gtox_mean"]

    # cross-cell-type degradation (honest result): compare safe-harbour separation across cts
    if len(report["atlas"]) >= 2:
        seps = {ct: v["safe_harbour_writability_mean"] - v["genotoxic_cis_writability_mean"]
                for ct, v in report["atlas"].items()}
        report["cross_cell_type_separation"] = seps

    report["all_prereg_checks_pass"] = all(report["prereg_checks"].values()) if report["prereg_checks"] else False
    (o / "validation_report.json").write_text(json.dumps(report, indent=2))

    print("=== PHASE 1 VALIDATION REPORT ===")
    if report["durability"]:
        d = report["durability"]
        print(f"Durability: Spearman={d['expr_spearman']:.3f}  silenced AUROC={d['silenced_auroc']:.3f} "
              f"(baseline {d['silenced_baseline_h3k9me3_auroc']:.3f}, beats={d['beats_baseline']})")
    for ct, v in report["atlas"].items():
        print(f"Atlas {ct}: safe-harbour writability={v['safe_harbour_writability_mean']:.3f} "
              f"vs genotoxic-CIS={v['genotoxic_cis_writability_mean']:.3f}  "
              f"(safe>genotoxic={v['safe_more_writable']})")
    print("\nPre-registered checks:")
    for k, v in report["prereg_checks"].items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nALL PRE-REGISTERED CHECKS PASS: {report['all_prereg_checks_pass']}")


if __name__ == "__main__":
    main()
