"""WS-ATLAS unit tests (Phase 4.0) - mesh-upgraded atlas (honest parity when oracles deferred, OOD-gated) +
the AAV packaging-margin delivery-oracle refinement. CI-safe."""
from __future__ import annotations

from pen_stack.verify import verify
from pen_stack.wgenome import mesh_features


def test_revalidate_reports_parity_when_oracles_deferred():
    r = mesh_features.revalidate_atlas()
    assert r["available"] is True
    # offline/CI: oracle backends deferred -> features unchanged -> honest parity vs v3.x, never hidden
    assert r["mesh_features_available"] is False
    assert r["delta"] == 0.0 and r["verdict"] == "parity"
    assert r["v3x_blind_gsh_auroc"] == r["mesh_blind_gsh_auroc"]
    assert r["ood_gated"] is True


def test_attach_oracle_features_is_ood_gated_and_does_not_fabricate():
    out = mesh_features.attach_oracle_features([{"locus": "AAVS1"}], in_distribution=False)
    # OOD locus -> not scored without a flag; no fabricated mesh feature attached
    assert out["mesh_features_added"] == 0
    assert "mesh_alphagenome_variant_effect" not in out["rows"][0]


def test_aav_packaging_margin_flags_near_limit_not_comfortable():
    # near the single-AAV limit (cap 4700) -> soft flag; comfortably small -> no flag
    near = verify(dict(write_type="insertion", writer_family="bridge_IS110", cargo_bp=4500,
                       delivery_vehicle="AAV_single"))
    comfy = verify(dict(write_type="insertion", writer_family="bridge_IS110", cargo_bp=2000,
                        delivery_vehicle="AAV_single"))
    near_flags = [s["rule_id"] for s in near.soft_flags]
    comfy_flags = [s["rule_id"] for s in comfy.soft_flags]
    assert "delivery.aav_packaging_margin" in near_flags
    assert "delivery.aav_packaging_margin" not in comfy_flags
    # both are still LEGAL (soft penalty, not a hard reject)
    assert near.legal is True and comfy.legal is True


def test_packaging_margin_not_applied_to_non_aav():
    # a non-AAV vehicle does not raise the AAV packaging-margin flag
    v = verify(dict(write_type="insertion", writer_family="bridge_IS110", cargo_bp=7000,
                    delivery_vehicle="lentivirus"))
    assert "delivery.aav_packaging_margin" not in [s["rule_id"] for s in v.soft_flags]
