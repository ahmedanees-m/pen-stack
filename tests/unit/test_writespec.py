"""The typed WriteRequest, grounded resolvers + extractor,
feasibility check, and the WriteSpec-Bench gates."""
from __future__ import annotations

import pytest

from pen_stack.spec import CargoComponent, Resolved, Target, WriteRequest
from pen_stack.spec.extract import extract_writespec
from pen_stack.spec.resolvers import (
    resolve_cell,
    resolve_chem,
    resolve_feature,
    resolve_gene,
    resolve_locus,
    resolve_phenotype,
)
from pen_stack.spec.satisfy import check_satisfiable
from pen_stack.spec.service import parse_request


def _example() -> WriteRequest:
    return WriteRequest(
        write_type="insertion",
        cargo=[CargoComponent(name="GFP", role=Resolved(text="CDS", id="SO:0000316", ontology="SO"),
                              sequence="ATGGTGAGC", length_bp=720)],
        target=Target(kind="gene", gene=Resolved(text="AAVS1", id="PPP1R12C", ontology="HGNC")),
        cell_type=Resolved(text="HEK293T", id="CVCL_0063", ontology="Cellosaurus"),
    )


def test_json_round_trip_lossless():
    wr = _example()
    assert WriteRequest.from_json(wr.to_json()) == wr


def test_ontology_validation_flags_bad_ids():
    wr = _example()
    assert wr.ontology_validation()["all_valid"] is True
    wr.cell_type = Resolved(text="x", id="not-a-cvcl", ontology="Cellosaurus")
    v = wr.ontology_validation()
    assert v["all_valid"] is False and any(b["field"] == "cell_type" for b in v["invalid"])


def test_legacy_design_adapter():
    d = _example().to_legacy_design()
    assert d["write_type"] == "insertion" and d["gene"] == "PPP1R12C" and d["cell_type"] == "CVCL_0063"


def test_genbank_export_only_with_sequence():
    pytest.importorskip("Bio")  # GenBank export uses Biopython (the [bio] extra)
    assert "LOCUS" in (_example().to_genbank() or "")
    intent_only = WriteRequest(write_type="excision", target=Target(kind="gene", gene=Resolved(id="CCR5", ontology="HGNC")))
    assert intent_only.to_genbank() is None


def test_sbol3_round_trip_when_installed():
    sbol3 = pytest.importorskip("sbol3")  # the [spec] extra
    assert sbol3 is not None
    wr = _example()
    assert WriteRequest.from_sbol3(wr.to_sbol3()) == wr


def test_resolvers_ground_or_abstain():
    assert resolve_gene("AAVS1").id == "PPP1R12C"
    assert resolve_gene("the").id is None          # jargon / stop token: unresolved, not invented
    assert resolve_cell("HEK293T").id == "CVCL_0063"
    assert resolve_cell("zog cells").id is None
    assert resolve_feature("promoter").id == "SO:0000167"
    assert resolve_phenotype("sickle cell").id == "MONDO:0011382"
    assert resolve_chem("doxycycline").id == "CHEBI:50845"
    # locus resolution is atlas-gated: it returns the GRCh38 region when the writable-genome atlas is present
    # (VM/local), and abstains (id None) when it is absent (CI does not ship the atlas) - never invented
    loc = resolve_locus("CFTR")
    assert loc.ontology == "GRCh38"
    assert loc.id is None or loc.id.startswith("chr7:")


def test_extractor_labels_inferred_and_never_fabricates():
    s = extract_writespec("I want to edit some cells")
    assert s.provenance["write_type"] == "inferred"           # the only defaulted field, labelled
    assert s.assumptions                                       # with a rationale
    assert s.target.kind == "unspecified" and s.clarifications  # asks rather than guesses
    # a fully specified request resolves with no clarification and no unresolved term
    s2 = extract_writespec("Knock out CCR5 in primary T cells")
    assert s2.write_type == "excision" and s2.target.gene.id == "CCR5"
    assert s2.cell_type.id == "CL:0000084" and not s2.clarifications and not s2.unresolved


def test_target_is_the_edit_site_not_a_gene_like_cargo():
    """A gene-like cargo token (CD19, FOXP3) must not hijack the target: the edit SITE is the one anchored by a
    site preposition ('into/at X') or a 'X locus' suffix. Regression for the brief-input under-parse."""
    a = extract_writespec("integrate a CD19 CAR into TRAC of primary T cells")
    assert a.target.kind == "gene" and a.target.gene.id == "TRAC"
    b = extract_writespec("insert FOXP3 into AAVS1 in HEK293T")
    assert b.target.gene.id == "PPP1R12C"            # AAVS1 nickname resolves; FOXP3 (cargo) does not win
    c = extract_writespec("knock in a CD19 CAR at the TRAC locus of CD8 T cells")
    assert c.target.gene.id == "TRAC"
    # a bare target with no site preposition still resolves via the first-token fallback
    d = extract_writespec("knock out PCSK9")
    assert d.target.gene.id == "PCSK9"


def test_satisfiability_feasible_and_infeasible():
    feasible = check_satisfiable(extract_writespec("Insert a 3 kb cassette at AAVS1 in HEK293T"))
    assert feasible.feasible is True
    infeasible = check_satisfiable(extract_writespec("Insert an 8 kb cassette at AAVS1 in HEK293T using a single AAV"))
    assert infeasible.feasible is False
    assert any(b["constraint"] == "legality" for b in infeasible.blocking)
    assert infeasible.repairs  # a repair hint is offered


def test_parse_request_service():
    out = parse_request("Knock out CCR5 in primary T cells")
    assert out["actionable"] is True and out["no_fabrication"] is True
    assert out["writespec"]["target"]["gene"]["id"] == "CCR5"
    assert out["feasibility"]["feasible"] in (True, False)


def test_writespec_bench_gates_pass():
    from benchmarks.writespec.harness import run
    r = run()
    assert r["all_gates_pass"] is True
    assert r["test_sealed"]["structural_fidelity"] >= 0.8
    assert r["beats_baseline_on_test"] is True
    assert r["inferred_field_labelling_recall"] == 1.0


def _limit(text: str):
    from pen_stack.spec.service import parse_request
    ws = parse_request(text)["writespec"]
    return (ws.get("constraints") or {}).get("delivery_limit")


def test_locus_name_does_not_read_as_a_delivery_vehicle():
    # AAVS1 is the standard safe harbour: its name merely STARTS with the letters of a vehicle. A substring match
    # would attach an unstated AAV_single limit (~4.7 kb) and wrongly call a 6 kb lentiviral design over-capacity,
    # while labelling the invented constraint as user-stated. The vehicle must be read as a whole word.
    assert _limit("Insert a 6 kb transgene into the AAVS1 locus in K562") is None
    assert _limit("Integrate at AAVS1 safe harbour.") is None
    assert _limit("Insert a 6 kb transgene into the CCR5 locus in K562") is None       # control
    # a locus whose name collides must not shadow the vehicle the user DID name
    assert _limit("Insert at AAVS1 using lentivirus") == "lentivirus"
    assert _limit("Knock in at AAVS1 by RNP electroporation") == "electroporation"


def test_named_delivery_vehicles_and_serotypes_still_resolve():
    # the word-boundary match must not cost real detections, including serotype suffixes
    assert _limit("Insert a 2 kb transgene into CCR5 delivered via AAV") == "AAV_single"
    assert _limit("Deliver a 4 kb cassette with AAV9 to CNS") == "AAV_single"
    assert _limit("Deliver with AAVrh74 to skeletal muscle") == "AAV_single"
    assert _limit("Package into scAAV") == "AAV_single"
    assert _limit("Deliver via AAV-PHP.eB to CNS") == "AAV_single"
    assert _limit("Deliver via AAV-DJ") == "AAV_single"
    assert _limit("Use dual AAV for a 7 kb cargo") == "AAV_dual"


def test_recombinant_aav_is_a_vehicle():
    # rAAV is the dominant spelling in the gene-therapy literature. Dropping it fails OPEN: with no vehicle on the
    # design the packaging-capacity rule reports not_applicable, so an over-capacity cargo is passed in silence.
    for prose in ("Deliver a 6000 bp factor VIII cassette to hepatocytes using rAAV9.", "Deliver via rAAV.",
                  "rAAV2/8 to liver.", "Deliver by rAAVrh74 to muscle.", "scrAAV delivery."):
        assert _limit(prose) == "AAV_single", prose


def test_dual_aav_is_not_downgraded_by_a_serotype_number():
    # a serotype suffix belongs to the AAV token, so it must not push a stated dual-vector strategy (~9 kb across
    # two capsids) down to the single-capsid limit (~4.7 kb)
    assert _limit("Use a dual AAV9 strategy for a 7 kb cargo") == "AAV_dual"
    assert _limit("dual AAV8 vector") == "AAV_dual"
    assert _limit("Use dual rAAV9 for a 7 kb cargo") == "AAV_dual"
    assert _limit("dual-AAV approach") == "AAV_dual"


def test_plural_and_spelled_out_vehicles_resolve():
    assert _limit("Two AAVs will carry the split cargo.") == "AAV_single"
    assert _limit("Cas9 RNPs into T cells.") == "electroporation"
    assert _limit("Deliver with LNPs.") == "LNP"
    assert _limit("Deliver via adeno-associated virus vector to retina.") == "AAV_single"


def test_a_vehicle_named_to_be_ruled_out_is_not_the_chosen_vehicle():
    """A vehicle read from the table's order rather than from the prose records the one the user REJECTED, and
    labels the invented constraint as user-stated. The cue next to the mention decides."""
    assert _limit("AAV is too small for this 9 kb cargo, so we will use lentivirus instead.") == "lentivirus"
    assert _limit("We rule out AAV and will use LNP.") == "LNP"
    assert _limit("Deliver with AAV9, not lentivirus.") == "AAV_single"
    assert _limit("Package without AAV; use lentivirus.") == "lentivirus"
    assert _limit("Use AAV rather than lentivirus.") == "AAV_single"
    assert _limit("use lentivirus instead of AAV") == "lentivirus"
    assert _limit("We ruled out AAV, so use lentivirus") == "lentivirus"
    assert _limit("Do not use AAV; deliver with lentivirus") == "lentivirus"


def test_a_negation_only_rules_out_the_vehicle_it_governs():
    """A cue counts only inside the mention's own clause and only when it reaches the vehicle directly. Searching
    the preceding characters for a bare 'not' rules out vehicles the request actually chose."""
    # the negation belongs to another clause
    assert _limit("A cassette that does not integrate, delivered by AAV9") == "AAV_single"
    assert _limit("It is not clear yet; use AAV") == "AAV_single"
    assert _limit("This does not matter: use AAV9") == "AAV_single"
    assert _limit("The cargo is not large, so package into AAV") == "AAV_single"
    # the negation governs a different word ("not only"), not the vehicle, so AAV is not ruled out: the request
    # names two vehicles and is asked about rather than resolved to the survivor of a false rejection
    both = extract_writespec("Use not only AAV but also lentivirus")
    assert both.constraints.delivery_limit is None
    assert any("more than one delivery vehicle" in c for c in both.clarifications)


def test_two_vehicles_with_no_cue_are_asked_about_not_guessed():
    s = extract_writespec("Deliver using AAV or lentivirus.")
    assert s.constraints.delivery_limit is None                       # neither is recorded as though stated
    assert s.provenance.get("constraints.delivery_limit") is None
    assert any("more than one delivery vehicle" in c for c in s.clarifications)
    # every named vehicle ruled out, none put in its place
    ruled = extract_writespec("AAV is too small for this 9 kb cargo.")
    assert ruled.constraints.delivery_limit is None
    assert any("ruled out" in c for c in ruled.clarifications)


def test_electroporation_alongside_a_capsid_is_not_an_ambiguous_choice():
    """The standard ex vivo knock-in names both: the pulse delivers the nuclease, the capsid carries the donor.
    Reading them as rival vehicles and abstaining would drop the donor's packaging-capacity check, which is the
    one constraint that matters here, on the most common protocol there is."""
    for prose in ("Deliver Cas9 RNP by electroporation with an AAV6 donor template",
                  "Electroporate Cas9 RNP and supply a 4 kb AAV6 donor"):
        s = extract_writespec(prose)
        assert s.constraints.delivery_limit == "AAV_single", prose
        assert not any("more than one delivery vehicle" in c for c in s.clarifications), prose
    # electroporation on its own is still the vehicle
    assert _limit("Knock in at AAVS1 by RNP electroporation") == "electroporation"
    # two capsids remain a genuine choice
    assert _limit("Deliver using AAV or lentivirus.") is None


def test_a_vehicle_written_in_capitals_is_not_a_gene_target():
    """A vehicle name in capitals has the shape of a gene symbol. It must not be read as the edit site."""
    for prose in ("Deliver with LENTIVIRUS", "Package the 4 kb cassette into ADENOVIRUS"):
        assert extract_writespec(prose).target.gene is None, prose
    # the vehicle itself still resolves, and a real target alongside it is unaffected
    assert _limit("Deliver with LENTIVIRUS") == "lentivirus"
    assert extract_writespec("Knock out CCR5 using LENTIVIRUS in K562").target.gene.id == "CCR5"
    # a capsid named as the donor is not the target gene either
    assert extract_writespec("Deliver Cas9 RNP by electroporation with an AAV6 donor").target.gene is None


def test_every_named_target_is_kept_not_just_the_first():
    a = extract_writespec("multiplex knockout of TRAC and B2M in CD8 T cells")
    assert a.write_type == "multiplex"                                 # the stated modality wins over the verb
    assert a.target.gene.id == "TRAC"                                  # a cell marker is not the edit site
    assert [g.id for g in a.target.additional_genes] == ["B2M"]
    b = extract_writespec("Knock out TRAC, B2M and CIITA in primary T cells")
    assert [g.id for g in b.target.additional_genes] == ["B2M", "CIITA"]
    assert any("target genes" in c for c in b.clarifications)          # 3 targets, one excision verb: ask
    # a gene-like CARGO name is not a second target
    c = extract_writespec("integrate a CD19 CAR into TRAC of primary T cells")
    assert c.target.gene.id == "TRAC" and not c.target.additional_genes


def test_two_cell_types_are_asked_about_not_committed_to():
    s = extract_writespec("Knock out CCR5 in HeLa or Jurkat")
    assert s.cell_type is None                                         # neither is recorded as though stated
    assert any("more than one cell type" in c for c in s.clarifications)
    # a cell term that CONTAINS another ('CD8 T cells' contains 'T cells') is one cell, not two
    assert extract_writespec("Knock out CCR5 in CD8 T cells").cell_type.id == "CL:0000084"
    assert extract_writespec("Insert a 3 kb cassette at AAVS1 in HEK293T").cell_type.id == "CVCL_0063"
    # ... and a real choice still asks even when both terms carry the suffix
    assert extract_writespec("Knock out CCR5 in HeLa or Jurkat cells").cell_type is None


def test_a_cell_line_named_with_its_suffix_is_one_cell_type():
    """Cell terms OVERLAP without nesting: in 'HEK293T cells' the line's trailing t is also the t of 't cell', and
    in 'Jurkat cells' likewise. Counting both would report two different cell types for one named line and abstain
    on a request that was never ambiguous."""
    for prose, expected in (("Insert a 3 kb cassette at AAVS1 in HEK293T cells", "CVCL_0063"),
                            ("Knock out CCR5 in Jurkat cells", "CVCL_0065"),
                            ("Knock out CCR5 in K562 cells", "CVCL_0004"),
                            ("Insert at AAVS1 in HepG2 cells", "CVCL_0027"),
                            ("Knock out CCR5 in HeLa cells", "CVCL_0030"),
                            ("Generate CAR-T cells targeting CD19", "CL:0000084")):
        s = extract_writespec(prose)
        assert s.cell_type is not None and s.cell_type.id == expected, prose
        assert not any("more than one cell type" in c for c in s.clarifications), prose


def test_a_symbol_the_atlas_cannot_confirm_says_so():
    """The pass-through for an unknown-but-plausible symbol is deliberate (a novel gene must still work), so it is
    surfaced rather than left to look grounded, and it no longer depends on the symbol's length."""
    s = extract_writespec("Knock out ZZQXW9")
    assert s.target.gene.id == "ZZQXW9" and s.target.gene.confidence < 0.5
    assert any("could not be confirmed" in c for c in s.clarifications)
    assert any("unvalidated" in a for a in s.assumptions)
    # a real symbol longer than the old bound is now seen at all, and is not flagged
    long_real = extract_writespec("Knock out ARHGEF10L")
    assert long_real.target.gene.id == "ARHGEF10L"
    assert not any("could not be confirmed" in c for c in long_real.clarifications)
