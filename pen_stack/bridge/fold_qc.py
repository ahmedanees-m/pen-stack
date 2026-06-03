"""Bridge-RNA fold / cross-loop QC (Phase 1.5, Step 1.5.3).

Predict whether a designed bridge RNA folds correctly (ViennaRNA, in the VM image) and flag DBL-DBL /
TBL-TBL self/cross-recombination risk from guide complementarity - an experimentally observed failure
mode where the target- and donor-binding loops recombine with each other instead of the genome.

``cross_loop_risk`` is pure-Python (no dependency); ``fold`` uses ViennaRNA and degrades gracefully when
the package is absent (returns None) so the rest of the QC still runs.
"""
from __future__ import annotations

_PAIR = {"A": "U", "U": "A", "G": "C", "C": "G", "T": "A"}


def fold(scaffold_seq: str) -> dict:
    """MFE fold of the bridge-RNA scaffold. Returns {structure, mfe} or {available: False}."""
    try:
        import RNA
    except Exception:  # noqa: BLE001 - ViennaRNA only in the VM image
        return {"available": False, "note": "ViennaRNA not installed (runs in the VM image)"}
    fc = RNA.fold_compound(scaffold_seq.upper().replace("T", "U"))
    struct, mfe = fc.mfe()
    return {"available": True, "structure": struct, "mfe": round(float(mfe), 2),
            "length": len(scaffold_seq)}


def _complementarity(a: str, b: str) -> float:
    """Fraction of positions where a pairs with the reverse-complement of b (crude antiparallel match)."""
    a = a.upper()
    b_rc = "".join(_PAIR.get(x, "N") for x in reversed(b.upper()))
    n = min(len(a), len(b_rc))
    if n == 0:
        return 0.0
    return sum(1 for x, y in zip(a[:n], b_rc[:n]) if x == y) / n


def cross_loop_risk(target_guide: str, donor_guide: str) -> dict:
    """Self/cross complementarity of the binding loops. High values predict unintended recombination."""
    return {"tbl_self": round(_complementarity(target_guide, target_guide), 3),
            "dbl_self": round(_complementarity(donor_guide, donor_guide), 3),
            "tbl_dbl": round(_complementarity(target_guide, donor_guide), 3)}


def qc_verdict(target_guide: str, donor_guide: str, scaffold_seq: str | None = None,
               cross_loop_threshold: float = 0.6) -> dict:
    """Combined fold + cross-loop verdict for a design."""
    xl = cross_loop_risk(target_guide, donor_guide)
    flags = [k for k, v in xl.items() if v >= cross_loop_threshold]
    out = {"cross_loop": xl, "cross_loop_flags": flags,
           "pass": len(flags) == 0}
    if scaffold_seq:
        out["fold"] = fold(scaffold_seq)
    return out
