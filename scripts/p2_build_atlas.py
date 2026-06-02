"""Phase 2 atlas pipeline (reproducible): expand -> mechanism -> therapeutic readiness.

Runs the three atlas-building steps in order so ``atlas.parquet`` carries every Phase-2 column. Network
is needed only for Step 2.1 (UniProt; cached under data/external/atlas after the first run).

    python scripts/p2_build_atlas.py            # full build
    python scripts/p2_build_atlas.py --offline  # use cached UniProt TSVs only
"""
from __future__ import annotations

import argparse

from pen_stack.atlas.expand import build_atlas
from pen_stack.mech.classify_atlas import classify_atlas, core_agreement
from pen_stack.score.therapeutic import apply_to_atlas


def main(offline: bool = False) -> None:
    print("[2.1] expand Writer Atlas across families ...")
    a = build_atlas(offline_ok=offline)
    print(f"      {len(a):,} systems across {a['family'].nunique()} families")

    print("[2.2] mechanism classification at scale ...")
    a = classify_atlas()
    print(f"      core agreement vs audited labels: {core_agreement(a)}")

    print("[2.3] therapeutic-readiness scoring ...")
    a = apply_to_atlas()
    print(f"      deliv_class: {a['deliv_class'].value_counts().to_dict()}")
    print("done -> pen_stack/atlas/atlas.parquet")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true")
    main(**vars(p.parse_args()))
