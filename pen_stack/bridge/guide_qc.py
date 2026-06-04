"""Bridge-RNA guide ranking / QC layer (v3.1, WS-G2).

Wraps a bridge-RNA design: when a default guide design trips a QC flag - self-complementarity, cross-loop
(TBL-DBL) recombination, poor scaffold fold (MFE), or off-target - this enumerates candidate variants and
RANKS them by the existing fold-QC (`bridge/fold_qc.py`) plus off-target risk (`bridge/offtarget.py`).

This is a RANKING layer, not validated design: it retrospectively down-ranks known-bad guides; it makes NO
claim of generating superior novel guides. It reuses the validated QC primitives so the score is grounded.
"""
from __future__ import annotations

from pen_stack.bridge import fold_qc

_PAIR = {"A": "T", "T": "A", "G": "C", "C": "G", "U": "A"}


def _revcomp(s: str) -> str:
    return "".join(_PAIR.get(b, "N") for b in reversed(s.upper()))


def qc_flags(target_guide: str, donor_guide: str, scaffold_seq: str | None = None,
             offtarget_count: int | None = None, cross_loop_threshold: float = 0.6,
             mfe_per_nt_warn: float = -0.5) -> dict:
    """Tripped QC flags for one design. Pure-python except the optional ViennaRNA fold (degrades)."""
    xl = fold_qc.cross_loop_risk(target_guide, donor_guide)
    flags = []
    if xl["tbl_self"] >= cross_loop_threshold or xl["dbl_self"] >= cross_loop_threshold:
        flags.append("self_complementarity")
    if xl["tbl_dbl"] >= cross_loop_threshold:
        flags.append("cross_loop_recombination")
    fold = fold_qc.fold(scaffold_seq) if scaffold_seq else {"available": False}
    if fold.get("available") and fold["length"] and (fold["mfe"] / fold["length"]) < mfe_per_nt_warn:
        flags.append("poor_fold_mfe")
    if offtarget_count is not None and offtarget_count > 0:
        flags.append("off_target")
    return {"cross_loop": xl, "fold": fold, "offtarget_count": offtarget_count, "flags": flags,
            "pass": len(flags) == 0}


def qc_score(target_guide: str, donor_guide: str, scaffold_seq: str | None = None,
             offtarget_count: int | None = None) -> float:
    """Combined QC quality in [0,1] (HIGHER = safer): penalize cross-loop complementarity, weak scaffold
    fold, and off-targets. Used only to RANK candidate guides, not to certify them."""
    xl = fold_qc.cross_loop_risk(target_guide, donor_guide)
    score = 1.0 - max(xl["tbl_self"], xl["dbl_self"], xl["tbl_dbl"])     # cross-loop is the dominant penalty
    if scaffold_seq:
        fold = fold_qc.fold(scaffold_seq)
        if fold.get("available") and fold["length"]:
            # reward a fold near the expected ~ -0.35 kcal/mol per nt; penalize too-weak structure
            score -= min(0.3, max(0.0, -0.35 - fold["mfe"] / fold["length"]))
    if offtarget_count:
        score -= min(0.4, 0.1 * offtarget_count)
    return round(max(0.0, min(1.0, score)), 4)


def rank_variants(variants: list[dict]) -> list[dict]:
    """Rank guide variants by QC score (best first). Each variant: {name, target_guide, donor_guide,
    optional scaffold_seq, optional offtarget_count}."""
    scored = []
    for v in variants:
        s = qc_score(v["target_guide"], v["donor_guide"], v.get("scaffold_seq"), v.get("offtarget_count"))
        scored.append({**{k: v[k] for k in ("name",) if k in v}, "qc_score": s,
                       "flags": qc_flags(v["target_guide"], v["donor_guide"], v.get("scaffold_seq"),
                                         v.get("offtarget_count"))["flags"]})
    return sorted(scored, key=lambda r: r["qc_score"], reverse=True)


def screen_and_rank(default: dict, variants: list[dict] | None = None) -> dict:
    """If the default design trips a flag, rank the provided variants by QC and recommend the best.

    `variants` are caller-supplied (e.g. from bridgernadesigner enumeration); if absent, only the default's
    QC verdict is returned. No novel-guide generation is claimed.
    """
    d_flags = qc_flags(default["target_guide"], default["donor_guide"], default.get("scaffold_seq"),
                       default.get("offtarget_count"))
    out = {"default_flags": d_flags["flags"], "default_pass": d_flags["pass"]}
    if d_flags["pass"] or not variants:
        out["ranked"] = []
        out["recommended"] = None if not d_flags["pass"] else "default (no flags)"
        return out
    ranked = rank_variants(variants)
    out["ranked"] = ranked
    out["recommended"] = ranked[0] if ranked else None
    return out
