"""MC3 gate — does off-target energetics beat the 0.77 position-weight baseline? (Phase 3.2, WS-MC).

Leakage-safe protocol: split the real Perry off-targets into TRAIN / TEST by site (seeded). Fit the
(position, substitution) penalties on TRAIN positives only; evaluate discrimination AUROC on the HELD-OUT
TEST set — positives = real off-targets (core preserved), negatives = a core-disrupted decoy of each (the
same construction the published 0.77 uses). Compare the energetics model against the position-weight model
on the SAME held-out test set, and against the published 0.77 gate.

HARD GATE (prereg/ws_mc.yaml, MC3): the energetics model ships ONLY if its held-out AUROC beats BOTH the
position-weight model on the same split AND 0.77. Otherwise it is reported as a NEGATIVE and the
position-weight model stays the default — no mechanism is added that does not earn its place.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from pen_stack.bridge.ingest import load_insertion_sites
from pen_stack.bridge.offtarget import mismatches, position_weights, risk_score
from pen_stack.bridge.offtarget_energetics import energetic_risk, fit_penalties

_ROOT = Path(__file__).resolve().parents[2]
_OUT = _ROOT / "out" / "offtarget_energetics_eval.json"
_CORE0 = 7          # 0-based position 8 — the most-conserved / critical core position
GATE_AUROC = 0.77   # the published position-weight held-out AUROC the energetics model must beat to ship


def _auroc(scores, labels) -> float:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def run(out: str | Path = _OUT, seed: int = 20260608, train_frac: float = 0.5) -> dict:
    s2 = load_insertion_sites()
    if s2.empty:
        report = {"available": False, "note": "Perry S2 insertion-site table absent (PEN_PERRY_DIR)"}
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    off = s2[(s2["On-Target"] == False) &  # noqa: E712
             (s2["Insertion_Site_Sequence"].str.len() == 14) &
             (s2["Plasmid_Encoded_Sequence"].str.len() == 14)]
    pairs = [(seq, intended) for seq, intended in
             zip(off["Insertion_Site_Sequence"], off["Plasmid_Encoded_Sequence"])
             if seq[_CORE0] == intended[_CORE0]]            # core-preserved positives only

    rng = random.Random(seed)
    idx = list(range(len(pairs)))
    rng.shuffle(idx)
    n_train = int(train_frac * len(idx))
    train = [pairs[i] for i in idx[:n_train]]
    test = [pairs[i] for i in idx[n_train:]]

    model = fit_penalties(train)            # penalties from TRAIN positives only
    w = position_weights()                  # the measured position-weight model (the 0.77 baseline)

    rng2 = random.Random(seed + 1)
    e_scores, p_scores, labels = [], [], []
    for seq, intended in test:
        mm = mismatches(seq, intended)
        e_scores.append(energetic_risk(seq, intended, model))
        p_scores.append(risk_score(mm, w))
        labels.append(1)
        alt = rng2.choice([b for b in "ACGT" if b != seq[_CORE0]])
        decoy = seq[:_CORE0] + alt + seq[_CORE0 + 1:]
        mmd = mismatches(decoy, intended)
        e_scores.append(energetic_risk(decoy, intended, model))
        p_scores.append(risk_score(mmd, w))
        labels.append(0)

    e_auroc = round(_auroc(e_scores, labels), 4)
    p_auroc = round(_auroc(p_scores, labels), 4)
    beats_baseline = bool(e_auroc > p_auroc)
    beats_gate = bool(e_auroc > GATE_AUROC)
    ships = bool(beats_baseline and beats_gate)
    report = {
        "available": True, "n_train": len(train), "n_test_pairs": len(test),
        "energetics_heldout_auroc": e_auroc,
        "position_weight_heldout_auroc": p_auroc,
        "gate_auroc": GATE_AUROC,
        "energetics_beats_position_weight": beats_baseline,
        "energetics_beats_gate_0_77": beats_gate,
        "ships": ships,
        "decision": ("SHIP — energetics beats both the position-weight model and the 0.77 gate on held-out"
                     if ships else
                     "DO NOT SHIP — energetics does not beat the 0.77 gate / position-weight on held-out; "
                     "position-weight model stays the default (honest negative, no mechanism added that does "
                     "not earn its place)"),
        "data_source": "Perry et al. 2025 Science 391:eadz0276 Table S2 (raw local/copyrighted; derived only)",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2))
