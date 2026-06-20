"""WS-WV unit tests (Phase 4.0) - writer-verification: score/critique, never invent. CI-safe (frozen panel
when the Perry DMS is absent; structure oracle deferred without a backend)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from pen_stack.atlas import writer_verify as WV

# the Perry 2025 Table S3 DMS (verification only); present on the Drive/VM, absent in bare CI
_PERRY_S3 = Path(__file__).resolve().parents[2].parent / "Perry_et_al" / "science.adz0276_table_s3.xlsx"


def test_frozen_panel_matches_real_perry_dms_table_s3():
    """The frozen panel + catalytic residues must be VERBATIM from Perry Table S3 - never fabricated.
    Skips when the (copyrighted, local) Perry table is absent; runs on the Drive/VM."""
    if not _PERRY_S3.exists() or os.environ.get("PEN_SKIP_PERRY"):
        pytest.skip("Perry 2025 Table S3 not present (local/Drive only)")
    pd = pytest.importorskip("pandas")
    z = dict(zip(*[pd.read_excel(_PERRY_S3, sheet_name="L2FC_Relative_Z-Scores")[c]
                   for c in ("Mutation", "Z_Score_wrt_WT")]))
    for variant, frozen in WV._FROZEN_DMS_Z.items():
        real = float(z[str(variant)])
        assert abs(real - frozen) < 0.0015, f"{variant}: frozen {frozen} != measured {real:.4f}"
    # catalytic residues match the "Residue Groups" sheet (1-based here vs 0-based in code)
    rg = pd.read_excel(_PERRY_S3, sheet_name="Residue Groups")
    cat = rg[rg["Catalytic_Residues"].astype(str).str.strip() == "Catalytic"]
    aa3 = {"ASP": "D", "GLU": "E", "SER": "S", "THR": "T", "TYR": "Y"}
    real_cat = {int(r["Residue_Number"]): aa3.get(str(r["Residue"]).strip(), "?")
                for _, r in cat.iterrows()}
    assert {k + 1: v for k, v in WV._CORE_RESIDUES.items()} == real_cat


def test_blind_recovery_recovers_known_enhancers_above_worse():
    r = WV.blind_recovery()
    assert r["available"] and r["all_enhancers_recovered"] is True
    assert r["enhancers_outrank_worse"] is True
    for e in ("N322P", "H50K", "R278M"):
        assert r["recovered"][e] is True


def test_measured_variant_is_claimable_unmeasured_is_not():
    scores = {s.variant: s for s in WV.score_variants(["N322P", "ZZZ999A"])}
    assert scores["N322P"].claimable is True and scores["N322P"].in_dms is True
    assert scores["N322P"].score is not None and scores["N322P"].interval is not None
    # a variant with no measured/in-distribution support: flagged, NOT claimable, NO activity asserted
    assert scores["ZZZ999A"].claimable is False and scores["ZZZ999A"].extrapolating is True
    assert scores["ZZZ999A"].score is None


def test_critique_flags_a_bad_candidate_and_never_claims_it_works():
    c = WV.critique_candidate("M" + "A" * 330, writer_family="bridge_IS110",
                              site_seq="ACGT", delivery_vehicle="AAV_single")
    assert c["pass"] is False
    assert c["no_claim"] is True and c["claimable"] is False # WV2 never asserts a generated writer works
    assert "active_site_implausible" in c["flags"] or "fold_unverified" in c["flags"]


def test_critique_fold_unverified_without_structure_backend():
    c = WV.critique_candidate("MKT" * 110)
    # no AF3/Boltz/Chai/Protenix backend in CI -> fold is unverified, not assumed
    assert c["fold_ok"] is False and "fold_unverified" in c["flags"]
    assert c["claimable"] is False


def test_verifier_attaches_writer_critique_as_scope_not_confidence():
    from pen_stack.verify import verify
    v = verify(dict(write_type="insertion", writer_family="bridge_IS110", cargo_bp=3000,
                    delivery_vehicle="AAV_single", writer_candidate_seq="M" + "A" * 330))
    assert v.writer_critique is not None
    assert v.writer_critique["no_claim"] is True and v.writer_critique["claimable"] is False
    assert any(s.get("kind") == "writer_candidate_critique" for s in v.scope_flags)
    assert v.no_fabrication is True
    # control: no candidate -> no critique
    v2 = verify(dict(write_type="insertion", writer_family="bridge_IS110", cargo_bp=3000,
                     delivery_vehicle="AAV_single"))
    assert v2.writer_critique is None
