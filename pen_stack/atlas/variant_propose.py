"""DMS-grounded variant proposal (Phase 2, Step 2.4) - replaces the failed de-novo chimera generation.

Instead of speculative chimeras (PEN-ASSEMBLE produced 0 TRUE_WRITERs and was HPC-hungry/unvalidatable),
propose *single/double point mutations* with a predicted activity effect, retrospectively validatable
against a published enhanced variant. **No chimeras are ever produced** - only point substitutions.

The activity predictor is a pluggable ``VariantEffectModel``. The DMS-trained model is a Phase-1.5
deliverable (deep mutational scanning of bridge recombinases); until it lands, a transparent,
clearly-labelled physico-chemical baseline lets the framework + retrospective-validation harness run
end-to-end. The headline "recovers the published enhanced variant blind" criterion is evaluated when the
real DMS model is supplied (see ``retrospective_recovery``).

Inputs : enzyme sequence; a VariantEffectModel (Phase-1.5 DMS model, or the baseline).
Outputs: out/variant_proposals_<enzyme>.csv (ranked point mutations + predicted effect + confidence).
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import pandas as pd

_AA = "ACDEFGHIKLMNPQRSTVWY"
_OUT = Path(__file__).resolve().parents[2] / "out"

# Kyte-Doolittle hydropathy + a coarse charge/volume signal, for the labelled baseline ONLY.
_HYDRO = {"A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5, "G": -0.4,
          "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6, "S": -0.8,
          "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2}


@runtime_checkable
class VariantEffectModel(Protocol):
    """Predict a per-mutation activity gain. (i, wt, mut) -> predicted effect (higher = better)."""

    name: str

    def predict(self, seq: str, variants: list[tuple[int, str, str]]) -> list[float]: ...


class BaselinePhysicoChemical:
    """A transparent, NON-DMS placeholder predictor (Phase-1.5 supplies the real DMS model).

    Scores a substitution by *conservativeness* (small hydropathy change ranks higher) - a deliberately
    weak, documented heuristic so the proposal/validation framework is exercisable before Phase 1.5.
    It makes no activity claim and must never be presented as the DMS predictor.
    """

    name = "baseline_physicochemical_placeholder"

    def predict(self, seq: str, variants: list[tuple[int, str, str]]) -> list[float]:
        return [-abs(_HYDRO.get(mut, 0.0) - _HYDRO.get(wt, 0.0)) for (_, wt, mut) in variants]


def propose_variants(seq: str, model: VariantEffectModel, top: int = 20,
                     positions: list[int] | None = None) -> pd.DataFrame:
    """Rank single point mutations by predicted activity gain. No chimeras - substitutions only."""
    idxs = positions if positions is not None else range(len(seq))
    cand = [(i, seq[i], aa) for i in idxs for aa in _AA if aa != seq[i]]
    pred = model.predict(seq, cand)
    df = pd.DataFrame({
        "pos": [c[0] for c in cand],
        "wt": [c[1] for c in cand],
        "mut": [c[2] for c in cand],
        "variant": [f"{c[1]}{c[0] + 1}{c[2]}" for c in cand],   # 1-based, e.g. A123V
        "pred_gain": pred,
        "model": model.name,
    })
    return df.sort_values("pred_gain", ascending=False).head(top).reset_index(drop=True)


def retrospective_recovery(proposals: pd.DataFrame, known_variants: list[str], k: int = 20) -> dict:
    """Blind-validation harness: does the top-k proposal set recover a published enhanced variant?

    ``known_variants`` are 1-based strings like "A123V". Returns recovery flags per known variant and an
    overall hit. With the Phase-1.5 DMS model this is the headline retrospective criterion; with the
    baseline it merely demonstrates the harness runs (recovery is not expected from the placeholder).
    """
    topk = set(proposals.head(k)["variant"])
    hits = {v: (v in topk) for v in known_variants}
    return {"k": k, "model": proposals["model"].iloc[0] if len(proposals) else None,
            "known": known_variants, "recovered": hits, "any_recovered": any(hits.values())}


def run(enzyme: str, seq: str, model: VariantEffectModel | None = None, top: int = 20,
        out_dir: str | Path = _OUT) -> pd.DataFrame:
    model = model or BaselinePhysicoChemical()
    props = propose_variants(seq, model, top=top)
    out = Path(out_dir) / f"variant_proposals_{enzyme}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    props.to_csv(out, index=False)
    return props


if __name__ == "__main__":  # pragma: no cover
    # ISCro4 is 326 aa; without the protein sequence on hand we demo the harness on a short stub.
    demo = "MSEQNKI" * 5
    p = run("DEMO_stub", demo, top=10)
    print(p.to_string(index=False))
    print("\nNOTE: uses the labelled placeholder model; the DMS-trained predictor is a Phase-1.5 deliverable.")
