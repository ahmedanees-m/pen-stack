"""Cargo / donor design (Phase 3, Step 3.2).

Assemble a donor construct spec for a chosen writer + site: insulators (protect durability), promoter +
polyA, codon optimisation flag for the host cell type, and a size check against the writer's
deliverability/cargo class. For bridge/seek writers, attach the Phase-1.5 off-target prediction *if the
bridge engine is available* - otherwise the field is marked pending (Phase 1.5), so the Planner runs
end-to-end now and the off-target annotation drops in once Phase 1.5 lands.

We design at the level of construct *elements + sizes* (the payload sequence is the user's CDS/regulatory
cassette); element lengths are nominal, documented constants.
"""
from __future__ import annotations

# nominal element sizes (bp) for the assembled donor; documented, not hidden
_ELEMENTS = {"insulator_5": 250, "promoter": 600, "polyA": 250, "insulator_3": 250}


def _bridge_offtarget(writer_family: str, site: tuple) -> dict:
    """Optional Phase-1.5 hook. Returns the off-target prediction if the bridge engine exists, else pending."""
    try:
        from pen_stack.bridge.offtarget import predict_offtargets  # Phase 1.5 deliverable
    except Exception:  # noqa: BLE001 - engine not built yet
        return {"status": "pending_phase_1_5", "note": "bridge off-target engine ships in Phase 1.5"}
    return predict_offtargets(writer_family, site)


def design_cargo(payload_bp: int, writer_row: dict, site: tuple, ct: str) -> dict:
    """Assemble a donor construct spec. writer_row needs: family, cargo_capacity_bp, deliv_class."""
    fam = writer_row.get("family")
    cap = writer_row.get("cargo_capacity_bp")
    elements = dict(_ELEMENTS)
    assembled_bp = int(payload_bp) + sum(elements.values())
    size_ok = (cap is None) or (assembled_bp <= cap)

    out = {
        "host": ct,
        "payload_bp": int(payload_bp),
        "elements": elements,                       # insulators + promoter + polyA
        "assembled_bp": assembled_bp,
        "codon_optimised": True,
        "writer_family": fam,
        "cargo_capacity_bp": cap,
        "size_ok": size_ok,
        "deliverability": writer_row.get("deliv_class"),
    }
    if fam in {"bridge_IS110", "seek_IS1111"}:
        out["offtargets"] = _bridge_offtarget(fam, site)
    return out
