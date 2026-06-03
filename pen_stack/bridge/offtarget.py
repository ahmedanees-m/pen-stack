"""Genome-wide bridge-recombinase off-target engine (Phase 1.5, Step 1.5.2) - HEADLINE.

Given a bridge-RNA design's target core (bipartite ~14 nt with a central CT dinucleotide), scan hg38 for
pseudosites tolerating up to ~2 mismatches and score each by a position-weight model (some positions
tolerate substitutions, the central core does not). This is the clinical gatekeeper: it tells a designer
where else in the genome the recombinase might write.

Efficiency: the central core (CT) must match for recombination, so we **seed on the core dinucleotide**
and verify the surrounding 14-mer - bounding the scan without loading the genome into RAM (per-chromosome
via pysam). Scoring beats a naive Hamming ranking *because mismatch position matters*.

Also exposes ``predict_offtargets(writer_family, site, ...)`` - the summary entry the Phase-3 Planner
cargo step calls (so its off-target annotation is no longer "pending Phase 1.5").
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from pen_stack.bridge.ingest import load_measured_profile, load_profile_config, protective_weights

_COMP = {"A": "T", "T": "A", "G": "C", "C": "G", "N": "N"}


def position_weights(prefer_measured: bool = True) -> dict[int, float]:
    """0-based protective weight per core position (1 = mismatch abolishes recombination).

    Prefers the MEASURED Perry-2025 profile (committed parquet, available everywhere) when present;
    otherwise the literature-grounded config weights.
    """
    if prefer_measured:
        m = load_measured_profile()
        if not m.empty:
            return {int(p) - 1: float(w) for p, w in zip(m["position"], m["protective_weight"])}
    return {p - 1: w for p, w in protective_weights().items()}


def mismatches(window: str, core: str) -> list[tuple[int, str]]:
    return [(j, window[j]) for j in range(len(core)) if window[j] != core[j]]


def risk_score(mm: list[tuple[int, str]], weights: dict[int, float]) -> float:
    """Fewer / weaker-position mismatches -> higher off-target risk. Perfect match -> 1.0."""
    if not mm:
        return 1.0
    r = 1.0
    for j, _ in mm:
        r *= (1 - weights.get(j, 0.5))
    return float(r)


def hamming_risk(mm: list[tuple[int, str]], core_len: int) -> float:
    """Naive baseline: position-blind - risk decreases uniformly with mismatch count."""
    return float((core_len - len(mm)) / core_len)


def scan_sequence(seq: str, core: str, max_mm: int, weights: dict[int, float],
                  core_positions: list[int]) -> list[dict]:
    """Seed on the central core dinucleotide, verify the full core with <= max_mm mismatches."""
    seq = seq.upper()
    L = len(core)
    c0 = core_positions[0]                      # 0-based index of the core's first central base
    motif = core[c0:c0 + len(core_positions)]   # e.g. 'CT'
    hits = []
    for m in re.finditer(f"(?={motif})", seq):  # overlapping seed matches
        start = m.start() - c0                  # align so the motif sits at the core position
        if start < 0 or start + L > len(seq):
            continue
        window = seq[start:start + L]
        if "N" in window:
            continue
        mm = mismatches(window, core)
        if len(mm) <= max_mm:
            hits.append({"pos": start, "site": window, "n_mm": len(mm),
                         "risk": risk_score(mm, weights), "hamming": hamming_risk(mm, L)})
    return hits


def scan_offtargets(fasta: str | Path, target_core: str, chroms: list[str],
                    max_mm: int | None = None) -> pd.DataFrame:
    """Genome-wide off-target scan for a target core. Per-chromosome (memory-bounded)."""
    from pysam import FastaFile
    cfg = load_profile_config()
    max_mm = cfg["max_mismatches"] if max_mm is None else max_mm
    core_pos = [p - 1 for p in cfg["central_core_positions"]]
    weights = position_weights()
    fa = FastaFile(str(fasta))
    rows = []
    for c in chroms:
        for h in scan_sequence(fa.fetch(c), target_core.upper(), max_mm, weights, core_pos):
            rows.append({"chrom": c, **h})
    fa.close()
    df = pd.DataFrame(rows)
    return df.sort_values("risk", ascending=False).reset_index(drop=True) if not df.empty else df


# ---------------------------------------------------------------- Phase-3 Planner hook + design API

def predict_offtargets(writer_family: str, site: tuple | None = None, target_core: str | None = None,
                       fasta: str | Path | None = None, chroms: list[str] | None = None,
                       top: int = 20) -> dict:
    """Off-target summary for a writer at a site - the entry the Phase-3 cargo step calls.

    Only bridge/seek families are RNA-guided pseudosite-scannable. If a genome + target core are
    available it returns a real genome-wide scan summary; otherwise it reports the engine is ready and
    how to run the full scan (never fabricates off-target sites).
    """
    if writer_family not in {"bridge_IS110", "seek_IS1111"}:
        return {"family": writer_family, "applicable": False,
                "note": "off-target pseudosite scan applies to RNA-guided bridge/seek recombinases only"}
    if not (target_core and fasta):
        return {"family": writer_family, "applicable": True, "status": "engine_ready", "site": site,
                "note": "provide target_core + hg38 fasta (pen-bridge design) for a genome-wide scan"}
    df = scan_offtargets(fasta, target_core, chroms or [], )
    n_exact = int((df["n_mm"] == 0).sum()) if not df.empty else 0
    return {"family": writer_family, "applicable": True, "status": "scanned",
            "target_core": target_core, "n_candidates": int(len(df)),
            "n_exact_matches": n_exact,
            "top": df.head(top).to_dict("records") if not df.empty else []}


if __name__ == "__main__":  # pragma: no cover
    # tiny self-test on a synthetic sequence
    cfg = load_profile_config()
    cp = [p - 1 for p in cfg["central_core_positions"]]
    w = position_weights()
    core = "AAACGTCTACGTTT"   # 14 nt, CT at positions 7-8 (0-based 6-7)
    seq = "GGGG" + core + "TTTT" + core[:6] + "GG" + core[8:] + "AA"  # one exact + one core-disrupted
    hits = scan_sequence(seq, core, cfg["max_mismatches"], w, cp)
    for h in hits:
        print(h)
