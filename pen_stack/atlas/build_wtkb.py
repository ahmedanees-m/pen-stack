"""Build the Writer-Targeting Knowledge Base (WT-KB) - Phase 0, Step 0.2.

Reads the curated YAML (one block per writer family), validates every row against the
``WriterEntry`` schema (which enforces the sourcing rule: >=1 DOI per row), and emits both a
parquet (for the pipeline) and a human-readable markdown table (for literature cross-check).

Usage:
    python -m pen_stack.atlas.build_wtkb --curated configs/wtkb_curated.yaml \
        --out pen_stack/atlas/wtkb.parquet --md docs/wtkb.md
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

from pen_stack.atlas.schema import WriterEntry


def build(curated_yaml: str, out_parquet: str | None = None, out_md: str | None = None) -> pd.DataFrame:
    curated = yaml.safe_load(Path(curated_yaml).read_text(encoding="utf-8"))
    rows = []
    for key, block in curated.items():
        entry = WriterEntry(**block) # validates (raises on missing DOI / bad enum)
        d = entry.model_dump()
        d["_key"] = key
        rows.append(d)
    df = pd.DataFrame(rows)
    # stable column order, _key first
    cols = ["_key"] + [c for c in df.columns if c != "_key"]
    df = df[cols]
    if out_parquet:
        Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_parquet, index=False)
    if out_md:
        Path(out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(out_md).write_text(_to_markdown(df), encoding="utf-8")
    return df


def _to_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# Writer-Targeting Knowledge Base (WT-KB)",
        "",
        f"_Generated from `configs/wtkb_curated.yaml` - {len(df)} writer families. "
        "Every row is schema-validated and carries >=1 DOI (sourcing rule)._",
        "",
        "| Family | Representative | Mechanism | Modality | Target site | Tier | Confidence | DOIs |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for _, r in df.iterrows():
        dois = "; ".join(r["key_dois"])
        lines.append(
            f"| {r['family']} | {r['representative_system']} | {r['mechanism_bucket']} | "
            f"{r['targeting_modality']} | {r['target_site_spec']} | {r['reachability_tier']} | "
            f"{r['confidence']} | {dois} |"
        )
    lines += ["", "## Reachability constraints (per family)", ""]
    for _, r in df.iterrows():
        lines.append(f"- **{r['family']}** ({r['reachability_tier']}): {r['reachability_constraints']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--curated", default="configs/wtkb_curated.yaml")
    ap.add_argument("--out", default="pen_stack/atlas/wtkb.parquet")
    ap.add_argument("--md", default="docs/wtkb.md")
    a = ap.parse_args()
    df = build(a.curated, a.out, a.md)
    print(f"WT-KB built: {len(df)} families -> {a.out}")
    tiers = df["reachability_tier"].value_counts().to_dict()
    print(f"tiers: {tiers}")
    print(f"fully-specified families: {len(df)} (target >=6)")


if __name__ == "__main__":
    main()
