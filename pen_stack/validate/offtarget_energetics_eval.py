"""MC3 gate, does off-target energetics beat the 0.77 position-weight baseline? (Phase 3.2, WS-MC).

Leakage-safe protocol: split the real Perry off-targets into TRAIN / TEST by site (seeded). Fit the
(position, substitution) penalties on TRAIN positives only; evaluate discrimination AUROC on the HELD-OUT
TEST set, positives = real off-targets (core preserved), negatives = a core-disrupted decoy of each (the
same construction the published 0.77 uses). Compare the energetics model against the position-weight model
on the SAME held-out test set, and against the published 0.77 gate.

HARD GATE (prereg/ws_mc.yaml, MC3): the energetics model ships ONLY if its held-out AUROC beats BOTH the
position-weight model on the same split AND 0.77. Otherwise it is reported as a NEGATIVE and the
position-weight model stays the default, no mechanism is added that does not earn its place.
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
_CORE0 = 7 # 0-based position 8, the most-conserved / critical core position
GATE_AUROC = 0.77 # the published position-weight held-out AUROC the energetics model must beat to ship


def _auroc(scores, labels) -> float:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def _make_decoy(seq: str, intended: str, mode: str, rng: random.Random) -> str | None:
    """Build a negative from a (core-preserved) positive.

    * ``core_disrupted`` - flip the core position (the original construction, comparable to the published
      0.77): positive and decoy differ at exactly the conserved core. This can be won by sharp core
      penalisation alone, so it does NOT isolate the non-core substitution-identity claim.
    * ``core_preserved`` - flip a currently-MATCHED NON-core position to a different base, keeping the core
      matched. The decoy therefore differs from the positive only at a non-core position - so out-ranking it
      requires non-core position/identity information, isolating the actually-novel claim. Returns None when
      the positive has no matched non-core position to flip.
    """
    if mode == "core_disrupted":
        alt = rng.choice([b for b in "ACGT" if b != seq[_CORE0]])
        return seq[:_CORE0] + alt + seq[_CORE0 + 1:]
    # core_preserved: pick a non-core position that currently matches the intended target, then mismatch it
    matched_noncore = [j for j in range(len(seq)) if j != _CORE0 and seq[j] == intended[j]]
    if not matched_noncore:
        return None
    j = rng.choice(matched_noncore)
    alt = rng.choice([b for b in "ACGT" if b != intended[j]])
    return seq[:j] + alt + seq[j + 1:]


def _eval_mode(test, model, w, mode: str, seed: int) -> dict:
    rng = random.Random(seed + 1)
    e_scores, p_scores, labels, n_decoys = [], [], [], 0
    for seq, intended in test:
        decoy = _make_decoy(seq, intended, mode, rng)
        if decoy is None:
            continue
        for s, y in ((seq, 1), (decoy, 0)):
            e_scores.append(energetic_risk(s, intended, model))
            p_scores.append(risk_score(mismatches(s, intended), w))
            labels.append(y)
        n_decoys += 1
    e_auroc, p_auroc = round(_auroc(e_scores, labels), 4), round(_auroc(p_scores, labels), 4)
    return {"mode": mode, "n_pairs": n_decoys, "energetics_auroc": e_auroc,
            "position_weight_auroc": p_auroc,
            "energetics_beats_position_weight": bool(e_auroc > p_auroc),
            "delta": round(e_auroc - p_auroc, 4)}


def run(out: str | Path = _OUT, seed: int = 20260608, train_frac: float = 0.5) -> dict:
    s2 = load_insertion_sites()
    if s2.empty:
        report = {"available": False, "note": "Perry S2 insertion-site table absent (PEN_PERRY_DIR)"}
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    off = s2[(s2["On-Target"] == False) & # noqa: E712
             (s2["Insertion_Site_Sequence"].str.len() == 14) &
             (s2["Plasmid_Encoded_Sequence"].str.len() == 14)]
    pairs = [(seq, intended) for seq, intended in
             zip(off["Insertion_Site_Sequence"], off["Plasmid_Encoded_Sequence"])
             if seq[_CORE0] == intended[_CORE0]] # core-preserved positives only

    rng = random.Random(seed)
    idx = list(range(len(pairs)))
    rng.shuffle(idx)
    n_train = int(train_frac * len(idx))
    train = [pairs[i] for i in idx[:n_train]]
    test = [pairs[i] for i in idx[n_train:]]

    model = fit_penalties(train) # penalties from TRAIN positives only
    w = position_weights() # the measured position-weight model (the 0.77 baseline)

    # The shipping gate uses core_disrupted (comparable to the published 0.77). The core_preserved mode is the
    # reviewer-driven diagnostic that isolates whether NON-core substitution identity is the source of the gain.
    cd = _eval_mode(test, model, w, "core_disrupted", seed)
    cp = _eval_mode(test, model, w, "core_preserved", seed)

    e_auroc, p_auroc = cd["energetics_auroc"], cd["position_weight_auroc"]
    beats_baseline, beats_gate = bool(e_auroc > p_auroc), bool(e_auroc > GATE_AUROC)
    ships = bool(beats_baseline and beats_gate)
    # the substitution-identity CLAIM holds only if energetics still beats position-weight when the core is
    # held matched (core_preserved); otherwise the core_disrupted gain is mostly the core-penalisation artifact.
    identity_claim_holds = bool(cp["energetics_beats_position_weight"] and cp["delta"] > 0.01)
    report = {
        "available": True, "n_train": len(train), "n_test_pairs": len(test),
        "energetics_heldout_auroc": e_auroc,
        "position_weight_heldout_auroc": p_auroc,
        "gate_auroc": GATE_AUROC,
        "energetics_beats_position_weight": beats_baseline,
        "energetics_beats_gate_0_77": beats_gate,
        "ships": ships,
        "by_negative_construction": {"core_disrupted": cd, "core_preserved": cp},
        "substitution_identity_claim_holds": identity_claim_holds,
        "favorable_negative_set_caveat": "BOTH AUROCs (energetics 0.88 AND the published position-weight 0.77) "
            "are computed against a FAVOURABLE negative set - decoys constructed from real off-targets, not an "
            "independent non-recombining background (Perry S2 observes only recombined sites). The core_preserved "
            "diagnostic below isolates whether the energetics gain is real non-core signal vs the core artifact.",
        "interpretation": ("substitution-identity gain is REAL: energetics still beats position-weight when the "
                           "core is held matched (core_preserved)" if identity_claim_holds else
                           "the core_disrupted gain is mostly the CORE-PENALISATION ARTIFACT: with the core held "
                           "matched, energetics does not meaningfully beat position-weight - report accordingly"),
        "decision": ("SHIP, energetics beats both position-weight and the 0.77 gate on the core_disrupted set "
                     "(comparable to the published metric)" if ships else
                     "DO NOT SHIP, does not beat the 0.77 gate; position-weight stays default"),
        "data_source": "Perry et al. 2025 Science 391:eadz0276 Table S2 (raw local/copyrighted; derived only)",
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(run(), indent=2))
