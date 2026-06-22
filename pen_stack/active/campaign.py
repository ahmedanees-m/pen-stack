"""Validation-campaign engine (v7.0, Stage J, J-WS3): point active learning at the first outcome-validated axis.

The first campaign targets the PEN-EXPRESS expression axis (Stage H), which stays a calibrated PROXY until
independent wet-lab (cassette x locus x cell type) expression measurements pass
:func:`pen_stack.validate.immune_calibration.calibrate_axis`. This engine enumerates the candidate measurements,
orders them by expected information gain (reusing :func:`pen_stack.active.design.select_batch`), shows the EIG
strategy beats random on the acquisition order (reusing
:func:`pen_stack.active.validate.retrospective_active_learning`, reps + bootstrap CI), names the gate it would
flip, and emits an executable, cloud-lab-submittable campaign spec. The campaign measures INDEPENDENT data, never
the in-silico model's own outputs. The experiments are candidates; the wet run is the standing bottleneck.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# real safe-harbour landing loci, real cell lines, promoter x reporter cassettes (a measurable expression grid)
_CASSETTES = [("EF1a-GFP", 1800), ("CMV-GFP", 1700), ("CAG-mCherry", 2200), ("PGK-luciferase", 2400)]
_LOCI = ["AAVS1", "CCR5", "CLYBL", "HPRT1"]
_CELLS = ["HEK293T", "K562", "Jurkat"]


def candidate_measurements() -> list[dict]:
    """The (cassette x locus x cell type) grid, each a design whose expression readout is the measurement."""
    out: list[dict] = []
    for cas, bp in _CASSETTES:
        for locus in _LOCI:
            for cell in _CELLS:
                out.append({
                    "write_type": "insertion", "gene": locus, "cargo_bp": bp,
                    "cell_type": cell.lower(), "cell_state": cell.lower(),
                    "edit_intent": "safe_harbour_insertion",
                    "cassette": cas, "locus": locus, "readout": "expression",
                })
    return out


def design_campaign(*, k: int = 12, reps: int = 20, rounds: int = 6) -> dict[str, Any]:
    """Order the expression measurements by EIG, validate EIG-beats-random, and name the calibrate_axis target."""
    from pen_stack.active.design import select_batch
    from pen_stack.active.validate import retrospective_active_learning
    cands = candidate_measurements()
    batch = select_batch(cands, cell_state="k562", k=min(k, len(cands)))
    val = retrospective_active_learning(reps=reps, rounds=rounds)  # active vs random/greedy + CI (CI-robust)
    target_gate = {
        "axis": "expression (Stage H / PEN-EXPRESS)",
        "gate": "pen_stack.validate.immune_calibration.calibrate_axis",
        "current": "calibrated proxy (chrom_holdout); not outcome-validated",
        "flips_to": "outcome-validated when the measured (proxy vs observed) calibration passes the gate",
        "measures": "independent wet-lab expression, never the in-silico model's own output",
    }
    return {
        "campaign": "PEN-EXPRESS expression validation",
        "n_candidates": len(cands),
        "batch": [{"cassette": e.get("cassette"), "locus": e.get("locus"), "cell": e.get("cell_type"),
                   "expected_info_gain": round(float(e.get("expected_info_gain", 0.0)), 4)} for e in batch],
        "batch_size": len(batch),
        "eig_beats_random": val["active_beats_random"],
        "active_vs_random": val["active_vs_random"],
        "target_gate": target_gate,
        "cloud_lab_executable": True,
        "autonomy_level": 3,
        "human_in_control": True,
        "no_fabrication": True,
        "note": ("the experiments are candidates ordered by information gain; the wet run that flips the axis to "
                 "outcome-validated needs a real cloud-lab partner + budget (the standing bottleneck)"),
    }


def write_campaign_spec(path: str | Path = "out/expression_validation_campaign.md") -> str:
    """Render the campaign as an executable, cloud-lab-submittable spec and write it. Returns the path."""
    c = design_campaign()
    g = c["target_gate"]
    rows = "\n".join(f"| {i + 1} | {b['cassette']} | {b['locus']} | {b['cell']} | {b['expected_info_gain']} |"
                     for i, b in enumerate(c["batch"]))
    avr = c["active_vs_random"]
    md = f"""# PEN-EXPRESS expression-validation campaign (Stage J)

The first campaign that points active learning at the measurements which would earn the program's first
outcome-validated axis. It is a candidate plan, not a result; the wet run is the standing bottleneck.

## Target gate
- Axis: **{g['axis']}**
- Gate: `{g['gate']}`
- Current: {g['current']}
- Flips to: {g['flips_to']}
- Measures: {g['measures']}

## Acquisition
- Candidate measurements: {c['n_candidates']} ((cassette x locus x cell type) grid).
- EIG beats random on the acquisition order: **{c['eig_beats_random']}** (curve-area gap {avr}).
- Autonomy: Level {c['autonomy_level']} (human in control); the biosecurity gate runs before any export.

## The next batch (ordered by expected information gain)

| # | Cassette | Locus | Cell | EIG |
|---|---|---|---|---|
{rows}

## Execution
Each row is a safe-harbour expression measurement, submittable to a cloud lab via
`pen_stack.build.cloudlab.submit` (safety-gated; mock / dry-run for v7.0). The returned readouts feed
`{g['gate']}`; when the measured proxy-vs-observed calibration passes, the expression axis becomes
outcome-validated. {c['note']}.
"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(md, encoding="utf-8")
    return str(p)
