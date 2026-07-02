"""PhiC31 pseudo-attP recall / enrichment benchmark (O-G2) — sealed harness.

Does attP-sequence-similarity recover the documented human pseudo-attP (Thyagarajan 2001: psiA/psiC/psiD,
GenBank AF333429/30/31) above length-matched random GRCh38 background? Positives are the verified GenBank
sequences; the query is the verified phage attP (PDB 9U2T attP60, central 30 bp); background is sampled from
GRCh38. Result (committed in phic31_recall_metrics.json): NEGATIVE — the positives sit at the background median,
so sequence identity to attP is NOT a validated PhiC31 pseudo-attP predictor. Reported verbatim.

Run on the VM (needs GRCh38 + pysam): docker run --rm --entrypoint bash -v <genomes>:/genome -v <bench>:/work
-w /work penstack:phase1.5 -lc 'python harness.py'. Deterministic (seed=20260701).
"""
import json
import os
import random

import pysam

GENOME = os.environ.get("GRCH38", "/genome/GRCh38.fa")
ATTP_Q = "AACTGGGGTAACCTTTGAGTTCTCTCAGTT"  # phiC31 attP (PDB 9U2T attP60) central 30 bp
POSITIVES = "phic31_pseudo.fasta"          # AF333429/30/31 FASTA (Thyagarajan 2001)
N_BG = 1000
_C = {"A": "T", "T": "A", "G": "C", "C": "G", "N": "N"}


def rc(s):
    return "".join(_C.get(b, "N") for b in reversed(s))


def best_mm(query, target):
    L, best = len(query), len(query)
    for q in (query, rc(query)):
        for i in range(len(target) - L + 1):
            mm = 0
            for a, b in zip(q, target[i:i + L]):
                if a != b:
                    mm += 1
                    if mm >= best:
                        break
            best = min(best, mm)
    return best


def run():
    random.seed(20260701)
    seqs, name = {}, None
    for line in open(POSITIVES):
        line = line.strip()
        if line.startswith(">"):
            name = line.split()[0][1:]; seqs[name] = ""
        elif name:
            seqs[name] += line.upper()
    if not os.path.exists(GENOME + ".fai"):
        pysam.faidx(GENOME)
    fa = pysam.FastaFile(GENOME)
    chroms = [c for c in fa.references if c in {f"chr{i}" for i in range(1, 23)} | {"chrX", "chrY"}]
    clens = {c: fa.get_reference_length(c) for c in chroms}
    tot = sum(clens.values()); w = [clens[c] / tot for c in chroms]
    labels = {"AF333429.1": "psiA", "AF333430.1": "psiC", "AF333431.1": "psiD"}
    out = {}
    for acc, seq in seqs.items():
        L = len(seq); pscore = best_mm(ATTP_Q, seq); bg = []
        while len(bg) < N_BG:
            c = random.choices(chroms, weights=w)[0]
            if clens[c] <= L:
                continue
            s = random.randint(0, clens[c] - L); win = fa.fetch(c, s, s + L).upper()
            if win.count("N") > 0.1 * L:
                continue
            bg.append(best_mm(ATTP_Q, win))
        out[labels[acc]] = {"pos_mm": pscore, "bg_median": sorted(bg)[len(bg) // 2],
                            "frac_bg_as_or_more_similar": round(sum(b <= pscore for b in bg) / len(bg), 4)}
    fa.close()
    recovered = all(v["frac_bg_as_or_more_similar"] < 0.05 for v in out.values())
    print(json.dumps({"per_site": out, "recovered_above_background": recovered}, indent=2))


if __name__ == "__main__":
    run()
