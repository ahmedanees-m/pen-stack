"""WS-INNATE unit tests (Phase 5.4) - the COMPUTED nucleic-acid innate-sensing scorer (CpG O/E + U/dsRNA).

Fully CI-safe and deterministic: a pure sequence computation, no external data/model, no VM (the ViennaRNA
dsRNA sub-signal degrades gracefully when absent). Asserts: CpG observed/expected is computed correctly and
maps to a TLR9 score; DNA / mRNA / RNP forms are handled; the scorer abstains (never fabricates) on empty /
bad input; verify() surfaces the cargo innate load when a cargo sequence is supplied; the realized in-vivo
innate response stays a known-unknown and the mRNA nucleoside-modification lever is declared out of scope."""
from __future__ import annotations

import yaml

from pen_stack._resources import resource
from pen_stack.agent.cite import citations_grounded
from pen_stack.planner.innate_sensing import (
    PROVENANCE_DOIS,
    computed_innate_score,
    cpg_observed_expected,
    innate_sensing,
)


def test_cpg_observed_expected_is_correct():
    # "CGCGCG": C=3, G=3, CpG=3, L=6 -> O/E = 3/(3*3)*6 = 2.0
    c = cpg_observed_expected("CGCGCG")
    assert c["cpg_count"] == 3 and c["cpg_oe"] == 2.0
    # a CpG-free sequence -> O/E 0
    assert cpg_observed_expected("ATATATAATTAA")["cpg_oe"] == 0.0


def test_dna_cpg_maps_to_tlr9_score():
    depleted = innate_sensing("ATATAATTAACCAATTGGTTAA" * 6, "DNA") # no CpG
    rich = innate_sensing("ATCGCGATCGCGCG" * 20, "DNA") # CpG-dense
    assert depleted.available and rich.available
    assert depleted.value["innate_score"] == 1.0 # no CpG -> least TLR9
    assert rich.value["innate_score"] == 0.0 # CpG-rich -> max TLR9
    assert "TLR9" in rich.value["pathway"]
    assert rich.output_kind == "baseline" and rich.scope_card == "innate_sensing"


def test_mrna_is_partial_signal_and_flags_modification_limit():
    r = innate_sensing("AUGGCCUACGGCUUUAUCGAUCGGAUCGGCUACG" * 4, "mRNA")
    assert r.available and 0.0 <= r.value["innate_score"] <= 1.0
    assert r.extrapolating is True # sequence-only signal is PARTIAL
    assert "RIG-I" in r.value["pathway"] or "TLR7" in r.value["pathway"]
    assert "nucleoside modification" in r.note.lower() # the dominant lever is out of scope


def test_rnp_is_minimal_by_mechanism():
    r = innate_sensing("GCAUGCAUGCAU", "RNP")
    assert r.available and r.value["innate_score"] == 0.9
    assert "transient" in r.note.lower()


def test_scorer_abstains_on_empty_or_bad_input():
    assert innate_sensing("", "DNA").available is False
    assert innate_sensing("ACGT", "plasmidoid").available is False
    score, res = computed_innate_score("", "DNA")
    assert score is None and res.available is False


def test_verify_surfaces_cargo_innate_when_sequence_supplied():
    from pen_stack.verify import verify
    v = verify({"write_type": "insertion", "writer_family": "bridge_IS110", "writer_output_form": "DNA",
                "cargo_bp": 2000, "delivery_vehicle": "AAV_single", "cargo_seq": "ATCGCGATCGCG" * 30})
    fl = [f for f in v.scope_flags if f.get("kind") == "cargo_innate_sensing"]
    assert fl and fl[0]["cargo_form"] == "DNA"
    assert "known-unknown" in fl[0]["reason"].lower()
    assert v.no_fabrication is True
    # no cargo sequence -> no innate flag (the scorer is only invoked on a supplied sequence)
    v2 = verify({"write_type": "insertion", "delivery_vehicle": "AAV_single"})
    assert [f for f in v2.scope_flags if f.get("kind") == "cargo_innate_sensing"] == []


def test_provenance_curated_and_response_stays_known_unknown():
    assert citations_grounded(PROVENANCE_DOIS)["all_grounded"] is True
    cards = yaml.safe_load(resource("configs/oracles/scope_cards.yaml").read_text(encoding="utf-8"))["oracles"]
    nv = cards["innate_sensing"]["not_valid_for"].lower()
    assert "in-vivo" in nv and ("nucleoside modification" in nv or "pseudouridine" in nv)
