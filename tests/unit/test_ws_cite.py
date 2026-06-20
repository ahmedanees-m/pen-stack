"""WS-CITE + WS-GEN unit tests (Phase 5.0) - cited mechanistic rationale (citations resolve by construction)
+ scoped generalisation (grounded-or-refused). CI-safe (citations checked against the curated world-model)."""
from __future__ import annotations

from pen_stack.agent.cite import (
    cited_rationale,
    citations_grounded,
    curated_dois,
    generalise,
)


def test_rationale_cites_real_world_model_sources_and_is_grounded():
    cr = cited_rationale({"write_type": "insertion", "writer_family": "bridge_IS110", "cargo_bp": 3000,
                          "delivery_vehicle": "AAV_single", "safety": 0.8, "p_durable": 0.7,
                          "writer_activity": 0.7})
    assert cr["n_citations"] >= 1 and cr["citations_grounded"] is True
    assert cr["no_fabrication"] is True
    # every cited DOI is in the curated, already-verified set
    for c in cr["citations"]:
        assert c["doi"] in curated_dois()


def test_hallucinated_citation_guard_rejects_a_fabricated_doi():
    g = citations_grounded(["10.9999/fabricated.not.real.000"])
    assert g["all_grounded"] is False and g["ungrounded"] == ["10.9999/fabricated.not.real.000"]
    # a real curated DOI passes
    real = next(iter(curated_dois()))
    assert citations_grounded([real])["all_grounded"] is True


def test_generalisation_answers_grounded_task():
    r = generalise("delivery_selection", {"write_type": "insertion", "writer_family": "Cas9",
                                          "cargo_bp": 1000, "delivery_vehicle": "AAV_single"})
    assert r["grounded"] is True and r["refused"] is False
    assert r["verdict"]["legal"] is False # Cas9 RNP into DNA-only AAV -> illegal, grounded
    assert r["no_fabrication"] is True


def test_generalisation_refuses_ungrounded_task():
    r = generalise("design_a_metabolic_pathway_de_novo")
    assert r["refused"] is True and r["grounded"] is False
    assert "refused" in r["scope_statement"].lower() and r["no_fabrication"] is True
