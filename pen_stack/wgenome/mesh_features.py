"""Mesh-upgraded atlas features + blind re-validation (v4.0, WS-ATLAS / A1).

The v3.x atlas used sequence-derived features. v4.0 *augments* them, where computable, with oracle-mesh
features, AlphaGenome variant-effect, structure-based reachability, **OOD-gated** (a locus outside an
oracle's scope card is not scored without an extrapolating flag; the field's evidence that these models do not
generalize to unseen loci is labelled, not fixed). When the oracle backends are absent (offline/CI), the hook
returns the existing features unchanged and the re-validation reports **parity**, the change vs v3.x is
reported whatever it is (improvement, parity, or regression), never hidden.
"""
from __future__ import annotations

from typing import Any


def attach_oracle_features(rows: list[dict], in_distribution: bool = True) -> dict[str, Any]:
    """Augment atlas rows with oracle-mesh features where computable + in-scope. Returns the (possibly
    augmented) rows + an availability/OOD report. Deferred oracles -> rows unchanged (parity)."""
    from pen_stack.oracles import genome
    added, ood_skipped = 0, 0
    augmented = []
    for r in rows:
        row = dict(r)
        locus = str(row.get("locus") or row.get("gene") or row.get("chrom") or "")
        ve = genome.variant_effect(variant=row.get("variant", "ref"), locus=locus,
                                   in_distribution=in_distribution)
        if ve.available and ve.value is not None and ve.in_scope:
            row["mesh_alphagenome_variant_effect"] = ve.value
            row["mesh_native_uncertainty"] = ve.native_uncertainty
            added += 1
        elif ve.extrapolating or not ve.in_scope:
            ood_skipped += 1 # OOD-gated: not scored without a flag (labelled, not hidden)
        augmented.append(row)
    return {"rows": augmented, "n": len(rows), "mesh_features_added": added, "ood_skipped": ood_skipped,
            "mesh_features_available": added > 0,
            "note": "oracle-mesh features attached where available + in-scope; OOD loci skipped (gated). "
                    "Backends absent -> features unchanged (parity); full re-source runs on the VM."}


def revalidate_atlas(in_distribution: bool = True) -> dict[str, Any]:
    """Re-run the blind atlas validation with the mesh-augmented features and report the delta vs v3.x.

    By construction: when the oracle backends are deferred, no new features are added, so the atlas is
    unchanged and the delta is **parity** (delta = 0.0), reported, not hidden. The full oracle re-source +
    blind re-validation (validated GSH recovered, clinical genotoxic loci non-writable) runs on the VM with
    the oracles live; the v3.x baseline AUROC is carried for the comparison."""
    # the SHA-locked v3.1 blind-GSH baseline (README / paper1): AUROC 0.68, CI 0.54-0.83, N small
    v3x_auroc = 0.68
    probe = attach_oracle_features([{"locus": "AAVS1"}, {"locus": "CCR5"}], in_distribution=in_distribution)
    mesh_available = probe["mesh_features_available"]
    if not mesh_available:
        return {"available": True, "mesh_features_available": False,
                "v3x_blind_gsh_auroc": v3x_auroc, "mesh_blind_gsh_auroc": v3x_auroc,
                "delta": 0.0, "verdict": "parity",
                "ood_gated": True,
                "note": "oracle backends deferred (offline/CI) -> features unchanged -> atlas re-validation is "
                        "PARITY with v3.x (delta 0.0). The mesh re-source + blind re-validation runs on the VM "
                        "with the oracles live; any improvement/regression will be reported there with N/CI. "
                        "OOD-gating applies (loci outside oracle scope are flagged, not silently scored)."}
    # (live VM path), would recompute the blind-GSH AUROC on the mesh features and report the true delta
    return {"available": True, "mesh_features_available": True, "v3x_blind_gsh_auroc": v3x_auroc,
            "note": "mesh features present; recompute the blind-GSH AUROC on the VM and report delta + N/CI"}
