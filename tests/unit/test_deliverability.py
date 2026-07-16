"""Cross-modality deliverability + learned capsid-fitness + serotype tropism priors.

CI-safe: the FLIP-AAV data stays on the VM; the trained model (~3 MB) + derived bench metrics + the approved-therapy
serotype registry ship. Asserts: the learned capsid-fitness beats the mutation-burden baseline on held-out FLIP-AAV;
serotype->tissue priors are grounded for approved serotypes and a known-unknown for novel capsids; the
dose<->immune tradeoff is surfaced and NEVER collapsed; generative capsids are verify-gated candidates; no fabrication.
"""
from __future__ import annotations

from pen_stack.agent.cite import citations_grounded
from pen_stack.planner.delivery_immune import delivery_immune_tradeoff
from pen_stack.planner.delivery_predict import (
    capsid_fitness,
    recommend_delivery_plus,
    serotype_tropism,
    serotypes_for_tissue,
)


# ---- Learned capsid-fitness beats the baseline ------------------------------------
def test_capsid_fitness_bench_beats_baseline():
    from benchmarks.delivery.harness import run
    r = run()
    assert r["available"] is True
    for split in ("sampled", "mut_des"):
        s = r["splits"][split]
        assert s["learned_beats_baseline"] is True
        assert s["learned_spearman"] > s["baseline_spearman"]
        assert s["gap_ci95"][0] > 0 # bootstrap CI on the learned-minus-baseline gap excludes 0
    assert r["learned_beats_baseline"] is True


def test_capsid_fitness_model_scores_or_abstains():
    # the shipped model scores a VP1 sequence as a CANDIDATE (measured packaging axis), or abstains if absent
    wt = ("MAADGYLPDWLEDTLSEGIRQWWKLKPGPPPPKPAERHKDDSRGLVLPGYKYLGPFNGLDKGEPVNEADAAALEHDKAYDRQLDSGDNPYLKYNHADAEF"
          "QERLKEDTSFGGNLGRAVFQAKKRVLEPLGLVEEPVKTAPGKKRPVEHSPVEPDSSSGTGKAGQQPARKRLNFGQTGDADSVPDPQPLGQPPAAPSGLGT"
          "NTMATGSGAPMADNNEGADGVGNSSGNWHCDSTWMGDRVITTSTRTWALPTYNNHLYKQISSQSGASNDNHYFGYSTPWGYFDFNRFHCHFSPRDWQRLIN"
          "NNWGFRPKRLNFKLFNIQVKEVTQNDGTTTIANNLTSTVQVFTDSEYQLPYVLGSAHQGCLPPFPADVFMVPQYGYLTLNNGSQAVGRSSFYCLEYFPSQM"
          "LRTGNNFTFSYTFEDVPFHSSYAHSQSLDRLMNPLIDQYLYYLSRTNTPSGTTTQSRLQFSQAGASDIRDQSRNWLPGPCYRQQRVSKTSADNNNSEYSWT"
          "GATKYHLNGRDSLVNPGPAMASHKDDEEKFFPQSGVLIFGKQGSEKTNVDIEKVMITDEEEIRTTNPVATEQYGSVSTNLQRGNRQAATADVNTQGVLPGM"
          "VWQDRDVYLQGPIWAKIPHTDGHFHPSPLMGGFGLKHPPPQILIKNTPVPANPSTTFSAAKFASFITQYSTGQVSVEIEWELQKENSKRWNPEIQYTSNYN"
          "KSVNVDFTVDTNGVYSEPRPIGTRYLTRNL")
    r = capsid_fitness(wt)
    assert r["output_kind"] == "candidate"
    if r["available"]:
        assert isinstance(r["predicted_fitness"], float) and "in-vivo" in r["status"].lower()
    else:
        assert r["abstain"] is True


def test_capsid_fitness_abstains_for_non_aav_vectors():
    # the learned model is AAV-capsid-specific: other vectors (LV / adenovirus / HSV) have NO packaging-fitness
    # model, so it abstains WITH that stated, never fabricating a score for a vector it was never trained on.
    for vec in ("Lentivirus", "Adenovirus", "HSV"):
        r = capsid_fitness("MAADGYLPDWLEDNLSEG", vector=vec)
        assert r["available"] is False and r["abstain"] is True and r["predicted_fitness"] is None
        assert vec.lower() in r["note"].lower() and "not fabricat" in r["note"].lower()


def test_capsid_fitness_input_guard():
    # the model reads AAV VP1 residues 555-595 ONLY; a too-short or nucleotide input must ABSTAIN (not return the
    # degenerate constant), a partial-window input scores WITH a warning, and a full VP1 scores clean. The guard
    # only runs once the model is loaded, so skip where the .pkl is absent (CI / bare wheel).
    import pytest

    from pen_stack.planner.delivery_predict import _fitness_model
    if _fitness_model() is None:
        pytest.skip("capsid_fitness model absent; the input guard runs only after the model loads")
    short = capsid_fitness("MAADGYLPDW")                 # 10 aa: never reaches the 555-595 window
    assert short["available"] is False and short["predicted_fitness"] is None and "input_issue" in short
    nuc = capsid_fitness("ACGT" * 200)                   # 800 nt of pure ACGT -> a nucleotide sequence, not a protein
    assert nuc["available"] is False and "nucleotide" in nuc["input_issue"].lower()
    full = capsid_fitness("M" + "A" * 600)               # >= 595 aa -> scores clean, no warning
    assert full["available"] is True and full["input_warning"] is None
    part = capsid_fitness("M" + "A" * 579)               # 580 aa: 555 < len < 595 -> scores WITH a padded-tail warning
    assert part["available"] is True and part["input_warning"] and "padded" in part["input_warning"]


def test_capsid_fitness_reports_percentile_and_verdict():
    # usability: a raw log-enrichment float is hard to read, so a scored result carries a PERCENTILE among the
    # model's held-out FLIP-AAV predictions + a plain-language verdict bucket, for the UI to lead with.
    import pytest

    from pen_stack.planner.delivery_predict import _fitness_model
    m = _fitness_model()
    if m is None or not m.get("pred_percentiles"):
        pytest.skip("capsid_fitness model / percentile reference absent (pre-percentile model build)")
    r = capsid_fitness("M" + "A" * 610)
    assert r["available"] and r["percentile"] is not None and 0 <= r["percentile"] <= 100
    assert r["verdict"] and r["verdict_bucket"] in {"better", "similar", "worse"}
    exp = "better" if r["percentile"] >= 67 else ("similar" if r["percentile"] >= 33 else "worse")
    assert r["verdict_bucket"] == exp  # bucket consistent with the percentile thresholds
    # a compact reference histogram for the UI sparkline: 24 bins over [lo, hi]
    assert r["distribution"] and len(r["distribution"]["counts"]) == 24 and r["distribution"]["hi"] > r["distribution"]["lo"]


# ---- Serotype -> tissue tropism priors (grounded / known-unknown) ------------------------
def test_serotype_tropism_grounded_and_distinguishes_rh74_variants():
    assert serotype_tropism("AAV5")["tissue"] == ["liver"] # Hemgenix/Roctavian
    # the critical distinction: AAVrh74 -> muscle, AAVRh74var -> liver (different capsids)
    assert "skeletal_muscle" in serotype_tropism("AAVrh74")["tissue"]
    assert serotype_tropism("AAVRh74var")["tissue"] == ["liver"]
    # a novel/engineered capsid with no approved precedent -> known-unknown, NOT a fabricated tissue
    nov = serotype_tropism("AAV_novel_xyz")
    assert nov["confidence"] == "known-unknown" and nov["tissue"] is None
    # the grounded prior surfaces its provenance (approved product + a DOI) so the UI can cite it
    aav9 = serotype_tropism("AAV9")
    assert "CNS" in aav9["tissue"] and aav9["doi"] and aav9["indication"] and "Zolgensma" in aav9["evidence"]


def test_delivery_tropism_endpoint_is_bidirectional():
    # the /delivery/tropism endpoint answers BOTH directions: serotype -> tissue, and target_tissue -> serotypes.
    import pytest
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from pen_stack.server.api import app
    c = TestClient(app)
    s = c.get("/delivery/tropism", params={"serotype": "AAV5"}).json()
    assert s["tissue"] == ["liver"] and s["doi"]
    t = c.get("/delivery/tropism", params={"target_tissue": "muscle"}).json()
    assert any(g["serotype"] == "AAVrh74" for g in t["grounded_serotypes"])
    assert c.get("/delivery/tropism").status_code == 422  # neither param -> 422, not a silent empty answer
    # tissue -> grounded serotypes
    assert {s["serotype"] for s in serotypes_for_tissue("liver")["grounded_serotypes"]} >= {"AAV5", "AAVRh74var"}
    assert serotypes_for_tissue("pancreas")["grounded_serotypes"] == [] # no approved prior -> abstains


def test_recommender_surfaces_serotype_tropism_prior_for_a_serotype():
    # Bug 3 regression: recommend_delivery_plus must populate serotype_tropism_prior from a passed ``serotype``
    # (AAV9 -> CNS/Zolgensma), not only from a target_tissue. It was always null before.
    from pen_stack.planner.delivery_predict import recommend_delivery_plus
    r = recommend_delivery_plus("AAV", 4000, serotype="AAV9")
    prior = r["serotype_tropism_prior"]
    assert prior and prior["serotype"] == "AAV9" and "CNS" in prior["tissue"]
    assert prior["confidence"] == "grounded (approved therapy)"
    # a novel capsid -> known-unknown, never fabricated; no serotype/tissue -> None
    assert recommend_delivery_plus("AAV", 4000, serotype="AAV_novel_xyz")["serotype_tropism_prior"]["confidence"] == "known-unknown"
    assert recommend_delivery_plus("AAV", 4000)["serotype_tropism_prior"] is None


def test_tropism_provenance_dois_grounded():
    import yaml

    from pen_stack._resources import resource
    trop = yaml.safe_load(resource("configs/aav_serotype_tropism.yaml").read_text(encoding="utf-8"))
    assert citations_grounded(trop["provenance_dois"])["all_grounded"] is True


# ---- Immune-coupled selection, tradeoff surfaced, never collapsed -----------------------
def test_recommender_and_immune_tradeoff_never_collapsed():
    rec = recommend_delivery_plus("DNA", cargo_bp=4000, target_tissue="liver")
    assert rec["target_tissue"] == "liver" and rec["serotype_tropism_prior"]["grounded_serotypes"]
    tr = delivery_immune_tradeoff("DNA", cargo_bp=4000, target_tissue="liver", writer_family="Cas9")
    assert tr["collapsed_score"] is None and tr["no_fabrication"] is True # dose<->immune is a vector
    assert "in_vivo_immunogenicity_magnitude" in tr["known_unknowns"]


# ---- Generative capsid candidates, verify-gated --------------------------------------
def test_generative_capsids_are_candidates_or_abstain():
    from pen_stack.design.capsid_generate import generate_capsid_candidates
    wt = "M" + "A" * 560 + "GSGAPMADNNEGADGVGNSSGNWHCDSTWMGDRVITT" + "A" * 200 # synthetic VP1-length scaffold
    g = generate_capsid_candidates(wt, n=40, max_mut=3)
    assert g["output_kind"] == "candidate"
    if g["available"]:
        assert all(c["output_kind"] == "candidate" for c in g["candidates"])
        assert "not claimed" in g["honesty"].lower() or "candidate" in g["honesty"].lower()
    else:
        assert g["abstain"] is True


def test_capsid_generate_endpoint_enforces_fitness_gate():
    # Endpoint: POST /capsid/generate proposes VP1 555-595 variants and keeps ONLY survivors with
    # fitness >= WT (verifier-as-discriminator); each survivor is a labelled candidate; abstains without the model.
    import pytest
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from pen_stack.planner.delivery_predict import _fitness_model
    from pen_stack.server.api import app
    c = TestClient(app)
    r = c.post("/capsid/generate", json={"wt_vp1": "M" + "A" * 610, "n": 40, "max_mut": 3, "top": 10}).json()
    assert r["output_kind"] == "candidate"
    if _fitness_model() is not None:
        assert r["available"] is True and r["n_survivors"] <= 10
        assert all(cand["predicted_fitness"] >= r["fitness_threshold"] for cand in r["candidates"])
        assert all(cand["output_kind"] == "candidate" for cand in r["candidates"])
    else:
        assert r["abstain"] is True
