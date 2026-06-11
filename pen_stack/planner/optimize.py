"""Inverse-design optimiser with edit_intent (Phase 3, Step 3.1).

Given a goal (gene/locus, edit_intent, cargo, cell type), search destination x writer for the joint
optimum of safety x durability x reachability x writer-activity, conditioned on an explicit
``edit_intent``. The intent is *load-bearing*: its ``target_gene_sign`` decides whether hitting the
named target gene/element is penalised (safe-harbour: avoid) or rewarded (knock-in / excision: intended)
- so the same locus ranks high or low depending only on the stated goal.

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

import numpy as np
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
    # Deterministic ranking: a stable sort with explicit tie-breakers, so tied scores (common when safety
    # saturates) always resolve identically across runs - the default quicksort is NOT stable.
    keys = ["score"] + [c for c in ("chrom", "bin", "gene") if c in out.columns]
    asc = [False] + [True] * (len(keys) - 1)
    return out.sort_values(keys, ascending=asc, kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------- WS-UQ / UQ3 plan-level confidence

# Default per-axis conformal half-widths used when an explicit WS-UQ calibration is not supplied. These are
# documented placeholders, not magic numbers: ``durability`` is the widest because the durability signal is
# the weakest (v3.1.1: silenced-AUROC ~0.65); ``safety`` and ``activity`` are tighter. A caller that has run
# the conformal calibration (validate/uncertainty_eval) passes the measured half-widths instead.
DEFAULT_AXIS_HALF_WIDTHS = {"safety": 0.10, "durability": 0.15, "activity": 0.10}


def _axis_intervals(row, half_widths: dict, ood_factor: float = 1.0) -> dict:
    """Per-axis {point, lo, hi} for a candidate, intervals widened by the OOD factor (UQ2 hook)."""
    cols = {"safety": "safety", "durability": "p_durable", "activity": "writer_activity"}
    out = {}
    for axis, col in cols.items():
        p = float(row[col]) if col in row and pd.notna(row[col]) else 0.5
        h = float(half_widths.get(axis, 0.1)) * float(ood_factor)
        out[axis] = {"point": p, "lo": max(0.0, p - h), "hi": min(1.0, p + h)}
    return out


def attach_uncertainty(scored: pd.DataFrame, intent: EditIntent | str,
                       half_widths: dict | None = None, ood_factor=None,
                       threshold: float = 0.5, abstain_below: float = 0.5) -> pd.DataFrame:
    """UQ3 - propagate per-axis conformal intervals into a plan-level confidence + epistemic status.

    Additive: takes the output of :func:`score_candidates`/:func:`plan` and appends ``confidence``,
    ``score_lo``/``score_hi`` (90% plan-score band), ``abstain`` and ``epistemic_status`` per plan, using
    :func:`selective_prediction.propagate_plan_confidence` over the intent's axis weights. ``ood_factor`` may
    be a scalar or a per-row sequence (from :class:`wgenome.ood.OODDetector.widen_factor`) so out-of-
    distribution sites get wider bands and lower confidence - the grounded-confident vs grounded-
    extrapolating distinction. Does not change the existing ranking columns.
    """
    from pen_stack.validate.selective_prediction import propagate_plan_confidence
    intent = EditIntent(intent) if not isinstance(intent, EditIntent) else intent
    w = load_intent_weights()["intents"][intent.value]
    weights = {"safety": w["safety"], "durability": w["durability"], "activity": w["activity"]}
    half_widths = half_widths or DEFAULT_AXIS_HALF_WIDTHS
    out = scored.copy().reset_index(drop=True)
    if ood_factor is None:
        ood_factor = [1.0] * len(out)
    elif np.isscalar(ood_factor):
        ood_factor = [float(ood_factor)] * len(out)

    conf, lo, hi, status, abst = [], [], [], [], []
    for i, row in out.iterrows():
        of = float(ood_factor[i])
        axes = _axis_intervals(row, half_widths, of)
        prop = propagate_plan_confidence(axes, weights, threshold=threshold)
        c = prop["confidence"]
        conf.append(round(c, 4))
        lo.append(round(prop["lo"], 4))
        hi.append(round(prop["hi"], 4))
        is_abstain = bool(c < abstain_below)
        abst.append(is_abstain)
        if of >= 1.5:
            status.append("grounded-extrapolating")
        elif is_abstain:
            status.append("not-computable")
        else:
            status.append("grounded-confident")
    out["confidence"] = conf
    out["score_lo"] = lo
    out["score_hi"] = hi
    out["abstain"] = abst
    out["epistemic_status"] = status
    return out


def mechanistic_filter(reachable_tier1: str, site_seq: str, installed_att: bool = False) -> dict:
    """WS-MC / MC1 — hard sequence-level reachability filter on a concrete site.

    Given the WT-KB Tier-1 writer list (the ``reachable_tier1`` string) and the site's sequence, drop writers
    whose required targeting element (PAM / core dinucleotide / att) is absent — a physically impossible
    writer–site pairing is rejected. Returns the surviving family list + the rejections (with reasons). Called
    by the Planner/agent only when a concrete site sequence is available; the bulk bin ranking is unchanged.
    """
    from pen_stack.planner.target_site import filter_reachable
    fams = [f for f in str(reachable_tier1).split(";") if f]
    res = filter_reachable(fams, site_seq, installed_att=installed_att)
    res["reachable_str"] = ";".join(res["reachable"])
    return res


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


# Genomic safe-harbour *locus nicknames* are not HGNC gene symbols, so they are absent from gene_coords; map the
# well-documented ones to their host gene so a user who types the common name still gets a plan. AAVS1 = intron 1
# of PPP1R12C (19q13.42); H11/Hipp11 = an intron of EIF4ENIF1 (22q12). (CCR5, CLYBL, HPRT1 are real symbols.)
_GSH_ALIASES = {"AAVS1": "PPP1R12C", "H11": "EIF4ENIF1", "HIPP11": "EIF4ENIF1"}


def resolve_gene(gene: str) -> str:
    """Map a safe-harbour locus nickname (e.g. AAVS1) to its HGNC host gene; pass real symbols through unchanged."""
    return _GSH_ALIASES.get(str(gene).strip().upper(), gene)


def gene_region(gene: str, flank_kb: int = 50) -> tuple[str, int, int] | None:
    gc = _gene_coords()
    g = gc[gc["gene"] == resolve_gene(gene)]
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
    gr = g[g["gene"] == resolve_gene(gene)].iloc[0]
    sub["on_target"] = sub["bin"].between(int(gr["start"]) // BIN_BP, int(gr["end"]) // BIN_BP)
    scored = score_candidates(sub, intent, cargo_bp)
    cols = ["chrom", "bin", "writer", "safety", "p_durable", "writer_activity",
            "on_target", "cargo_ok", "reachable_tier1", "score", "intent"]
    return scored[[c for c in cols if c in scored.columns]].head(k)
