"""Hierarchical TrueWriter tier classifier (v3.2).

Applies the 5 TrueWriterScore gates per config/gates_v3.yaml (SHA-256 locked).
G1 is the necessary gate: failing it auto-classifies as NOT_WRITER regardless
of all other gates.  G2–G5 are qualifying gates; tier depends on how many pass
and whether cell_based is in the evidence set.
"""

from __future__ import annotations

from dataclasses import dataclass

from pen_stack.compare.core.gates import (
    GateResult,
    GateRole,
    gate_1_dsb,
    gate_2_programmability,
    gate_3_native_cargo,
    gate_4_deliverability,
    gate_5_evidence,
)


@dataclass(frozen=True)
class TrueWriterResult:
    editor_id: str
    tier: str  # TRUE_WRITER / PROBABLE_WRITER / EMERGING_WRITER / NOT_WRITER
    necessary_gates_passed: int
    qualifying_gates_passed: int
    has_cell_based_evidence: bool
    gate_results: tuple[GateResult, ...]
    auto_demoted: bool
    auto_demote_reason: str | None


def certify(
    editor_id: str,
    s_dsb: float,
    s_prog: float,
    s_cargo: float,
    length_aa: int | None,
    evidence_sources: list[str],
    intrinsic_cargo_mechanism: bool,
    split_aav_eligible: bool = False,
    # Threshold overrides for sensitivity analysis (Steps 14–16)
    g1_threshold: float | None = None,
    g2_threshold: float | None = None,
    g3_threshold: float | None = None,
    g4_size_max: int = 900,
) -> TrueWriterResult:
    """Apply 5-gate hierarchical certification.

    Tier ladder (v3.2):
      TRUE_WRITER    — G1 pass + all 4 qualifying pass + cell_based in evidence
      PROBABLE_WRITER — G1 pass + (4 qualifying, no cell_based) OR (3 qualifying + cell_based)
      EMERGING_WRITER — G1 pass + 1–2 qualifying pass
      NOT_WRITER     — G1 FAILS (auto-demote, final) OR 0 qualifying pass
    """
    gate_results: tuple[GateResult, ...] = (
        gate_1_dsb(s_dsb, threshold=g1_threshold),
        gate_2_programmability(s_prog, threshold=g2_threshold),
        gate_3_native_cargo(s_cargo, intrinsic_cargo_mechanism, threshold=g3_threshold),
        gate_4_deliverability(length_aa, split_aav_eligible, size_max=g4_size_max),
        gate_5_evidence(evidence_sources),
    )

    necessary_passed = sum(1 for g in gate_results if g.role == GateRole.NECESSARY and g.passes)
    qualifying_passed = sum(1 for g in gate_results if g.role == GateRole.QUALIFYING and g.passes)
    has_cell_based = "cell_based" in evidence_sources

    # Necessary gate auto-fail
    if necessary_passed < 1:
        failed = [g.gate_id for g in gate_results if g.role == GateRole.NECESSARY and not g.passes]
        return TrueWriterResult(
            editor_id=editor_id,
            tier="NOT_WRITER",
            necessary_gates_passed=necessary_passed,
            qualifying_gates_passed=qualifying_passed,
            has_cell_based_evidence=has_cell_based,
            gate_results=gate_results,
            auto_demoted=True,
            auto_demote_reason=f"Necessary gate(s) failed: {failed}.",
        )

    # All necessary gates passed — assign tier within writer category
    if qualifying_passed == 4 and has_cell_based:
        tier = "TRUE_WRITER"
    elif qualifying_passed == 4 and not has_cell_based or qualifying_passed == 3 and has_cell_based:
        tier = "PROBABLE_WRITER"
    elif qualifying_passed >= 1:
        tier = "EMERGING_WRITER"
    else:
        tier = "NOT_WRITER"

    return TrueWriterResult(
        editor_id=editor_id,
        tier=tier,
        necessary_gates_passed=necessary_passed,
        qualifying_gates_passed=qualifying_passed,
        has_cell_based_evidence=has_cell_based,
        gate_results=gate_results,
        auto_demoted=False,
        auto_demote_reason=None,
    )
