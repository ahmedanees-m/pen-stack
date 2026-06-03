"""Phase 1.5 — bridge-recombinase off-target engine + QC.

Off-target headline property: the position-weight model beats a naive Hamming ranking *because mismatch
position matters* — a core-disrupting 2-mismatch site (recombination abolished) ranks far below a distal
2-mismatch site, while Hamming scores them identically. Fold/cross-loop QC and the Phase-3 hook are also
exercised. The genome-wide hg38 scan itself runs on the VM (pysam + hg38.fa).
"""
from __future__ import annotations

from pen_stack.bridge.fold_qc import cross_loop_risk, qc_verdict
from pen_stack.bridge.ingest import load_profile_config, protective_weights
from pen_stack.bridge.offtarget import (
    hamming_risk,
    mismatches,
    position_weights,
    predict_offtargets,
    risk_score,
)

_CORE = "AAACGTCTACGTTT"   # 14 nt, CT core at positions 7-8 (0-based 6-7)


def test_profile_covers_14_core_positions():
    w = protective_weights()
    assert set(w) == set(range(1, 15))
    cfg = load_profile_config()
    assert cfg["central_core_positions"] == [7, 8]
    assert w[7] == 1.0 and w[8] == 1.0   # central CT core is critical


def test_position_model_beats_hamming_on_position():
    w = position_weights(prefer_measured=False)   # literature profile: core weight 1.0 -> crisp mechanism
    distal = _CORE[:0] + "C" + _CORE[1:13] + "C"      # 2 mismatches at distal (tolerant) positions
    core_dis = _CORE[:6] + "A" + "A" + _CORE[8:]       # 2 mismatches at the critical CT core
    mm_d, mm_c = mismatches(distal, _CORE), mismatches(core_dis, _CORE)
    assert len(mm_d) == 2 and len(mm_c) == 2
    # position model: distal risk >> core-disrupted risk (~0); Hamming cannot tell them apart
    assert risk_score(mm_d, w) > risk_score(mm_c, w)
    assert risk_score(mm_c, w) == 0.0
    assert hamming_risk(mm_d, 14) == hamming_risk(mm_c, 14)


def test_cross_loop_and_qc():
    xl = cross_loop_risk(_CORE, "GGGCATCTAGGCCC")
    assert set(xl) == {"tbl_self", "dbl_self", "tbl_dbl"}
    assert all(0.0 <= v <= 1.0 for v in xl.values())
    # a donor complementary to the target scores higher cross-loop risk than an unrelated donor
    comp_pair = cross_loop_risk("AAAAAAAAAAAAAA", "UUUUUUUUUUUUUU")["tbl_dbl"]
    indep_pair = cross_loop_risk("AAAAAAAAAAAAAA", "GGGGGGGGGGGGGG")["tbl_dbl"]
    assert comp_pair > indep_pair
    v = qc_verdict(_CORE, "GGGCATCTAGGCCC")
    assert "pass" in v and "cross_loop" in v


def test_phase3_hook_engine_ready():
    # bridge family -> engine present (no longer 'pending'); non-bridge -> not applicable
    r = predict_offtargets("bridge_IS110", ("chr19", 55090000))
    assert r["applicable"] is True and r["status"] == "engine_ready"
    assert predict_offtargets("serine_integrase", None)["applicable"] is False
