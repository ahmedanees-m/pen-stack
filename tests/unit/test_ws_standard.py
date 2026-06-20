"""WS-CHALLENGE / WS-COSCI2 unit tests (Phase 5.13 → v6.0.0, the Standard).

CI-safe. Asserts:
  * the Genome-Writing Challenge scores an external submission on a HELD-OUT round (labels never in the public
    input); the PEN-STACK reference anchors at 1.0; an ungrounded submission scores lower; an immune-risk task is
    included; no circular labels; no-fabrication audited;
  * the co-scientist drives the full loop with safe + legal + calibrated + cited + scope-ledgered + IMMUNE-PROFILED
    outputs, and never fabricates; hazardous candidates are discarded.
"""
from __future__ import annotations

import pytest

from benchmarks.genome_writing_challenge.harness import Submission, evaluate, reference_submission
from pen_stack.agent.co_scientist import co_scientist_session

_BASE = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
         "cargo_bp": 3000, "cell_type": "k562", "writer_family": "bridge_IS110", "promoter": "ef1a",
         "accessibility": 0.8, "safety": 0.92, "p_durable": 0.8, "writer_activity": 0.7, "deliverability": 0.36}
_GOAL = {"gene": "AAVS1", "intent": "safe_harbour_insertion", "cargo_bp": 3000, "cell_type": "k562"}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


# --- WS-CHALLENGE ----------------------------------------------------------------------

def test_reference_anchors_and_round_is_well_formed():
    r = evaluate(reference_submission())
    assert r["aggregate"] == 1.0 # the validated reference scores all families
    assert r["immune_risk_task_included"] is True # the v5.6-grounded immune-risk task is present
    assert r["no_circular_labels"] is True and r["no_fabrication"] is True
    assert set(r["by_family"]) >= {"legality", "safety", "immune_risk"}


def test_ungrounded_submission_scores_lower():
    ung = Submission("ungrounded", lambda pi: {"legality": True, "safety": "clear",
                                               "immune_risk": "nonsense"}[pi["family"]])
    assert evaluate(ung)["aggregate"] < evaluate(reference_submission())["aggregate"]


def test_public_input_never_leaks_the_label():
    from benchmarks.genome_writing_challenge.harness import _round_tasks
    # legitimate INPUT keys per family (design, or the off-target guide + candidate sites); the LABEL never appears
    allowed = {"task_id", "family", "design", "instructions", "guide", "candidate_sites", "serotype"}
    leak_keys = {"active_set", "label", "answer", "score"}
    for t in _round_tasks("2026R1"):
        assert set(t.public_input) <= allowed
        assert not (set(t.public_input) & leak_keys) # no held-out label/answer leaks into the public input


def test_submission_abstain_does_not_crash_audit():
    abstain = Submission("abstain", lambda pi: None)
    r = evaluate(abstain)
    assert r["no_fabrication"] is True and r["aggregate"] >= 0.0 # abstaining is allowed; it just scores 0


# --- WS-COSCI2 -------------------------------------------------------------------------

def _session():
    cands = [{**_BASE, "delivery_vehicle": v} for v in ("AAV_single", "AAV_dual", "lentivirus")]
    cands.append({**_BASE, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}) # hazard
    return co_scientist_session(_GOAL, "k562", candidates=cands, actor="scientist")


def test_co_scientist_drives_full_loop_immune_first_class():
    s = _session()
    assert s["n_designs"] == 3 and s["no_fabrication"] is True # hazard discarded; nothing fabricated
    assert s["strategies"] # v5.8 Pareto frontier
    assert all("interval" in o for o in s["predicted_outcomes"]) # v5.9 calibrated outcomes
    assert s["suggested_experiments"] # v5.10 experiments
    assert set(s["safety"]) <= {"clear", "flag"} # v5.7 all cleared/flagged
    assert "assessed" in s["scope_ledger"] # v5.0 scope ledger


def test_co_scientist_immune_profiles_present_and_uncollapsed():
    s = _session()
    assert len(s["immune_profiles"]) == s["n_designs"]
    for p in s["immune_profiles"]:
        assert p is not None and "axes" in p
        assert p["collapsed_score"] is None # v5.6 invariant preserved end-to-end
