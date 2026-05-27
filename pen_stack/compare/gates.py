"""5 TrueWriterScore gate functions: 1 necessary + 4 qualifying.

All thresholds come from config/gates_v3.yaml (SHA-256 locked at pre-registration).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "gates_v3.yaml"
CONFIG = yaml.safe_load(_CONFIG_PATH.read_text())

ELIGIBLE_EVIDENCE = frozenset(CONFIG["qualifying_gates"]["gate_5_evidence"]["eligible_sources"])


class GateRole(Enum):
    NECESSARY = "necessary"
    QUALIFYING = "qualifying"


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    name: str
    role: GateRole
    passes: bool
    observed_value: float | None
    threshold: float | None
    rationale: str


def gate_1_dsb(s_dsb: float, threshold: float | None = None) -> GateResult:
    """NECESSARY gate — DSB Avoidance. Failing auto-classifies as NOT_WRITER."""
    cfg = CONFIG["necessary_gates"]["gate_1_dsb"]
    t = threshold if threshold is not None else float(cfg["threshold"])
    passes = s_dsb >= t
    return GateResult(
        gate_id="gate_1_dsb",
        name=cfg["name"],
        role=GateRole.NECESSARY,
        passes=passes,
        observed_value=s_dsb,
        threshold=t,
        rationale=f"S_DSB={s_dsb:.3f} {'≥' if passes else '<'} {t} (NECESSARY)",
    )


def gate_2_programmability(s_prog: float, threshold: float | None = None) -> GateResult:
    """QUALIFYING gate — Programmability."""
    cfg = CONFIG["qualifying_gates"]["gate_2_programmability"]
    t = threshold if threshold is not None else float(cfg["threshold"])
    passes = s_prog >= t
    return GateResult(
        gate_id="gate_2_programmability",
        name=cfg["name"],
        role=GateRole.QUALIFYING,
        passes=passes,
        observed_value=s_prog,
        threshold=t,
        rationale=f"S_Prog={s_prog:.3f} {'≥' if passes else '<'} {t}",
    )


def gate_3_native_cargo(
    s_cargo: float,
    intrinsic_cargo_mechanism: bool,
    threshold: float | None = None,
) -> GateResult:
    """QUALIFYING gate — Native Cargo Capability.

    Requires BOTH S_Cargo >= threshold AND intrinsic_cargo_mechanism=True.
    HDR-template-based cargo (SpCas9) does not satisfy intrinsic_cargo_mechanism.
    """
    cfg = CONFIG["qualifying_gates"]["gate_3_native_cargo"]
    t = threshold if threshold is not None else float(cfg["threshold"])
    passes = (s_cargo >= t) and intrinsic_cargo_mechanism
    return GateResult(
        gate_id="gate_3_native_cargo",
        name=cfg["name"],
        role=GateRole.QUALIFYING,
        passes=passes,
        observed_value=s_cargo,
        threshold=t,
        rationale=(
            f"S_Cargo={s_cargo:.3f}, intrinsic={intrinsic_cargo_mechanism}; "
            f"need S_Cargo≥{t} AND intrinsic cargo mechanism"
        ),
    )


def gate_4_deliverability(
    length_aa: int | None,
    split_aav_eligible: bool = False,
    size_max: int = 900,
) -> GateResult:
    """QUALIFYING gate — Deliverability (AAV-compatible size).

    Passes if length_aa <= size_max OR split_aav_eligible.
    When length_aa is None (not yet annotated), passes if split_aav_eligible=True.
    """
    cfg = CONFIG["qualifying_gates"]["gate_4_deliverability"]
    if length_aa is None:
        passes = split_aav_eligible
        obs = None
        rationale = f"length_aa=unknown, split_aav={split_aav_eligible}, size_max={size_max}"
    else:
        passes = (length_aa <= size_max) or split_aav_eligible
        obs = float(length_aa)
        rationale = f"length={length_aa}aa, split_aav={split_aav_eligible}, size_max={size_max}"
    return GateResult(
        gate_id="gate_4_deliverability",
        name=cfg["name"],
        role=GateRole.QUALIFYING,
        passes=passes,
        observed_value=obs,
        threshold=float(size_max),
        rationale=rationale,
    )


def gate_5_evidence(evidence_sources: list[str]) -> GateResult:
    """QUALIFYING gate — Evidence (≥ 2 eligible sources)."""
    cfg = CONFIG["qualifying_gates"]["gate_5_evidence"]
    provided = set(evidence_sources) & ELIGIBLE_EVIDENCE
    passes = len(provided) >= 2
    return GateResult(
        gate_id="gate_5_evidence",
        name=cfg["name"],
        role=GateRole.QUALIFYING,
        passes=passes,
        observed_value=float(len(provided)),
        threshold=2.0,
        rationale=f"sources={sorted(provided)} (need ≥2 of {sorted(ELIGIBLE_EVIDENCE)})",
    )
