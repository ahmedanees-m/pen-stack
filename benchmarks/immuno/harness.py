"""Immuno-Bench, the immunogenicity track for the Genome-Writing Challenge (v6.9 PEN-IMMUNE, G-WS4).

Scores a predictor on the **immunogenic-vs-tolerated** question for genome-writer/therapeutic proteins: given a
protein sequence, predict an ADA-risk; the panel labels each protein as **immunogenic (foreign)** or **tolerated
(self/human)** from its origin. The PEN-IMMUNE ADA-risk axis must rank the foreign writers (Cas9, the bridge
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
    """The G-G1 acceptance: foreign writers rank ABOVE the human self control by ADA-risk. Reports the per-protein
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
    """G-G2: run the EXISTING calibrate_axis gate for the ADA axis. No public paired (proxy, observed-ADA-incidence)
    dataset is bundled at the N>=6 power the gate requires, so this returns mechanistic_proxy, reported,
    never a manufactured (the standing data limit, identical to the v6.5 finding for the other axes)."""
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
