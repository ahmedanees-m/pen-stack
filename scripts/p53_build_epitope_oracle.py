"""Build the COMPUTED capsid T-cell-epitope-load oracle artifact (v5.3, WS-EPITOPE).

For each VIRAL vector's capsid/envelope antigen we compute, from the protein sequence, how much of it is
presentable to CD8 T cells across a reference panel of frequent HLA-I alleles — the data-grounded
adaptive-immunogenicity signal that refines the documented `adaptive_immune` tier in
configs/delivery_vehicles.yaml:

    for every overlapping 9-mer x every panel allele -> MHCflurry affinity percentile rank;
    a 9-mer is a STRONG binder for an allele if %rank <= 0.5;
    epitope_fraction = (capsid residues covered by >=1 strong-binder 9-mer for >=1 allele) / length;
    capsid_immune_score = 1 - epitope_fraction          # 1 = least presentable / least immunogenic

This is the NetMHC-style calculation the user asked for, made population-level (averaged over a frequent-allele
panel) so it is NOT a patient-HLA-specific magnitude. Inputs are committed (configs/capsid_sequences.fasta,
fetched + verified from UniProt) so the run needs no network and is reproducible. Answers through the v4.0
OracleResult contract (output_kind="baseline").

Sequences (UniProt, verified): AAV2 VP1 P03135; Ad5 hexon P04133; VSV-G Indiana P03522 (LV pseudotyping
antigen); HSV-1 gD P57083 + gB P06437. Method: MHCflurry 2.0 [10.1016/j.cels.2020.06.010]; HLA-I frequent-
allele panel / supertypes [10.1186/1471-2172-9-1].

Run (on the VM, in the dedicated mhcflurry image):
    docker run --rm -v ~/penstack:/app -w /app penstack:mhcflurry \\
        python scripts/p53_build_epitope_oracle.py > configs/capsid_epitope_oracle.yaml
"""
from __future__ import annotations

import datetime as _dt
import sys

import yaml

# frequent HLA-I alleles giving broad population / supertype coverage (Sidney 2008).
HLA_PANEL = ["HLA-A*01:01", "HLA-A*02:01", "HLA-A*03:01", "HLA-A*11:01", "HLA-A*24:02", "HLA-A*26:01",
             "HLA-B*07:02", "HLA-B*08:01", "HLA-B*15:01", "HLA-B*40:01", "HLA-B*44:03", "HLA-B*58:01"]
PEPTIDE_LEN = 9
STRONG_RANK = 0.5          # %rank <= 0.5 => strong binder
BINDER_RANK = 2.0          # %rank <= 2.0 => binder
FASTA = "configs/capsid_sequences.fasta"

# which committed sequence(s) is the immunogenic antigen for each VIRAL vehicle (others are non-viral).
VEHICLE_ANTIGENS = {
    "AAV_single": ["AAV2_VP1"], "AAV_dual": ["AAV2_VP1"],
    "lentivirus": ["VSVg_Indiana"],              # VSV-G pseudotyping antigen (surface)
    "helper_dependent_adenovirus": ["Ad5_hexon"],
    "hsv_amplicon": ["HSV1_gD", "HSV1_gB"],      # two major HSV envelope antigens (averaged)
}
PROVENANCE_DOIS = ["10.1016/j.cels.2020.06.010", "10.1186/1471-2172-9-1"]


def _read_fasta(path: str) -> dict[str, str]:
    seqs, name = {}, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip()
        if line.startswith(">"):
            name = line[1:].split("|")[0]
            seqs[name] = ""
        elif name:
            seqs[name] += line
    return seqs


def _protein_stats(seq: str, predictor) -> dict:
    # overlapping 9-mers; predict affinity percentile rank PER allele across the panel, then union-cover
    # residues by any strong-binder 9-mer for any allele.
    peptides = [seq[i:i + PEPTIDE_LEN] for i in range(len(seq) - PEPTIDE_LEN + 1)]
    valid = [(i, p) for i, p in enumerate(peptides) if set(p) <= set("ACDEFGHIKLMNPQRSTVWY")]
    starts = [i for i, _ in valid]
    peps = [p for _, p in valid]
    covered_strong, covered_binder = set(), set()
    n_strong_pairs = 0
    for allele in HLA_PANEL:
        df = predictor.predict_to_dataframe(peptides=peps, allele=allele)
        ranks = df["prediction_percentile"].values
        for k, rank in enumerate(ranks):
            start = starts[k]
            if rank <= BINDER_RANK:
                covered_binder.update(range(start, start + PEPTIDE_LEN))
            if rank <= STRONG_RANK:
                covered_strong.update(range(start, start + PEPTIDE_LEN))
                n_strong_pairs += 1
    L = len(seq)
    return {"length": L, "n_9mers": len(peps),
            "epitope_fraction_strong": round(len(covered_strong) / L, 4),
            "epitope_fraction_binder": round(len(covered_binder) / L, 4),
            "strong_binder_density": round(n_strong_pairs / (len(peps) * len(HLA_PANEL)), 5)}


def build() -> dict:
    from mhcflurry import Class1AffinityPredictor
    predictor = Class1AffinityPredictor.load()
    seqs = _read_fasta(FASTA)
    proteins = {name: _protein_stats(seq, predictor) for name, seq in seqs.items()}
    # per-vehicle: capsid_immune_score = 1 - mean(epitope_fraction_strong over the vehicle's antigen(s))
    vehicles = {}
    for veh, antigens in VEHICLE_ANTIGENS.items():
        efs = [proteins[a]["epitope_fraction_strong"] for a in antigens if a in proteins]
        if not efs:
            continue
        ef = sum(efs) / len(efs)
        vehicles[veh] = {"antigens": antigens, "epitope_fraction_strong": round(ef, 4),
                         "capsid_immune_score": round(1.0 - ef, 4)}
    return {
        "version": "1.0",
        "built": _dt.date.today().isoformat(),
        "description": ("computed capsid/envelope CD8 T-cell epitope-load oracle: fraction of the antigen "
                        "presentable (MHCflurry %rank<=0.5) across a frequent HLA-I panel. "
                        "capsid_immune_score = 1 - epitope_fraction_strong. Patient-HLA-specific response is "
                        "NOT modelled (known-unknown); this is a population-level sequence-intrinsic signal."),
        "method": {"predictor": "MHCflurry 2.0 Class1AffinityPredictor (per-allele %rank)",
                   "peptide_len": PEPTIDE_LEN,
                   "strong_rank": STRONG_RANK, "binder_rank": BINDER_RANK, "hla_panel": HLA_PANEL},
        "provenance_dois": PROVENANCE_DOIS,
        "proteins": proteins,
        "vehicles": vehicles,
    }


if __name__ == "__main__":
    yaml.safe_dump(build(), sys.stdout, sort_keys=False, default_flow_style=False)
