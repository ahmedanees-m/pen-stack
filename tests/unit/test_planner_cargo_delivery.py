"""Phase 3, Steps 3.2-3.3 — cargo/donor design + delivery recommendation."""
from __future__ import annotations

from pen_stack.planner.cargo import design_cargo
from pen_stack.planner.delivery import recommend_delivery


def test_cargo_elements_and_size_check():
    wr = {"family": "bridge_IS110", "cargo_capacity_bp": 5000, "deliv_class": "AAV"}
    c = design_cargo(3200, wr, ("chr19", 55090000), "hspc")
    assert c["size_ok"] is True
    assert {"insulator_5", "promoter", "polyA", "insulator_3"} <= set(c["elements"])
    assert c["codon_optimised"] is True
    # bridge family -> off-target field present; the Phase-1.5 engine is now built, so the hook is
    # engine-backed (engine_ready without a genome/core, or scanned when one is supplied).
    assert c["offtargets"]["status"] in {"engine_ready", "scanned"}


def test_cargo_oversize_flagged():
    wr = {"family": "bridge_IS110", "cargo_capacity_bp": 5000, "deliv_class": "AAV"}
    assert design_cargo(6000, wr, ("chr1", 1), "k562")["size_ok"] is False


def test_delivery_single_aav_for_iscro4_cassette():
    # 326 aa ISCro4 + 3.2 kb cassette -> single AAV (program success example)
    d = recommend_delivery(326 * 3, 3200, "hspc")
    assert d["delivery"] == "AAV (single)"


def test_delivery_large_payload_fallback():
    assert "ex vivo" in recommend_delivery(1500 * 3, 36000, "hspc")["delivery"]
    assert recommend_delivery(500 * 3, 8000, "hepg2")["delivery"] in {"dual-AAV", "LNP-mRNA (in vivo, tissue-dependent)"}
