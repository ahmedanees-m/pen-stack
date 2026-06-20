"""Within-locus site ranking (v3.1, WS-A5) - descriptive.

For a large validated safe-harbour gene, does the planner rank the documented intronic safe bin above the
other bins in that locus? We rank every 1 kb bin in the gene body by writability and report the documented
bin's within-locus percentile. Descriptive (few qualifying loci); not a hypothesis test.

Documented safe sub-region coordinates (hg38, widely cited):
  - AAVS1 = PPP1R12C intron 1, chr19:55,115,768 (DeKelver 2010, 10.1101/gr.106773.110)
  - CLYBL = CLYBL intron 2, chr13:99,816,475 (Cerbini 2015, 10.1371/journal.pone.0116032)
  - Pansio-1 = HIPK1, chr1:113,340,237 (Lin 2024 eLife 79592, in-vitro validated)
  - Olonne-18 = TXNL1, chr18:56,535,607 (Lin 2024 eLife 79592, in-vitro validated)
  - Keppel-19 = SAFB, chr19:5,401,450 (Lin 2024 eLife 79592, in-vitro validated)

Acceptance (prereg/ws_a.yaml): the documented bin lands in the top quartile (>= 75th percentile of
writability within the locus) for a pre-registered fraction of loci; reported per locus. Scaled in v3.1.1
from 2 to 5 loci using the in-vitro-validated eLife universal-GSH sub-regions.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
_OUT = _ROOT / "out" / "within_locus_ranking.json"
_WDF = _ROOT.parent / "phase_1" / "out" / "atlas_k562.parquet"

# documented safe bins (gene, chrom, documented_bp)
_LOCI = [
    {"name": "AAVS1", "gene": "PPP1R12C", "chrom": "chr19", "doc_bp": 55115768,
     "doi": "10.1101/gr.106773.110"},
    {"name": "CLYBL", "gene": "CLYBL", "chrom": "chr13", "doc_bp": 99816475,
     "doi": "10.1371/journal.pone.0116032"},
    {"name": "Pansio-1", "gene": "HIPK1", "chrom": "chr1", "doc_bp": 113340237,
     "doi": "10.7554/eLife.79592"},
    {"name": "Olonne-18", "gene": "TXNL1", "chrom": "chr18", "doc_bp": 56535607,
     "doi": "10.7554/eLife.79592"},
    {"name": "Keppel-19", "gene": "SAFB", "chrom": "chr19", "doc_bp": 5401450,
     "doi": "10.7554/eLife.79592"},
]


def run(out: str | Path = _OUT) -> dict:
    from pen_stack.planner.optimize import _gene_coords
    wdf = pd.read_parquet(_WDF)
    gc = _gene_coords()
    rows = []
    for loc in _LOCI:
        g = gc[gc["gene"] == loc["gene"]]
        if g.empty:
            continue
        r = g.iloc[0]
        lo, hi = int(r["start"]) // 1000, int(r["end"]) // 1000
        body = wdf[(wdf["chrom"] == loc["chrom"]) & (wdf["bin"].between(lo, hi))].dropna(subset=["writability"])
        if body.empty:
            continue
        doc_bin = loc["doc_bp"] // 1000
        doc_row = body[body["bin"] == doc_bin]
        if doc_row.empty: # nearest available bin in the body
            doc_row = body.iloc[(body["bin"] - doc_bin).abs().argsort()[:1]]
        doc_w = float(doc_row.iloc[0]["writability"])
        pct = float((body["writability"] < doc_w).mean()) # within-locus percentile of the documented bin
        rows.append({"name": loc["name"], "gene": loc["gene"], "n_bins": int(len(body)),
                     "documented_bin": int(doc_bin), "documented_writability": round(doc_w, 4),
                     "within_locus_percentile": round(pct, 3), "top_quartile": bool(pct >= 0.75),
                     "doi": loc["doi"]})
    tab = pd.DataFrame(rows)
    n = len(tab)
    n_top = int(tab["top_quartile"].sum()) if n else 0
    report = {
        "what_this_is": "within-locus ranking of the documented safe bin (descriptive, not a hypothesis test)",
        "n_loci": n, "n_top_quartile": n_top,
        "fraction_top_quartile": round(n_top / n, 3) if n else None,
        "per_locus": rows,
        "scope": "few qualifying loci; descriptive; the documented sub-region is a 1 kb bin approximation.",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
