"""Immuno-Bench, the immunogenicity track for the Genome-Writing Challenge.

Scores a predictor on the **immunogenic-vs-tolerated** question for genome-writer/therapeutic proteins: given a
protein sequence, predict an ADA-risk; the panel labels each protein as **immunogenic (foreign)** or **tolerated
(self/human)** from its origin. The ADA-risk axis must rank the foreign writers (Cas9, the bridge
recombinase ISCro4, the serine integrase Bxb1, all bacterial/phage) ABOVE the human self control (albumin).

Labels are GROUNDED (origin is the central-tolerance ground truth: self proteins are tolerated, foreign drive
ADA) and NON-CIRCULAR (the label is the protein's biological origin, not a submitter claim). The panel uses REAL
UniProt sequences (configs/writer_sequences.fasta). The ADA *calibration* against an observed-incidence set runs
through the EXISTING calibrate_axis gate and is reported (it stays at public-data power, not faked).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pen_stack.planner.ada_risk import ada_risk
from pen_stack.planner.immune_mhc2 import writer_sequences


def panel() -> list[dict]:
    """The labelled immunogenic-vs-tolerated panel (real bundled proteins; label = origin)."""
    out = []
    for name, rec in writer_sequences().items():
        out.append({"name": name, "family": rec.get("family"), "accession": rec.get("accession"),
                    "origin": rec.get("origin"), "label_immunogenic": rec.get("origin") == "foreign",
                    "seq_len": len(rec.get("seq", ""))})
    return out


def recovery() -> dict:
    """The acceptance check: foreign writers rank ABOVE the human self control by ADA-risk. Reports the per-protein
    ADA-risk, the min foreign vs max self separation, and whether the separation is clean."""
    seqs = writer_sequences()
    scored = []
    for name, rec in seqs.items():
        r = ada_risk(rec["seq"], rec.get("origin"), name=name) # real NetMHCIIpan when cached
        scored.append({"name": name, "family": rec.get("family"), "origin": rec.get("origin"),
                       "ada_risk_score": r["ada_risk_score"], "mhc2_density": r["epitope_density"],
                       "foreignness": r["foreignness"]})
    foreign = [s["ada_risk_score"] for s in scored if s["origin"] == "foreign"]
    self_ = [s["ada_risk_score"] for s in scored if s["origin"] == "self"]
    clean = bool(foreign and self_ and min(foreign) > max(self_))
    return {"panel": sorted(scored, key=lambda s: s["ada_risk_score"], reverse=True),
            "n_foreign": len(foreign), "n_self": len(self_),
            "min_foreign_ada_risk": min(foreign) if foreign else None,
            "max_self_ada_risk": max(self_) if self_ else None,
            "immunogenic_above_tolerated": clean,
            "note": "foreign writers (Cas9/ISCro4/Bxb1) rank above the human self control by ADA-risk, the "
                    "immunogenic-vs-tolerated recovery. Population-level proxy; patient ADA titer is a "
                    "known-unknown."}


def ada_calibration() -> dict:
    """Run the EXISTING calibrate_axis gate for the ADA axis. No public paired (proxy, observed-ADA-incidence)
    dataset is bundled at the N>=6 power the gate requires, so this returns mechanistic_proxy, reported,
    never a manufactured (the standing data limit, identical to the finding for the other axes)."""
    from pen_stack.validate.immune_calibration import calibrate_axis
    res = calibrate_axis([], [], axis="ada_writer")
    return {"status": res["status"], "label": res["label"],
            "note": "ADA correlation needs an observed-incidence set at N>=6 with a bootstrap CI excluding 0; not "
                    "available at public-data power -> stays (the standing wet-lab/clinical-data bottleneck)."}


# ---- external submission interface ------------------------------------------------------------
@dataclass
class Submission:
    name: str
    predict_fn: Callable[[dict], Any] # {name, family, accession, seq_len, sequence} -> ada_risk float


def public_inputs():
    seqs = writer_sequences()
    return [{"name": n, "family": r.get("family"), "accession": r.get("accession"),
             "sequence": r.get("seq"), "instructions": "return an ADA-risk float (higher = more immunogenic)"}
            for n, r in seqs.items()]


def evaluate(submission: Submission) -> dict:
    """Score a submission: does it rank foreign immunogenic proteins above tolerated self ones? (AUROC-style.)"""
    seqs = writer_sequences()
    preds, labels = [], []
    ok = True
    for pi in public_inputs():
        try:
            preds.append(float(submission.predict_fn(dict(pi))))
        except Exception: # noqa: BLE001
            preds.append(0.0)
            ok = False
        labels.append(1 if seqs[pi["name"]].get("origin") == "foreign" else 0)
    # rank-separation (fraction of foreign>self pairs correctly ordered)
    pairs = correct = 0
    for i, li in enumerate(labels):
        for j, lj in enumerate(labels):
            if li == 1 and lj == 0:
                pairs += 1
                correct += 1 if preds[i] > preds[j] else 0
    return {"submission": submission.name, "n": len(labels), "no_crash": ok,
            "rank_separation": round(correct / pairs, 3) if pairs else None}


# ---- committed metrics record -----------------------------------------------------------------
_INPUTS = ("configs/writer_sequences.fasta", "configs/mhc_epitope_oracle.yaml")


def _input_hashes() -> dict:
    """sha256 of each committed input, as the repository stores it (LF; pinned in .gitattributes)."""
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    out = {}
    for rel in _INPUTS:
        p = root / rel
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return out


def run() -> dict:
    """Emit the Stage G record: what is measured, what is only consistent, and what did not validate.

    This benchmark does not produce a validated immunogenicity result and does not claim one. Two of its
    three pre-registered criteria are structural checks on the shipped axis, and the third, the only one
    that could promote the axis, is not met for want of paired outcome data. All three are recorded.
    """
    from pen_stack.planner.immune_profile import immune_profile
    from pen_stack.validate.immune_calibration import calibrate_axis, _MIN_N

    rec = recovery()
    dens = {s["name"]: s["mhc2_density"] for s in rec["panel"]}
    foreign_d = [s["mhc2_density"] for s in rec["panel"] if s["origin"] == "foreign"]
    self_d = [s["mhc2_density"] for s in rec["panel"] if s["origin"] == "self"]

    g1 = {
        "criterion": "G-G1: foreign writers rank above the human self control on the ADA-risk axis.",
        "outcome": "CONSISTENT, BUT NOT A TEST",
        "why_not_a_test": (
            "ada_risk = epitope_density x foreignness, and foreignness is 0.0 for any protein labelled "
            "self (pen_stack/planner/ada_risk.py). Every self control therefore scores exactly 0.0 "
            "whatever its measured epitope density, so min(foreign) > max(self) holds for any panel in "
            "which no foreign protein has a density of exactly zero. The criterion cannot be failed by "
            "any measurement and must not be read as a validation."
        ),
        "separation_is_arithmetically_forced": True,
        "label_and_predictor_share_a_field": (
            "The label (origin == foreign) and the foreignness multiplier both read the same FASTA field, "
            "so a predictor that returns the origin label alone would score a perfect rank separation."
        ),
        "measured_quantity": {
            "what": "NetMHCIIpan-4.0 class-II epitope densities for the four bundled proteins.",
            "densities": dens,
            "n_foreign": len(foreign_d),
            "n_self": len(self_d),
            "min_foreign_density_minus_max_self_density": (
                round(min(foreign_d) - max(self_d), 4) if foreign_d and self_d else None
            ),
            "interval": None,
            "reason_no_interval": "n = 1 self control; no interval is computable at this panel size.",
        },
        "derived_quantity": {
            "what": "ada_risk = density x foreignness, foreignness in {self: 0.0, foreign: 1.0}.",
            "panel": rec["panel"],
        },
    }

    cal = calibrate_axis([], [], axis="ada_writer")
    g2 = {
        "criterion": (
            "G-G2: the ADA axis correlates with a public observed-incidence set, promoted only if "
            f"N >= {_MIN_N} and the bootstrap Spearman CI excludes 0."
        ),
        "outcome": "NOT MET",
        "axis_promoted": False,
        "n_paired_points_available": cal.get("n"),
        "min_n_to_validate": _MIN_N,
        "calibrate_axis_output": cal,
        "interpretation": (
            "This is the load-bearing entry. No paired (proxy, observed ADA incidence) dataset exists at "
            "the pre-registered power, so the gate refuses to promote the axis and it ships as a "
            "mechanistic proxy. The refusal is the result: it is a recorded null, not a pending run."
        ),
    }

    prof = immune_profile({"delivery_vehicle": "lnp_mrna", "writer_family": "bridge_IS110"})
    g3 = {
        "criterion": (
            "G-G3: writer_dominant_risk fires on a foreign writer and the axes are never collapsed "
            "into a single score."
        ),
        "outcome": "MET",
        "collapsed_score": prof.get("collapsed_score"),
        "axes_reported": sorted(prof.get("axes", {}) or {}) if isinstance(prof.get("axes"), dict)
                          else list(prof.get("axes") or []),
        "writer_as_antigen": prof.get("writer_as_antigen"),
    }

    return {
        "bench": "Immuno-Bench (Stage G, immunogenicity)",
        "scope": (
            "Stage G ships as a mechanism-grounded axis, not an outcome-validated one. This record exists "
            "so that status is a checkable artifact rather than prose."
        ),
        "preregistration": {
            "file": "prereg/ws_immune2.yaml",
            "note": "Cited, not amended. The pre-registration names this directory as the deliverable.",
        },
        "G-G1_tolerance_filter_consistency": g1,
        "G-G2_ada_calibration": g2,
        "G-G3_no_collapse_writer_antigen": g3,
        "summary": (
            "One criterion is met (G-G3), one is arithmetically forced and therefore not a test (G-G1), "
            "and the one that could have promoted the axis is not met for want of data (G-G2). No "
            "aggregate pass flag is emitted, because averaging a structural check with a documented null "
            "would misrepresent both."
        ),
        "inputs_sha256": _input_hashes(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
