"""WS-CRIT + WS-SCOPE2 unit tests (Phase 5.0) - self-critique/revise loop (falsifiable) + scope ledger.
CI-safe (verifier-backed)."""
from __future__ import annotations

from pen_stack.agent.co_scientist import (
    critique,
    critique_and_revise,
    critique_falsifiability,
    scope_ledger,
)


def test_critique_flags_and_revises_an_illegal_design():
    cr = critique_and_revise({"write_type": "insertion", "writer_family": "bridge_IS110",
                              "cargo_bp": 30000, "delivery_vehicle": "AAV_single"})
    assert cr["revised"] is True and cr["improved"] is True       # oversize -> bigger DNA vehicle
    assert cr["before"]["legal"] is False and cr["after"]["legal"] is True
    assert cr["no_fabrication"] is True


def test_critic_only_flags_never_invents_a_number():
    c = critique({"write_type": "insertion", "writer_family": "Cas9", "cargo_bp": 1000,
                  "delivery_vehicle": "AAV_single"})
    assert c["no_fabrication"] is True
    # the suggested revision is a design-level SWAP (a vehicle name), not a fabricated quantity
    assert c["suggested_revision"] is None or isinstance(c["suggested_revision"].get("delivery_vehicle"), str)


def test_self_critique_is_falsifiable_and_useful_on_flawed_not_clean():
    f = critique_falsifiability()
    assert f["available"] and f["flawed_improve_rate"] == 1.0      # improves every flawed design
    assert f["clean_spurious_revisions"] == 0                      # never spuriously revises a clean design
    assert f["useful"] is True and f["no_fabrication"] is True


def test_scope_ledger_is_complete_and_itemises_out_of_scope():
    sl = scope_ledger({"write_type": "insertion", "writer_family": "bridge_IS110", "cargo_bp": 3000,
                       "delivery_vehicle": "AAV_single", "safety": 0.8, "p_durable": 0.7,
                       "writer_activity": 0.7})
    assert sl["complete"] is True and sl["n_assessed"] >= 4 and sl["n_not_assessed"] >= 4
    assessed = {a["dimension"] for a in sl["assessed"]}
    assert {"rule_legality", "calibrated_confidence"} <= assessed
    not_ids = {x["id"] for x in sl["not_assessed"]}
    # the standing known-unknowns are itemised, never silently omitted
    assert {"in_vivo_immunogenicity", "long_term_clinical_durability", "structure_to_phenotype"} <= not_ids
    assert sl["no_fabrication"] is True
