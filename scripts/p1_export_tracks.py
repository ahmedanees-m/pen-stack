"""Export Writable Genome BigWig tracks for a cell type (Phase 1, Step 1.11).

    python scripts/p1_export_tracks.py --ct k562
"""
import argparse

from pen_stack.wgenome.export_tracks import export_atlas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ct", default="k562")
    ap.add_argument("--out-dir", default="/data/out")
    ap.add_argument("--sizes", default="/data/raw/hg38.chrom.sizes")
    a = ap.parse_args()
    written = export_atlas(f"{a.out_dir}/atlas_{a.ct}.parquet", a.sizes, a.out_dir, a.ct)
    for k, v in written.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
