"""v6.11 PEN-DELIVER, cross-modality deliverability + learned capsid-fitness + serotype tropism priors (D-WS1..5).

CI-safe: the FLIP-AAV data stays on the VM; the trained model (~3 MB) + derived bench metrics + the approved-therapy
serotype registry ship. Asserts: the learned capsid-fitness beats the mutation-burden baseline on held-out FLIP-AAV
(D-G1); serotype->tissue priors are grounded for approved serotypes and a known-unknown for novel capsids; the
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


# ---- D-WS2: learned capsid-fitness beats the baseline (D-G1) ------------------------------------
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


def test_capsid_fitness_model_scores_or_abstains_honestly():
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


# ---- D-WS1: serotype -> tissue tropism priors (grounded / known-unknown) ------------------------
def test_serotype_tropism_grounded_and_distinguishes_rh74_variants():
    assert serotype_tropism("AAV5")["tissue"] == ["liver"] # Hemgenix/Roctavian
    # the critical distinction: AAVrh74 -> muscle, AAVRh74var -> liver (different capsids)
    assert "skeletal_muscle" in serotype_tropism("AAVrh74")["tissue"]
    assert serotype_tropism("AAVRh74var")["tissue"] == ["liver"]
    # a novel/engineered capsid with no approved precedent -> known-unknown, NOT a fabricated tissue
    nov = serotype_tropism("AAV_novel_xyz")
    assert nov["confidence"] == "known-unknown" and nov["tissue"] is None
    # tissue -> grounded serotypes
    assert {s["serotype"] for s in serotypes_for_tissue("liver")["grounded_serotypes"]} >= {"AAV5", "AAVRh74var"}
    assert serotypes_for_tissue("pancreas")["grounded_serotypes"] == [] # no approved prior -> abstains


def test_tropism_provenance_dois_grounded():
    import yaml

    from pen_stack._resources import resource
    trop = yaml.safe_load(resource("configs/aav_serotype_tropism.yaml").read_text(encoding="utf-8"))
    assert citations_grounded(trop["provenance_dois"])["all_grounded"] is True


# ---- D-WS4: immune-coupled selection, tradeoff surfaced, never collapsed -----------------------
def test_recommender_and_immune_tradeoff_never_collapsed():
    rec = recommend_delivery_plus("DNA", cargo_bp=4000, target_tissue="liver")
    assert rec["target_tissue"] == "liver" and rec["serotype_tropism_prior"]["grounded_serotypes"]
    tr = delivery_immune_tradeoff("DNA", cargo_bp=4000, target_tissue="liver", writer_family="Cas9")
    assert tr["collapsed_score"] is None and tr["no_fabrication"] is True # dose<->immune is a vector
    assert "in_vivo_immunogenicity_magnitude" in tr["known_unknowns"]


# ---- D-WS3: generative capsid candidates, verify-gated --------------------------------------
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
