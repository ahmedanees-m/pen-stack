"""Inverse-design optimiser with edit_intent (Phase 3, Step 3.1).

Given a goal (gene/locus, edit_intent, cargo, cell type), search destination × writer for the joint
optimum of safety × durability × reachability × writer-activity, conditioned on an explicit
``edit_intent``. The intent is *load-bearing*: its ``target_gene_sign`` decides whether hitting the
named target gene/element is penalised (safe-harbour: avoid) or rewarded (knock-in / excision: intended)
— so the same locus ranks high or low depending only on the stated goal.

Components are retained on every candidate row; the score is a transparent linear combination read from
``configs/intent_weights.yaml``. Reachability is a hard filter (Tier-1 high-confidence; Tier-2 candidate
flagged). Writer activity comes from the Phase-2 Writer Atlas (measured human-cell axis per family).

Inputs : Phase-1 writability atlas (safety/p_durable/reachable_tier1) + Phase-2 atlas.parquet.
Outputs: ranked (writer, site) candidates with full component provenance.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_CFG = _ROOT / "configs" / "intent_weights.yaml"
_ATLAS = _ROOT / "pen_stack" / "atlas" / "atlas.parquet"
BIN_BP = 1000


class EditIntent(str, Enum):
    SAFE_HARBOUR = "safe_harbour_insertion"
    KNOCK_IN_DISRUPT = "knock_in_with_disruption"
    HIGH_DURABILITY = "high_durability_insertion"
    REG_EXCISION = "regulatory_excision"
    REPEAT_EXCISION = "repeat_excision"


@lru_cache(maxsize=1)
def load_intent_weights(path: str | Path = _CFG) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def writer_activity_by_family(atlas_path: str | Path = _ATLAS) -> dict:
    """Per-family writer-activity proxy from the Writer Atlas curated cores (measured human-cell axis).

    Falls back to readiness when S_HumanCell is missing. Used so the optimiser prefers writers that
    actually work in human cells (e.g. bridge ISCro4) over weakly-active families.
    """
    atlas = pd.read_parquet(atlas_path)
    core = atlas[atlas["entry_kind"] == "curated_core"] if "entry_kind" in atlas else atlas
    act = {}
    for fam, sub in core.groupby("family"):
        r = sub.iloc[0]
        a = r.get("S_HumanCell")
        if a is None or pd.isna(a):
            a = r.get("readiness", 0.5)
        act[fam] = float(a) if pd.notna(a) else 0.5
    return act


def _best_writer(reachable_tier1: str, cargo_bp: int, atlas_caps: dict, activity: dict) -> tuple[str, float, bool]:
    """Pick the best reachable writer that fits the cargo: (family, activity, cargo_ok)."""
    fams = [f for f in str(reachable_tier1).split(";") if f]
    best, best_act, best_ok = None, -1.0, False
    for f in fams:
        cap = atlas_caps.get(f)
        ok = (cap is None) or (cargo_bp <= cap)
        a = activity.get(f, 0.4)
        # prefer cargo-fitting writers; among those, highest activity
        rank = (1 if ok else 0, a)
        if rank > (1 if best_ok else 0, best_act):
            best, best_act, best_ok = f, a, ok
    return best or (fams[0] if fams else "unknown"), best_act if best else 0.4, best_ok


def score_candidates(cands: pd.DataFrame, intent: EditIntent | str, cargo_bp: int) -> pd.DataFrame:
    """Score a candidate DataFrame (needs: safety, p_durable, reachable_tier1, on_target[bool]).

    Adds: writer (family), writer_activity, cargo_ok, score, and the retained components.
    """
    intent = EditIntent(intent) if not isinstance(intent, EditIntent) else intent
    cfg = load_intent_weights()
    w = cfg["intents"][intent.value]
    mag = float(cfg.get("on_target_magnitude", 1.0))

    atlas = pd.read_parquet(_ATLAS)
    caps = (atlas.dropna(subset=["cargo_capacity_bp"]).groupby("family")["cargo_capacity_bp"].max().to_dict())
    activity = writer_activity_by_family()

    out = cands.copy()
    picks = out["reachable_tier1"].apply(lambda rt: _best_writer(rt, cargo_bp, caps, activity))
    out["writer"] = [p[0] for p in picks]
    out["writer_activity"] = [p[1] for p in picks]
    out["cargo_ok"] = [p[2] for p in picks]

    on_target = out.get("on_target", pd.Series(False, index=out.index)).astype(float)
    base = (w["safety"] * out["safety"].astype(float)
            + w["durability"] * out["p_durable"].astype(float)
            + w["activity"] * out["writer_activity"].astype(float))
    # target_gene_sign: +1 -> penalise on-target (avoid the gene); -1 -> reward on-target (hit the gene)
    out["score"] = base - w["target_gene_sign"] * mag * on_target
    # cargo that cannot be delivered by any reachable writer is penalised
    out.loc[~out["cargo_ok"], "score"] -= 0.5
    out["intent"] = intent.value
    return out.sort_values("score", ascending=False).reset_index(drop=True)


def gene_coords_path() -> Path:
    """Locate gene_coords.parquet: packaged copy first (works in any container), then phase_1."""
    for p in (_ROOT / "data" / "curated" / "gene_coords.parquet",
              _ROOT.parent / "phase_1" / "app_data" / "gene_coords.parquet"):
        if p.exists():
            return p
    return _ROOT / "data" / "curated" / "gene_coords.parquet"


@lru_cache(maxsize=8)
def _gene_coords(path: str | None = None) -> pd.DataFrame:
    return pd.read_parquet(Path(path) if path else gene_coords_path())


def gene_region(gene: str, flank_kb: int = 50) -> tuple[str, int, int] | None:
    gc = _gene_coords()
    g = gc[gc["gene"] == gene]
    if g.empty:
        return None
    r = g.iloc[0]
    return r["chrom"], max(0, int(r["start"]) - flank_kb * 1000), int(r["end"]) + flank_kb * 1000


def plan(gene: str, intent: EditIntent | str, cargo_bp: int, writable_df: pd.DataFrame,
         k: int = 10, flank_kb: int = 50) -> pd.DataFrame:
    """Rank (writer, site) candidates near a gene for the given intent. Components retained."""
    intent = EditIntent(intent) if not isinstance(intent, EditIntent) else intent
    reg = gene_region(gene, flank_kb)
    if reg is None:
        return pd.DataFrame()
    chrom, lo, hi = reg
    sub = writable_df[(writable_df["chrom"] == chrom)
                      & (writable_df["bin"].between(lo // BIN_BP, hi // BIN_BP))].copy()
    if sub.empty:
        return pd.DataFrame()
    # on_target = bin overlaps the gene body (not just the flank)
    g = _gene_coords()
    gr = g[g["gene"] == gene].iloc[0]
    sub["on_target"] = sub["bin"].between(int(gr["start"]) // BIN_BP, int(gr["end"]) // BIN_BP)
    scored = score_candidates(sub, intent, cargo_bp)
    cols = ["chrom", "bin", "writer", "safety", "p_durable", "writer_activity",
            "on_target", "cargo_ok", "reachable_tier1", "score", "intent"]
    return scored[[c for c in cols if c in scored.columns]].head(k)
