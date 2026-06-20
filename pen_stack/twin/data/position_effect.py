"""Position-effect / expression supervision, the unified table behind Stage H (v6.7 PEN-EXPRESS, WS-D).

ONE schema over the scattered human/mouse position-effect datasets, so a single learned cassette x context
model (`twin.position_effect.PositionEffectModel`) can be trained and a held-out-cell-type benchmark
(`benchmarks/position_effect/`, TPE-Bench) can be sealed. Wrap, do not rebuild: TRIP supervision is the same
table the v3.x durability head already uses; this module just unifies it with the other sources and adds the
cassette identity + cross-dataset normalization + leakage-controlled splits.

NO FABRICATION. Each dataset is registered with its verified accession/DOI and a loader. A dataset whose raw
data is not present is reported `available=False` (an "not fetched"), never silently imputed. The only
dataset wired live in v6.7 is **TRIP** (Akhtar 2013, on the VM + pulled locally); the additional human
position-effect sources (PatchMPRA, MPIRE, lentiMPRA, Leemans) are registered with their accessions and a
loader contract, and become available when their raw data is fetched, the cross-cell-type *transfer* claim is
explicitly gated on that acquisition (documented, not asserted).

Canonical schema (one row = one integrated reporter / element measurement):
    dataset, organism, cell_type, chrom, pos, cassette, expression_raw, expression_z, silenced, <features...>
`expression_z` is z-scored WITHIN (dataset x cassette) so a promoter's strength does not leak across datasets
and the model learns the *context* effect on a comparable scale.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from pen_stack._resources import project_root

# canonical chromatin context features (subset present per dataset; missing -> excluded, never imputed silently)
FEATURE_COLS = ["atac", "dnase", "H3K27ac", "H3K4me1", "H3K4me3", "H3K9me3", "H3K27me3", "H3K36me3"]

SCHEMA = ["dataset", "organism", "cell_type", "chrom", "pos", "cassette",
          "expression_raw", "expression_z", "silenced"]


# --------------------------------------------------------------------------------------------------
# dataset registry, verified accessions/DOIs (see Final_Part_v3.0 verification pass, 2026-06-19)
# --------------------------------------------------------------------------------------------------
@dataclass
class Dataset:
    name: str
    citation: str
    doi: str
    accession: str
    organism: str
    cell_types: tuple[str, ...]
    role: str # "position_effect" (locus->expr) | "cassette_activity" (CRE/MPRA)
    loader: Callable[[Path], pd.DataFrame] | None = None
    note: str = ""
    _rel: str = "" # repo-relative raw path the loader reads (for availability check)

    def available(self, root: Path | None = None) -> bool:
        if self.loader is None or not self._rel:
            return False
        root = root or project_root()
        return (root / self._rel).exists()


def _load_trip(root: Path) -> pd.DataFrame:
    """TRIP (Akhtar 2013) mESC integrations + mES chromatin marks -> canonical schema.

    The parquet is the same `trip_with_chromatin.parquet` the durability head trains on (chrom, pos, promoter,
    expression [log2], silenced, + 5 histone marks). cassette = promoter; cell_type = mESC.
    """
    path = root / "data/external/trip/trip_with_chromatin.parquet"
    df = pd.read_parquet(path)
    marks = [c for c in FEATURE_COLS if c in df.columns]
    out = pd.DataFrame({
        "dataset": "TRIP_Akhtar2013",
        "organism": "mouse",
        "cell_type": "mESC",
        "chrom": df["chrom"].astype(str),
        "pos": df["pos"].astype("int64"),
        "cassette": df["promoter"].astype(str),
        "expression_raw": df["expression"].astype(float),
        "silenced": df["silenced"].astype(bool),
    })
    for m in marks:
        out[m] = df[m].astype(float)
    return out


def _loader_not_fetched(name: str, accession: str) -> Callable[[Path], pd.DataFrame]:
    def _raise(_root: Path) -> pd.DataFrame:
        raise FileNotFoundError(
            f"{name}: raw data not fetched (accession {accession}). v6.7 wires TRIP only; this source is "
            f"registered with its accession + loader contract and becomes available once fetched. The "
            f"cross-cell-type transfer claim is gated on this acquisition (not asserted).")
    return _raise


DATASETS: dict[str, Dataset] = {
    "TRIP_Akhtar2013": Dataset(
        name="TRIP_Akhtar2013",
        citation="Akhtar et al., Cell 2013 (thousands of reporters integrated in parallel)",
        doi="10.1016/j.cell.2013.07.018",
        accession="GEO GSE49806 (tetO) + GSE49807 (mPGK); trip.nki.nl",
        organism="mouse", cell_types=("mESC",), role="position_effect",
        loader=_load_trip, _rel="data/external/trip/trip_with_chromatin.parquet",
        note="position effect on an integrated cassette, the writing-relevant supervision (LIVE in v6.7)."),
    "PatchMPRA_Maricque2019": Dataset(
        name="PatchMPRA_Maricque2019",
        citation="Maricque, Chaudhari & Cohen, Nat Biotechnol 2019 (genomically integrated MPRA)",
        doi="10.1038/nbt.4285", accession="GEO (per paper)",
        organism="mouse", cell_types=("mESC",), role="position_effect",
        loader=_loader_not_fetched("PatchMPRA_Maricque2019", "10.1038/nbt.4285"),
        note="cassette x context separability evidence (data-gated)."),
    "MPIRE_Hong2024": Dataset(
        name="MPIRE_Hong2024",
        citation="Hong et al., Nat Commun 2024 (massively parallel insulator-activity MPRA)",
        doi="10.1038/s41467-024-52599-6", accession="GEO GSE223403; github.com/claricehong/MPIRE_insulators",
        organism="human", cell_types=("K562",), role="position_effect",
        loader=_loader_not_fetched("MPIRE_Hong2024", "GSE223403"),
        note="human K562 position/insulator context (data-gated)."),
    "lentiMPRA_Agarwal2025": Dataset(
        name="lentiMPRA_Agarwal2025",
        citation="Agarwal et al., Nature 639:411-420 (2025) (~680k regulatory elements)",
        doi="10.1038/s41586-024-08430-9", accession="ENCODE portal + GEO; bioRxiv 2023.03.05.531189",
        organism="human", cell_types=("HepG2", "K562", "WTC11"), role="cassette_activity",
        loader=_loader_not_fetched("lentiMPRA_Agarwal2025", "10.1038/s41586-024-08430-9"),
        note="cassette/CRE activity supervision across 3 human cell types (data-gated)."),
    "Leemans2019": Dataset(
        name="Leemans2019",
        citation="Leemans et al., Cell 2019 (promoter-intrinsic + local chromatin determine repression in LADs)",
        doi="10.1016/j.cell.2019.03.009", accession="GEO (per paper); van Steensel lab",
        organism="human", cell_types=("K562",), role="position_effect",
        loader=_loader_not_fetched("Leemans2019", "10.1016/j.cell.2019.03.009"),
        note="human LAD-repression context (data-gated)."),
}


def available_datasets(root: Path | None = None) -> list[str]:
    root = root or project_root()
    return [k for k, d in DATASETS.items() if d.available(root)]


# --------------------------------------------------------------------------------------------------
# normalization + loader
# --------------------------------------------------------------------------------------------------
def normalize_within(df: pd.DataFrame, by=("dataset", "cassette"), col: str = "expression_raw",
                     out: str = "expression_z") -> pd.DataFrame:
    """z-score expression within each (dataset x cassette) group, so a cassette's intrinsic strength does not
    leak across datasets and the model is supervised on the *context* deviation on a comparable scale. A
    singleton/zero-variance group maps to 0.0 (no spurious scale)."""
    df = df.copy()
    def _z(s: pd.Series) -> pd.Series:
        sd = s.std(ddof=0)
        return (s - s.mean()) / sd if sd and sd > 1e-12 else pd.Series(0.0, index=s.index)
    df[out] = df.groupby(list(by))[col].transform(_z)
    return df


def load_position_effect(datasets: list[str] | None = None, root: Path | None = None,
                         require: bool = False) -> pd.DataFrame:
    """Unified position-effect table. Loads every AVAILABLE registered dataset (or the named subset),
    concatenates to the canonical schema, and z-normalizes expression within (dataset x cassette).

    `require=True` raises if a requested dataset is unavailable; default skips unavailable ones (logging the
    skip in the returned frame's `.attrs['skipped']`), clear about what is and is not in the table.
    """
    root = root or project_root()
    names = datasets or list(DATASETS)
    frames, skipped = [], []
    for name in names:
        d = DATASETS[name]
        if not d.available(root):
            skipped.append(name)
            if require:
                d.loader(root) # raise the informative FileNotFoundError
            continue
        frames.append(d.loader(root))
    if not frames:
        raise FileNotFoundError(
            f"no position-effect dataset available under {root}. Available registry: {list(DATASETS)}; "
            f"skipped (not fetched): {skipped}. Pull TRIP via scratch/v67_pull_trip.py or set PEN_STACK_HOME.")
    df = pd.concat(frames, ignore_index=True)
    df = normalize_within(df)
    df.attrs["skipped"] = skipped
    df.attrs["datasets"] = [f["dataset"].iloc[0] for f in frames]
    # reorder: schema first, then whatever feature columns are present
    feats = [c for c in FEATURE_COLS if c in df.columns]
    return df[[c for c in SCHEMA if c in df.columns] + feats]


# --------------------------------------------------------------------------------------------------
# leakage-controlled splits
# --------------------------------------------------------------------------------------------------
def blocked_splits(df: pd.DataFrame, n_splits: int = 5, group: str = "chrom",
                   seed: int = 20260619) -> list[tuple[np.ndarray, np.ndarray]]:
    """Domain-blocked CV: no `group` (default chromosome) value appears in both train and test of a fold,
    the leakage control the position-effect task needs (nearby integrations share chromatin)."""
    from sklearn.model_selection import GroupKFold
    g = df[group].astype("category").cat.codes.to_numpy()
    k = min(n_splits, len(np.unique(g)))
    return list(GroupKFold(n_splits=k).split(df, groups=g))


def heldout_celltype_splits(df: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Leave-one-cell-type-out: train on all but one cell type, test on the held-out one. This is the headline
    transfer evaluation. With a single available cell type it returns [] and the caller reports the transfer
    axis as data-gated, never a fabricated transfer number."""
    cts = sorted(df["cell_type"].unique())
    if len(cts) < 2:
        return []
    out = []
    idx = np.arange(len(df))
    for ct in cts:
        te = idx[df["cell_type"].to_numpy() == ct]
        tr = idx[df["cell_type"].to_numpy() != ct]
        out.append((ct, tr, te))
    return out


def leakage_report(df: pd.DataFrame, splits: list[tuple[np.ndarray, np.ndarray]],
                   group: str = "chrom") -> dict:
    """Verify no `group` value is co-located across the train/test of any fold (the split's integrity claim)."""
    bad = 0
    for tr, te in splits:
        if set(df.iloc[tr][group]) & set(df.iloc[te][group]):
            bad += 1
    return {"n_folds": len(splits), "folds_with_leakage": bad, "clean": bad == 0, "group": group}
