"""Phase 1.5 — genome-wide bridge off-target scan for a design (reproducible runner).

    python scripts/p4_genome_scan.py --target ACGTGTCTACGTGA --fasta /path/hg38.fa --out out/offtargets_demo

Writes a ranked BED + parquet of predicted off-target pseudosites. Per-chromosome (memory-bounded).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from pen_stack.bridge.offtarget import scan_offtargets

DEFAULT_CHROMS = [f"chr{i}" for i in range(1, 23)] + ["chrX"]


def main(target: str, fasta: str, out: str, chroms: list[str] | None = None) -> None:
    chroms = chroms or DEFAULT_CHROMS
    print(f"scanning {len(chroms)} chromosomes for target core {target} ...")
    df = scan_offtargets(fasta, target, chroms)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(f"{out}.parquet", index=False)
    # BED: chrom, start, end, name(site), score(risk*1000), with n_mm
    if not df.empty:
        bed = df.copy()
        bed["start"] = bed["pos"]
        bed["end"] = bed["pos"] + len(target)
        bed["score"] = (bed["risk"] * 1000).round().astype(int)
        bed["name"] = bed["site"] + "|mm" + bed["n_mm"].astype(str)
        bed[["chrom", "start", "end", "name", "score"]].to_csv(
            f"{out}.bed", sep="\t", index=False, header=False)
    print(f"{len(df)} pseudosites -> {out}.parquet/.bed ; "
          f"exact={int((df.n_mm==0).sum()) if len(df) else 0}, risk>0.5={int((df.risk>0.5).sum()) if len(df) else 0}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True)
    p.add_argument("--fasta", required=True)
    p.add_argument("--out", default="out/offtargets_demo")
    p.add_argument("--chroms", default=None, help="comma-separated; default chr1..22,X")
    a = p.parse_args()
    main(a.target, a.fasta, a.out, a.chroms.split(",") if a.chroms else None)
