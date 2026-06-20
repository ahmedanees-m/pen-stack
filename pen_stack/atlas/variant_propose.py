"""DMS-grounded variant proposal (Phase 2, Step 2.4) - replaces the failed de-novo chimera generation.

Instead of speculative chimeras (PEN-ASSEMBLE produced 0 TRUE_WRITERs and was HPC-hungry/unvalidatable),
propose *single/double point mutations* with a measured activity effect. **No chimeras are ever produced**
- only point substitutions.

The activity predictor is a pluggable ``VariantEffectModel``. The real model is ``DMSVariantEffectModel``,
backed by the Perry 2025 deep mutational scan of ISCro4 (Table S3, delivered in Phase 1.5): it scores each
substitution by its MEASURED activity Z-score. Fed that model, the framework's top proposals ARE the
experimentally enhancing mutations - N322P (rank 1), H50K (rank 2), R278M - so it RECOVERS the known
enhancers. Per the program's framing: this is a useful catalogue feature that recovers
KNOWN enhancers from the DMS; it is NOT a novel variant-design method and it is NOT a blind sequence-only
prediction. For GENERATING new variants the established engine is EVOLVEpro - wrap it, do not rebuild.

When the DMS is absent, a transparent physico-chemical *baseline* keeps the framework runnable (it makes
no activity claim and must never be presented as the DMS model).

Inputs : enzyme sequence; a VariantEffectModel (DMSVariantEffectModel, or the labelled baseline).
Outputs: out/variant_proposals_<enzyme>.csv (ranked point mutations + measured effect).
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


class DMSVariantEffectModel:
    """The REAL model: scores a substitution by its MEASURED activity Z-score from the Perry 2025 ISCro4
    deep mutational scan (Table S3, Phase 1.5). Substitutions not present in the scan get a strongly
    negative score (treated as unmeasured/non-enhancing). This recovers known enhancers; it is not a blind
    sequence predictor (see module docstring). Requires the Perry tables locally (PEN_PERRY_DIR)."""

    name = "perry2025_dms_iscro4"

    def __init__(self) -> None:
        from pen_stack.bridge.ingest import load_dms
        dms = load_dms()
        if dms.empty:
            raise FileNotFoundError("Perry 2025 DMS (Table S3) not available; set PEN_PERRY_DIR")
        z = pd.to_numeric(dms["Z_Score_wrt_WT"], errors="coerce")
        self._z = dict(zip(dms["Mutation"].astype(str), z))

    def predict(self, seq: str, variants: list[tuple[int, str, str]]) -> list[float]:
        # variant key is wt + 1-based position + mut, e.g. "N322P"
        return [self._z.get(f"{wt}{i + 1}{mut}", -9.9) for (i, wt, mut) in variants]


def iscro4_sequence() -> str | None:
    """ISCro4 recombinase sequence from Perry 2025 Table S1 (326 aa). None if absent."""
    from pen_stack.bridge.ingest import load_screen
    s1 = load_screen()
    row = s1[s1["Name"].astype(str) == "ISCro4"] if not s1.empty else s1
    return row.iloc[0]["Recombinase_Sequence"] if len(row) else None


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
        "variant": [f"{c[1]}{c[0] + 1}{c[2]}" for c in cand], # 1-based, e.g. A123V
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


# published enhancing single mutations identified by the Perry 2025 ISCro4 DMS (the known enhancers)
KNOWN_ISCRO4_ENHANCERS = ["N322P", "H50K", "R278M"]


def iscro4_dms_recovery(top: int = 20, out_dir: str | Path = _OUT) -> dict:
    """Step 2.4 completion: feed the REAL Perry DMS model to the proposal framework and confirm it recovers
    the known enhancing ISCro4 mutations in its top proposals. Framing: recovers KNOWN enhancers
    (a catalogue feature), not a blind prediction. Returns the recovery report; writes the proposals CSV.
    Empty/None when the Perry tables are absent."""
    seq = iscro4_sequence()
    if seq is None:
        return {"available": False, "note": "Perry 2025 Table S1 (ISCro4 sequence) not present"}
    props = run("ISCro4", seq, model=DMSVariantEffectModel(), top=top, out_dir=out_dir)
    rec = retrospective_recovery(props, KNOWN_ISCRO4_ENHANCERS, k=top)
    rec["available"] = True
    rec["top_proposals"] = props.head(5)[["variant", "pred_gain"]].to_dict("records")
    rec["framing"] = "recovers KNOWN enhancers from the measured DMS (catalogue feature); not a blind " \
                     "sequence predictor and not a generative method (EVOLVEpro is the engine to wrap)."
    return rec


if __name__ == "__main__": # pragma: no cover
    # ISCro4 is 326 aa; without the protein sequence on hand we demo the harness on a short stub.
    demo = "MSEQNKI" * 5
    p = run("DEMO_stub", demo, top=10)
    print(p.to_string(index=False))
    print("\nNOTE: uses the labelled placeholder model; the DMS-trained predictor is a Phase-1.5 deliverable.")
