"""Build the COMPUTED genotoxicity-oracle artifact (v5.2, WS-GENOTOX).

For each integrating-vector CLASS we compute, from real data, how strongly its integration sites land near
known oncogenes — the data-grounded genotoxicity signal that replaces the hard-coded `genotoxicity` tier in
configs/delivery_vehicles.yaml for integrating vehicles:

    risk(class)       = P(an integration site of this class falls within `window_bp` of a COSMIC Cancer-Gene-
                        Census oncogene)              [observed fraction over the class's site catalogue]
    enrichment(class) = risk(class) / genome_background_frac        [fold over a random-bin baseline]
    genotox_score     = min(1, 1 / enrichment)        [1 = safest; episomal/non-targeting ~ 1.0]

Inputs (staged on the VM under /data; NOT shipped — this script runs where the data lives):
  - /data/external/visdb/*.csv          VISDB per-virus integration-site catalogues (hg38)  [10.1093/nar/gkz867]
  - /data/features/safety_annot.parquet per-1kb-bin dist_oncogene + genotoxic_cis (COSMIC CGC v104)
                                                                                  [COSMIC 10.1038/s41568-018-0060-1]
HIV ~= lentiviral integration biology (favors active gene bodies) [10.1016/S0092-8674(02)00864-4];
MLV ~= gammaretroviral (favors TSS/enhancers -> the LMO2 / SCID-X1 genotoxicity)  [10.1126/science.1083413].

Output: a SMALL, committable YAML (configs/genotoxicity_oracle.yaml) of per-class summary statistics +
provenance — the raw catalogues stay on the VM; only the auditable summary ships. Magnitude (in-vivo clonal
outcome) is NOT modelled here and stays the `in_vivo_immunogenicity` / clonal known-unknown.

Run (on the VM, in the data-mounted image):
    docker run --rm --entrypoint "" -v ~/data:/data -v ~/penstack:/app -w /app penstack:phase1.5 \\
        python scripts/p52_build_genotox_oracle.py > configs/genotoxicity_oracle.yaml
"""
from __future__ import annotations

import datetime as _dt
import glob
import os
import sys

import pandas as pd
import yaml

WINDOW_BP = 50_000
SAFETY_ANNOT = "/data/features/safety_annot.parquet"
VISDB_DIR = "/data/external/visdb"
ROBUST_MIN_N = 1000            # below this, a class is directional-only (flagged extrapolating)

# VISDB virus -> integration biology class + the palette vehicle(s) it grounds.
VIRUS_CLASS = {"HIV": "lentiviral", "HTLV": "deltaretroviral",
               "MLV": "gammaretroviral", "XMLV": "gammaretroviral"}
# which palette vehicles each computed class grounds (others are non-integrating -> handled by mechanism)
CLASS_VEHICLES = {"lentiviral": ["lentivirus"]}

PROVENANCE_DOIS = ["10.1093/nar/gkz867", "10.1038/s41568-018-0060-1",
                   "10.1016/S0092-8674(02)00864-4", "10.1126/science.1083413"]


def _sites(csv: str, main_chroms: set[str]) -> pd.DataFrame:
    df = pd.read_csv(csv, dtype=str)
    cols = {c.lower().strip(): c for c in df.columns}
    cc, sc = cols.get("human chromosome"), cols.get("hg38_start")
    if not cc or not sc:
        return pd.DataFrame(columns=["chrom", "bin"])
    d = pd.DataFrame({
        "chrom": df[cc].astype(str).map(lambda x: x if x.startswith("chr") else f"chr{x}"),
        "pos": pd.to_numeric(df[sc], errors="coerce")}).dropna()
    d = d[d["chrom"].isin(main_chroms)].copy()
    d["bin"] = (d["pos"].astype(int) // 1000)
    return d[["chrom", "bin"]]


def build() -> dict:
    sa = pd.read_parquet(SAFETY_ANNOT)[["chrom", "bin", "dist_oncogene", "genotoxic_cis"]]
    main = set(sa["chrom"].unique())
    background = float((sa["dist_oncogene"] <= WINDOW_BP).mean())

    classes: dict[str, dict] = {}
    for csv in sorted(glob.glob(os.path.join(VISDB_DIR, "*.csv"))):
        virus = os.path.basename(csv).replace(".csv", "")
        cls = VIRUS_CLASS.get(virus)
        if cls is None:
            continue
        m = _sites(csv, main).merge(sa, on=["chrom", "bin"], how="inner")
        n = int(len(m))
        if n == 0:
            continue
        frac = float((m["dist_oncogene"] <= WINDOW_BP).mean())
        ci95 = float(1.96 * (frac * (1 - frac) / n) ** 0.5)
        enrich = float(frac / background) if background else None
        rec = {"virus": virus, "n_sites": n,
               "frac_oncogene_50kb": round(frac, 5), "ci95": round(ci95, 5),
               "enrichment": round(enrich, 3) if enrich else None,
               "frac_genotoxic_cis": round(float(m["genotoxic_cis"].mean()), 6),
               "median_dist_oncogene": int(m["dist_oncogene"].median()),
               "robust": n >= ROBUST_MIN_N}
        # keep the larger-n catalogue if a class has multiple viruses (e.g. gammaretro: MLV+XMLV)
        if cls not in classes or n > classes[cls]["n_sites"]:
            classes[cls] = rec

    return {
        "version": "1.0",
        "built": _dt.date.today().isoformat(),
        "description": ("computed integration-site genotoxicity oracle: per vector class, the observed "
                        "enrichment of integration sites within window_bp of a COSMIC oncogene vs genome "
                        "background. genotox_score = min(1, 1/enrichment). In-vivo clonal outcome is NOT "
                        "modelled (stays a known-unknown)."),
        "window_bp": WINDOW_BP,
        "genome_background_frac_oncogene_50kb": round(background, 5),
        "inputs": {"visdb": "VISDB per-virus hg38 catalogues", "oncogenes": "COSMIC CGC v104 (safety_annot)"},
        "provenance_dois": PROVENANCE_DOIS,
        "robust_min_n": ROBUST_MIN_N,
        "classes": classes,
        "vehicle_class": CLASS_VEHICLES,
    }


if __name__ == "__main__":
    yaml.safe_dump(build(), sys.stdout, sort_keys=False, default_flow_style=False)
