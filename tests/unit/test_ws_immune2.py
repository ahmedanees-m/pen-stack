"""v6.9 PEN-IMMUNE, CD4/MHC-II + ADA + writer-as-antigen (G-WS1..G-WS4).

CI-safe: the grounded MHC-II method is pure-Python and the writer/control sequences are committed (real UniProt).
Asserts the immunogenic-vs-tolerated recovery (foreign writers > human self), the never-collapsed profile, the
writer-as-antigen dominant-risk flag, and that the ADA axis stays an honest proxy (no manufactured ).
"""
from __future__ import annotations

from benchmarks.immuno.harness import ada_calibration, recovery
from pen_stack.planner.ada_risk import ada_risk
from pen_stack.planner.immune_mhc2 import mhc2_epitope_load, writer_sequences
from pen_stack.planner.immune_profile import immune_profile


# ---- G-WS1: REAL NetMHCIIpan-4.0 MHC-II + no production proxy ----------------------------------
def test_mhc2_real_cache_is_grounded_and_bounded():
    # v6.9.2: the production MHC-II axis is the REAL NetMHCIIpan-4.0 residue-coverage cache (by antigen name)
    seqs = writer_sequences()
    el = mhc2_epitope_load(seqs["SpCas9"]["seq"], "SpCas9")
    assert el["backend"] == "netmhciipan_cache"
    assert 0.0 < el["epitope_density"] < 1.0
    assert el["mhc2_immune_score"] == round(1.0 - el["epitope_density"], 4) # 1 = least presentable
    assert "NetMHCIIpan-4.0" in el["method"]


def test_mhc2_abstains_without_a_grounded_name_no_production_proxy():
    # v6.9.2 honesty: an uncached sequence (no name) is an HONEST KNOWN-UNKNOWN, it ABSTAINS, never a guessed
    # proxy number. The documented promiscuous-binder estimate remains available for OFFLINE triage ONLY.
    from pen_stack.planner.immune_mhc2 import mhc2_proxy_estimate
    s = writer_sequences()["SpCas9"]["seq"]
    el = mhc2_epitope_load(s)
    assert el["backend"] == "abstain" and el["epitope_density"] is None and el["mhc2_immune_score"] is None
    pe = mhc2_proxy_estimate(s)
    assert pe["backend"] == "proxy_offline_only" and 0.0 < pe["epitope_density"] < 1.0
    assert pe["n_promiscuous_binders"] > 0


def test_real_netmhciipan_cache_wired_and_discriminates():
    # the REAL NetMHCIIpan-4.0 cache (committed configs/mhc_epitope_oracle.yaml) is used by name
    from pen_stack.planner.immune_mhc2 import real_mhc2_load
    cas, alb = real_mhc2_load("SpCas9"), real_mhc2_load("HumanAlbumin")
    assert cas and alb and cas["backend"] == "netmhciipan_cache" and "NetMHCIIpan-4.0" in cas["method"]
    # the gold-standard tool shows the human SELF protein has a LOWER MHC-II epitope load than the foreign writer
    assert alb["epitope_density"] < cas["epitope_density"]
    s = writer_sequences()["SpCas9"]["seq"]
    assert mhc2_epitope_load(s, "SpCas9")["backend"] == "netmhciipan_cache"
    assert mhc2_epitope_load(s)["backend"] == "abstain" # v6.9.2: NO production proxy, abstains


def test_bundled_sequences_are_real_uniprot_with_origin():
    seqs = writer_sequences()
    assert {"SpCas9", "ISCro4", "Bxb1", "HumanAlbumin"} <= set(seqs)
    assert seqs["SpCas9"]["accession"] == "Q99ZW2" and seqs["SpCas9"]["origin"] == "foreign"
    assert seqs["HumanAlbumin"]["accession"] == "P02768" and seqs["HumanAlbumin"]["origin"] == "self"
    # writers are bacterial/phage (foreign); the human control is self
    assert all(seqs[w]["origin"] == "foreign" for w in ("SpCas9", "ISCro4", "Bxb1"))


# ---- G-WS2: ADA-risk (real MHC-II x origin-foreignness) + real self-match cross-check ----------
def test_ada_recovery_foreign_above_self():
    seqs = writer_sequences()
    # ADA-risk = real NetMHCIIpan-4.0 density x foreignness(origin); needs name (real cache) + origin (authoritative)
    foreign = [ada_risk(seqs[w]["seq"], "foreign", name=w)["ada_risk_score"] for w in ("SpCas9", "ISCro4", "Bxb1")]
    self_ = ada_risk(seqs["HumanAlbumin"]["seq"], "self", name="HumanAlbumin")["ada_risk_score"]
    assert all(f is not None and f > 0.0 for f in foreign) # foreign writers score
    assert self_ == 0.0 # self tolerated (x foreignness 0)
    assert min(foreign) > self_ # immunogenic > tolerated


def test_ada_abstains_when_origin_unknown_no_proxy():
    # v6.9.2: foreignness is the protein ORIGIN (authoritative central-tolerance signal). An UNKNOWN origin
    # ABSTAINS (no k-mer guess, no heuristic) rather than fabricating a foreignness.
    seqs = writer_sequences()
    r = ada_risk(seqs["SpCas9"]["seq"], origin=None, name="SpCas9")
    assert r["backend"] == "abstain" and r["ada_risk_score"] is None and r["ada_immune_score"] is None


def test_real_human_proteome_self_match_crosscheck():
    # the REAL human-proteome 9-mer self-match (computed on the VM over the full UniProt reference proteome) is
    # reported as a cross-check: the human control is self (1.0), foreign writers are non-self (0.0)
    from pen_stack.planner.ada_risk import real_self_match
    alb, cas = real_self_match("HumanAlbumin"), real_self_match("SpCas9")
    assert alb["human_9mer_match_fraction"] == 1.0 # albumin IS human
    assert cas["human_9mer_match_fraction"] == 0.0 # SpCas9 is bacterial (non-self)
    assert "proteome" in alb["reference"].lower()


# ---- G-WS3: never-collapsed profile + writer-as-antigen ---------------------------------------
def test_profile_has_mhc2_ada_axes_never_collapsed():
    p = immune_profile({"delivery_vehicle": "aav_single", "writer_family": "Cas9"})
    assert p["collapsed_score"] is None
    assert p["axes"]["mhc2_writer"]["value"] is not None
    assert p["axes"]["ada_writer"]["value"] is not None
    assert "proxy" in p["axes"]["mhc2_writer"]["validation"].lower() # honest label travels
    assert p["writer_as_antigen"]["is_foreign"] is True


def test_writer_dominant_risk_on_nonviral_delivery():
    # non-viral delivery of a bacterial bridge recombinase: the WRITER is the dominant antigen (no capsid)
    p = immune_profile({"delivery_vehicle": "lnp_mrna", "writer_family": "bridge_IS110"})
    assert p["writer_as_antigen"]["writer_dominant_risk"] is True
    assert p["writer_as_antigen"]["dominant_antigen"] == "writer"
    # no writer -> the axes abstain (value None), never fabricate
    assert immune_profile({"delivery_vehicle": "aav_single"})["axes"]["mhc2_writer"]["value"] is None


# ---- G-WS4: bench recovery + honest ADA calibration -------------------------------------------
def test_immuno_bench_recovery_and_calibration_is_honest():
    assert recovery()["immunogenic_above_tolerated"] is True
    # the ADA axis stays a proxy at public-data power, no manufactured
    assert ada_calibration()["status"] == "mechanistic_proxy"
