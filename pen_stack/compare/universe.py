"""Unified Editor Universe assembly (Step 5).

The universe contains one row per evaluable entity:
- Natural editor (deduplicated by UniProt across sources)
- Computational design (one row per pen-assemble design_id)

Field reconciliation: when sources disagree, precedence is
pen-score > mech-class > genome-atlas (most specific to least specific).

Run directly:
    python -m pen_stack.compare.universe
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

CANONICAL_UNIVERSE_PATH = Path("data/unified_editor_universe.parquet")

# Mechanism buckets that count as DSB-free (S_DSB = 1.0)
_DSB_FREE_BUCKETS = frozenset(
    {
        "DSB_FREE_TRANSEST_RECOMBINASE",
        "DSB_FREE_NICKASE",
        "DSB_FREE_RECOMBINASE",
        "DSB_FREE_BASE_EDITOR",
        "DSB_FREE_PRIME_EDITOR",
    }
)

UNIVERSE_COLUMNS = [
    # Identity
    "entity_id",
    "source",
    "canonical_name",
    "aliases",
    "uniprot",
    "organism",
    "length_aa",
    # Mechanism
    "mechanism_class",
    "tier_a_gate",
    "mech_class_confidence",
    # PEN-SCORE 8 axes
    "s_dsb",
    "s_prog",
    "s_cargo",
    "s_energy",
    "s_immuno",
    "s_deliv",
    "s_mature",
    "s_spec",
    "penscore",
    # PEN-COMPARE v3.2 metadata fields
    "intrinsic_cargo_mechanism",  # Gate 3: must be True for native cargo
    "cell_based_evidence",  # TRUE_WRITER tier requirement
    # Evidence sources (bool per type)
    "has_biochemical",
    "has_structural",
    "has_computational",
    "has_cell_based",
    # Provenance
    "atlas_system_present",
    "in_pen_score",
    "in_pen_assemble",
    "parent_editor",
    "strategy",  # designs only
    "primary_doi",
    "secondary_doi",
]


def assemble_unified_universe() -> pd.DataFrame:
    """Build the unified editor universe Parquet from all 4 PEN-STACK packages."""
    import genome_atlas  # type: ignore
    from pen_score import Scorer, get_editor_metadata  # type: ignore
    from pen_score.data.loader import load_editor_universe  # type: ignore

    rows: list[dict] = []

    # ── 1. Natural editors from pen-score editor_universe ────
    print("[universe] Loading pen-score editor universe...")
    editors = load_editor_universe()  # returns list[EditorEntry]
    atlas_systems = genome_atlas.load_systems()
    scorer = Scorer()  # reuse single Scorer instance across all editors

    for editor in editors:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scored = _score_with_fallback(scorer, editor.canonical_accession)
            metadata = get_editor_metadata(editor.id)
        except Exception as e:
            print(f"  WARNING: scoring failed for {editor.id}: {e}")
            continue

        atlas_present = editor.id in atlas_systems or any(
            _uniprot_matches(s, editor.canonical_accession) for s in atlas_systems.values()
        )
        rows.append(_build_natural_row(editor, scored, metadata, atlas_present))

    # ── 2. Computational designs from pen-assemble v0.5.2 ────
    print("[universe] Loading pen-assemble catalog...")
    catalog = _load_catalog()
    if catalog is not None:
        for _, design in catalog.iterrows():
            rows.append(_build_design_row(design))
    else:
        print("  WARNING: pen-assemble catalog not found — designs omitted from universe")

    df = pd.DataFrame(rows, columns=UNIVERSE_COLUMNS)
    print(f"[universe] Assembled {len(df)} entities:")
    print(f"  Natural editors: {(df['source'] == 'natural').sum()}")
    print(f"  Designs:         {(df['source'] == 'design').sum()}")
    return df


def _score_with_fallback(scorer, accession: str):
    """Score editor, clamping S_Mature to 1.0 if pen_score returns > 1.0.

    pen_score v0.1.3 can produce S_Mature > 1.0 for highly published editors
    (SpCas9, PE2, etc.) because the PubMed citation normaliser uses a fixed
    max_count=10,000 that SpCas9's citation count exceeds. Temporarily patch
    AxisScores.__init__ to clamp the value before Pydantic validates it.
    """
    from pen_score.api import AxisScores  # type: ignore

    try:
        return scorer.score_editor(accession)
    except Exception as e:
        if "S_Mature" not in str(e):
            raise  # unrelated error — propagate

    # Patch AxisScores.__init__ to clamp S_Mature ≤ 1.0
    original_init = AxisScores.__init__

    def _clamped_init(self, **data):
        if "S_Mature" in data and data["S_Mature"] is not None:
            data["S_Mature"] = min(float(data["S_Mature"]), 1.0)
        original_init(self, **data)

    AxisScores.__init__ = _clamped_init
    try:
        return scorer.score_editor(accession)
    finally:
        AxisScores.__init__ = original_init


def _uniprot_matches(system_entry, accession: str) -> bool:
    """Check if a genome_atlas SystemEntry has the given UniProt accession."""
    if hasattr(system_entry, "uniprot") and system_entry.uniprot == accession:
        return True
    proteins = getattr(system_entry, "proteins", None) or []
    return accession in proteins


def _dsb_free(mechanism_bucket: str) -> bool:
    return mechanism_bucket in _DSB_FREE_BUCKETS


def _load_catalog() -> pd.DataFrame | None:
    """Try multiple candidate paths for the pen-assemble catalog."""
    candidates = [
        # VM layout: pen-assemble repo is at ~/pen-assemble/
        Path.home() / "pen-assemble/data/catalog_v0.5.2_current.parquet",
        # Docker volume mount (mount ~/pen-assemble as /workspace/pen-assemble)
        Path("/workspace/pen-assemble/data/catalog_v0.5.2_current.parquet"),
        # Legacy search paths (repos subdirectory layout)
        Path.home() / "repos/pen-assemble/data/catalog_v0.5.2_current.parquet",
        Path("repos/pen-assemble/data/catalog_v0.5.2_current.parquet"),
    ]
    for p in candidates:
        if p.exists():
            print(f"  Loaded catalog from: {p}")
            return pd.read_parquet(p)
    return None


def _build_natural_row(editor, scored, metadata, atlas_present: bool) -> dict:
    # Tier-A gate: derive from mechanism_bucket when mech_class models not available
    tier_a = _dsb_free(editor.mechanism_bucket)

    # S_DSB fallback: if mech-class Zenodo models are not yet available,
    # derive from mechanism_bucket (deterministic: DSB-free bucket → 1.0, else 0.0)
    s_dsb = scored.axes.S_DSB
    if s_dsb is None:
        s_dsb = 1.0 if tier_a else 0.0

    return {
        "entity_id": editor.id,
        "source": "natural",
        "canonical_name": metadata.canonical_name,
        "aliases": metadata.aliases,
        "uniprot": editor.canonical_accession,
        "organism": editor.organism,
        "length_aa": None,  # not in EditorEntry schema; added in Step 17 annotation
        "mechanism_class": editor.mechanism_bucket,
        "tier_a_gate": tier_a,
        "mech_class_confidence": None,  # populated after mech-class Zenodo deposit
        "s_dsb": s_dsb,
        "s_prog": scored.axes.S_Prog,
        "s_cargo": scored.axes.S_Cargo,
        "s_energy": scored.axes.S_Energy,
        "s_immuno": scored.axes.S_Immuno,
        "s_deliv": scored.axes.S_Deliv,
        "s_mature": scored.axes.S_Mature,
        "s_spec": scored.axes.S_Spec,
        "penscore": scored.pen_score,
        "intrinsic_cargo_mechanism": metadata.intrinsic_cargo_mechanism,
        "cell_based_evidence": metadata.cell_based_evidence,
        "has_biochemical": scored.axes.S_Cargo is not None,
        "has_structural": editor.canonical_pdb is not None,
        "has_computational": tier_a,
        "has_cell_based": metadata.cell_based_evidence,
        "atlas_system_present": atlas_present,
        "in_pen_score": True,
        "in_pen_assemble": False,
        "parent_editor": editor.parent_editor,
        "strategy": None,
        "primary_doi": editor.primary_doi,
        "secondary_doi": None,
    }


def _build_design_row(design: pd.Series) -> dict:
    # Catalog columns use capital-S prefix: S_DSB_v012, S_Spec_v012, etc.
    return {
        "entity_id": design["design_id"],
        "source": "design",
        "canonical_name": design["design_id"],
        "aliases": [],
        "uniprot": None,
        "organism": "synthetic",
        "length_aa": design.get("length_aa"),
        "mechanism_class": "INHERITED",
        "tier_a_gate": True,
        "mech_class_confidence": None,
        "s_dsb": design.get("S_DSB_v012", 1.0),
        "s_prog": design.get("S_Prog_v012"),
        "s_cargo": design.get("S_Cargo_v012"),
        "s_energy": design.get("S_Energy_v012", 1.0),
        "s_immuno": design.get("S_Immuno_v012"),
        "s_deliv": design.get("S_Deliv_v012"),
        "s_mature": 0.0,
        "s_spec": design.get("S_Spec_v012"),
        "penscore": design.get("penscore_v012"),
        "intrinsic_cargo_mechanism": design.get("intrinsic_cargo_mechanism", True),
        "cell_based_evidence": design.get("cell_based_evidence", False),
        "has_biochemical": False,
        "has_structural": False,
        "has_computational": True,
        "has_cell_based": False,
        "atlas_system_present": False,
        "in_pen_score": False,
        "in_pen_assemble": True,
        "parent_editor": design.get("parent_editor"),
        "strategy": design.get("strategy"),
        "primary_doi": None,
        "secondary_doi": None,
    }


def load_universe(path: Path | str = CANONICAL_UNIVERSE_PATH) -> pd.DataFrame:
    """Load the frozen unified universe Parquet."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Unified universe not found at {p}. Run assemble_unified_universe() first."
        )
    return pd.read_parquet(p)


if __name__ == "__main__":
    df = assemble_unified_universe()
    CANONICAL_UNIVERSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CANONICAL_UNIVERSE_PATH, index=False)
    print(f"Saved to {CANONICAL_UNIVERSE_PATH}")
