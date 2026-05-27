"""Triangulator: compare claims across the 4 PEN-STACK packages.

Each discrepancy category corresponds to a rule in config/triangulation_rules_v3.yaml.
Rules are applied to every row in the unified editor universe; results are returned
as DiscrepancyRecord objects that can be serialised to a Parquet file.
"""

from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
import yaml


@dataclass
class DiscrepancyRecord:
    entity_id: str
    source: str  # "natural" | "design"
    category: str  # matches a key in triangulation_rules_v3.yaml
    severity: str  # high | medium | low
    sources_involved: str  # pipe-separated source names
    details: str  # human-readable explanation of the discrepancy


class Triangulator:
    def __init__(
        self,
        rules_path: Path = Path("config/triangulation_rules_v3.yaml"),
    ) -> None:
        self.rules = yaml.safe_load(rules_path.read_text())

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def audit(self, entity_id: str, universe: pd.DataFrame) -> list[DiscrepancyRecord]:
        """Return all discrepancy records for one entity."""
        rows = universe[universe["entity_id"] == entity_id]
        if rows.empty:
            return []
        row = rows.iloc[0]
        return list(self._apply_all_rules(row))

    def run_full(self, universe: pd.DataFrame) -> pd.DataFrame:
        """Apply all rules to the full universe; return a flat DataFrame."""
        records: list[dict] = []
        for _, row in universe.iterrows():
            for rec in self._apply_all_rules(row):
                records.append(asdict(rec))
        if not records:
            return pd.DataFrame(columns=list(DiscrepancyRecord.__dataclass_fields__))
        return pd.DataFrame(records)

    # ──────────────────────────────────────────────────────────────────────────
    # Rule implementations
    # ──────────────────────────────────────────────────────────────────────────

    def _apply_all_rules(self, row: pd.Series) -> Iterator[DiscrepancyRecord]:
        yield from self._rule_axis_vs_tier(row)
        yield from self._rule_mech_vs_pfam(row)
        yield from self._rule_cargo_inconsistency(row)
        yield from self._rule_evidence_gap(row)
        yield from self._rule_size_inconsistency(row)

    def _rule_axis_vs_tier(self, row: pd.Series) -> Iterator[DiscrepancyRecord]:
        """AXIS_VS_TIER (high): S_DSB contradicts mech-class tier_a_gate for natural editors."""
        if row.get("source") != "natural":
            return
        s_dsb = _float(row, "s_dsb")
        tier_a = bool(row.get("tier_a_gate", False))
        cfg = self.rules["discrepancy_categories"]["AXIS_VS_TIER"]

        if s_dsb is not None and s_dsb >= 0.95 and not tier_a:
            yield DiscrepancyRecord(
                entity_id=str(row["entity_id"]),
                source="natural",
                category="AXIS_VS_TIER",
                severity=cfg["severity"],
                sources_involved="MECH_CLASS|PEN_SCORE",
                details=(
                    f"S_DSB={s_dsb:.3f} ≥ 0.95 (pen-score: DSB-free) "
                    f"but tier_a_gate=False (mech-class: not IS110 Tier-A). "
                    f"pen-score and mech-class disagree on DSB-avoidance classification."
                ),
            )

        if s_dsb is not None and s_dsb < 0.80 and tier_a:
            yield DiscrepancyRecord(
                entity_id=str(row["entity_id"]),
                source="natural",
                category="AXIS_VS_TIER",
                severity=cfg["severity"],
                sources_involved="MECH_CLASS|PEN_SCORE",
                details=(
                    f"tier_a_gate=True (mech-class: IS110 Tier-A) "
                    f"but S_DSB={s_dsb:.3f} < 0.80 (pen-score: unexpectedly low for IS110). "
                    f"Possible OOD probe or scoring artefact."
                ),
            )

    def _rule_mech_vs_pfam(self, row: pd.Series) -> Iterator[DiscrepancyRecord]:
        """MECH_VS_PFAM (high): PFAM-based atlas classification disagrees with mech-class tier."""
        if row.get("source") != "natural":
            return
        atlas = bool(row.get("atlas_system_present", False))
        tier_a = bool(row.get("tier_a_gate", False))
        s_dsb = _float(row, "s_dsb")
        cfg = self.rules["discrepancy_categories"]["MECH_VS_PFAM"]

        # In atlas (PFAM evidence for DSB-free) but mech-class says NOT IS110
        if atlas and not tier_a and s_dsb is not None and s_dsb >= 0.95:
            yield DiscrepancyRecord(
                entity_id=str(row["entity_id"]),
                source="natural",
                category="MECH_VS_PFAM",
                severity=cfg["severity"],
                sources_involved="GENOME_ATLAS|MECH_CLASS",
                details=(
                    f"atlas_system_present=True (genome-atlas has PFAM-based entry) "
                    f"and S_DSB={s_dsb:.3f} (pen-score: DSB-free), "
                    f"but tier_a_gate=False (mech-class: not IS110 Tier-A). "
                    f"PFAM evidence supports DSB-free mechanism; mech-class disagrees."
                ),
            )

        # mech-class says IS110 but no atlas entry — PFAM evidence absent
        if tier_a and not atlas and s_dsb is not None and s_dsb >= 0.95:
            yield DiscrepancyRecord(
                entity_id=str(row["entity_id"]),
                source="natural",
                category="MECH_VS_PFAM",
                severity=cfg["severity"],
                sources_involved="GENOME_ATLAS|MECH_CLASS",
                details=(
                    "tier_a_gate=True (mech-class: IS110 Tier-A) "
                    "but atlas_system_present=False (genome-atlas has no entry). "
                    "mech-class calls IS110 without supporting PFAM atlas record."
                ),
            )

    def _rule_cargo_inconsistency(self, row: pd.Series) -> Iterator[DiscrepancyRecord]:
        """CARGO_INCONSISTENCY (medium): intrinsic_cargo=True but S_Cargo < 0.60."""
        intrinsic = bool(row.get("intrinsic_cargo_mechanism", False))
        s_cargo = _float(row, "s_cargo")
        cfg = self.rules["discrepancy_categories"]["CARGO_INCONSISTENCY"]

        if intrinsic and s_cargo is not None and s_cargo < 0.60:
            yield DiscrepancyRecord(
                entity_id=str(row["entity_id"]),
                source=str(row.get("source", "unknown")),
                category="CARGO_INCONSISTENCY",
                severity=cfg["severity"],
                sources_involved="PEN_SCORE",
                details=(
                    f"intrinsic_cargo_mechanism=True (metadata: native cargo delivery) "
                    f"but S_Cargo={s_cargo:.3f} < 0.60 (pen-score: limited cargo demonstrated). "
                    f"Metadata flag and cargo axis score are discordant."
                ),
            )

    def _rule_evidence_gap(self, row: pd.Series) -> Iterator[DiscrepancyRecord]:
        """EVIDENCE_GAP (low): IS110 confirmed bridge recombinase with no cell-based evidence."""
        if row.get("source") != "natural":
            return
        tier_a = bool(row.get("tier_a_gate", False))
        s_dsb = _float(row, "s_dsb")
        cell = bool(row.get("cell_based_evidence", False))
        cfg = self.rules["discrepancy_categories"]["EVIDENCE_GAP"]

        if tier_a and s_dsb is not None and s_dsb >= 0.95 and not cell:
            yield DiscrepancyRecord(
                entity_id=str(row["entity_id"]),
                source="natural",
                category="EVIDENCE_GAP",
                severity=cfg["severity"],
                sources_involved="MECH_CLASS|PEN_SCORE",
                details=(
                    f"tier_a_gate=True AND S_DSB={s_dsb:.3f} (confirmed IS110 bridge recombinase) "
                    f"but cell_based_evidence=False. The Molecular Pen hypothesis is untested "
                    f"in mammalian cells for this IS110 member."
                ),
            )

    def _rule_size_inconsistency(self, row: pd.Series) -> Iterator[DiscrepancyRecord]:
        """SIZE_INCONSISTENCY (medium): atlas entry present but length_aa unknown in pen-score."""
        if row.get("source") != "natural":
            return
        atlas = bool(row.get("atlas_system_present", False))
        length_aa = row.get("length_aa")
        cfg = self.rules["discrepancy_categories"]["SIZE_INCONSISTENCY"]

        if atlas and pd.isna(length_aa):
            yield DiscrepancyRecord(
                entity_id=str(row["entity_id"]),
                source="natural",
                category="SIZE_INCONSISTENCY",
                severity=cfg["severity"],
                sources_involved="GENOME_ATLAS|PEN_SCORE",
                details=(
                    "atlas_system_present=True (genome-atlas has entry with UniProt record) "
                    "but length_aa=None in unified universe (pen-score EditorEntry does not "
                    "expose sequence length). Gate 4 deliverability falls back to split_aav "
                    "heuristic; cross-source length verification not possible."
                ),
            )


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _float(row: pd.Series, col: str) -> float | None:
    val = row.get(col)
    if val is None or (hasattr(val, "__class__") and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
