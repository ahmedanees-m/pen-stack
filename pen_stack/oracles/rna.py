"""RNA oracle (v4.0, WS-O4) — ViennaRNA secondary-structure fold, under the oracle contract.

A thin contract wrapper over the EXISTING `bridge.fold_qc` (the v1.5 ViennaRNA QC that already feeds the
hard fold-legality rule). ViennaRNA is real and runs in the VM image; when absent the adapter returns a
deferred `OracleResult` (available=False) rather than a fabricated structure. Fold legality remains a HARD
rule input (it does not become a soft signal here).
"""
from __future__ import annotations

from pen_stack.oracles import build_result
from pen_stack.oracles.schema import OracleResult


def fold(scaffold_seq: str) -> OracleResult:
    """MFE fold of a bridge-RNA scaffold via ViennaRNA, wrapped in the oracle contract."""
    from pen_stack.bridge.fold_qc import fold as _fold
    r = _fold(scaffold_seq)
    inputs = {"scaffold_len": len(scaffold_seq), "scaffold_seq": scaffold_seq.upper()}
    if not r.get("available"):
        return build_result("rna", "viennarna", inputs=inputs, available=False,
                            note=r.get("note", "ViennaRNA not installed (runs in the VM image)"))
    # native uncertainty proxy: a less-negative MFE per nt = a weaker, less-certain fold
    mfe, n = float(r["mfe"]), max(1, int(r["length"]))
    unc = max(0.0, min(1.0, 1.0 + (mfe / n) / 0.5))   # ~0 for strong folds, ->1 as MFE/nt -> 0
    return build_result("rna", "viennarna", inputs=inputs,
                        value={"structure": r["structure"], "mfe": r["mfe"], "length": r["length"]},
                        native_uncertainty=round(unc, 3),
                        note="ViennaRNA MFE fold; a hard legality input for bridge-RNA QC")
