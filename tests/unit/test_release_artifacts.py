"""Release meta-tests: the release artifacts are present, consistent, and their gates pass."""
from __future__ import annotations

from pathlib import Path

import pen_stack

_ROOT = Path(__file__).resolve().parents[2]


def test_version_consistent_across_release_artifacts():
    assert pen_stack.__version__ == "0.1.0"
    assert 'version = "0.1.0"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "version: 0.1.0" in (_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert 'org.opencontainers.image.version="0.1.0"' in (_ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_api_stability_commitment():
    # the committed public API: Production/Stable classifier + a documented stability / deprecation policy
    pp = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "Development Status :: 5 - Production/Stable" in pp
    assert (_ROOT / "docs/STABILITY.md").exists()


def test_env_extra_declared():
    pp = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "gymnasium" in pp and "env = [" in pp


def test_grounded_chat_routing_and_safety():
    # the grounded conversational chat system and its evaluation suite
    from pen_stack.rag.ground import ground_general  # noqa: F401
    from pen_stack.web.llm_provider import providers  # noqa: F401
    from benchmarks.chat_routing.harness import run as routing_run
    from benchmarks.chat_safety.harness import run as safety_run
    assert routing_run()["routing_safety_metric"] <= 0.001  # no write request leaks to general
    assert safety_run()["false_grounding_rate"] == 0.0       # no general fact mislabelled as a PEN-STACK result


def test_closed_loop_and_cloudlab():
    # the closed loop: cloud-lab connector + SDL-brain benchmark + validation campaign
    from pen_stack.active.brains import benchmark  # noqa: F401
    from pen_stack.active.campaign import design_campaign  # noqa: F401
    from pen_stack.build.cloudlab import submit_gated  # noqa: F401
    from benchmarks.loop.harness import run
    r = run()
    assert r["all_gates_pass"] is True
    assert r["cloudlab_biosecurity"]["hazard_blocked"] is True  # the biosecurity gate blocks a flagged export
    for p in ("pen_stack/build/cloudlab.py", "pen_stack/active/brains.py", "pen_stack/active/campaign.py",
              "benchmarks/loop/harness.py", "benchmarks/loop/loop_bench_metrics.json",
              "benchmarks/loop/SHA256SUMS", "docs/closed_loop.md",
              "prereg/ws_closedloop.yaml", "prereg/SHA256_LOCK_ws_closedloop.json"):
        assert (_ROOT / p).exists(), p


def test_writespec_layer():
    # WriteSpec: typed SBOL3-profile intent layer + grounded extractor + bench + SAT
    from pen_stack.spec import WriteRequest  # noqa: F401
    from pen_stack.spec.extract import extract_writespec  # noqa: F401
    from pen_stack.spec.satisfy import check_satisfiable  # noqa: F401
    from pen_stack.spec.service import parse_request  # noqa: F401
    from benchmarks.writespec.harness import run
    assert run()["all_gates_pass"] is True
    for p in ("pen_stack/spec/writespec.py", "pen_stack/spec/extract.py", "pen_stack/spec/clarify.py",
              "pen_stack/spec/satisfy.py", "pen_stack/spec/service.py",
              "pen_stack/spec/resolvers/gene.py", "pen_stack/spec/resolvers/cell.py",
              "pen_stack/spec/resolvers/feature.py", "pen_stack/spec/resolvers/phenotype.py",
              "pen_stack/spec/resolvers/chem.py", "pen_stack/spec/resolvers/locus.py",
              "benchmarks/writespec/corpus.json", "benchmarks/writespec/harness.py",
              "benchmarks/writespec/writespec_bench_metrics.json", "benchmarks/writespec/SHA256SUMS",
              "schemas/writespec.json", "docs/writespec_profile.md", "docs/writespec_bench.md",
              "prereg/ws_writespec.yaml", "prereg/SHA256_LOCK_ws_writespec.json"):
        assert (_ROOT / p).exists(), p


def test_oracle_mesh():
    # the oracle mesh: affinity dimension + per-oracle reliability + disagreement-to-interval
    from pen_stack.oracles.affinity import predict_affinity  # noqa: F401
    from pen_stack.oracles.reliability import all_reliability, disagreement_widens_monotonically  # noqa: F401
    from pen_stack.oracles.structure_run import complexes  # noqa: F401
    # the three Oracle-Bench gates pass: reliability verbatim, disagreement monotonic, affinity contract
    from benchmarks.oracle.harness import run
    assert run()["all_gates_pass"] is True
    for p in ("pen_stack/oracles/affinity.py", "pen_stack/oracles/reliability.py",
              "pen_stack/oracles/structure_run.py", "configs/oracles/reliability.yaml",
              "benchmarks/oracle/harness.py", "benchmarks/oracle/oracle_bench_metrics.json",
              "benchmarks/oracle/SHA256SUMS", "docs/oracle_mesh.md",
              "prereg/ws_oracle.yaml", "prereg/SHA256_LOCK_ws_oracle.json"):
        assert (_ROOT / p).exists(), p


def test_verification_service():
    # the verification service: rule spec + proof object + standards-aligned biosecurity
    from pen_stack.rules.spec import spec_parity  # noqa: F401
    from pen_stack.safety.standards import concordance_report  # noqa: F401
    from pen_stack.verify.proof import repair_from_proof, verify_proof  # noqa: F401
    # the three Verify-Bench gates pass: rule-spec parity, proof-object repair, standards concordance
    from benchmarks.verify.harness import run
    assert run()["all_gates_pass"] is True
    for p in ("pen_stack/rules/spec.py", "pen_stack/verify/proof.py", "pen_stack/safety/standards.py",
              "benchmarks/verify/harness.py", "benchmarks/verify/rule_spec.json",
              "benchmarks/verify/verify_bench_metrics.json", "benchmarks/verify/SHA256SUMS",
              "docs/rule_spec.md", "docs/verify_service.md",
              "prereg/ws_verify.yaml", "prereg/SHA256_LOCK_ws_verify.json"):
        assert (_ROOT / p).exists(), p


def test_cross_modality_delivery():
    # cross-modality deliverability + learned FLIP-AAV capsid-fitness
    from pen_stack.planner.delivery_immune import delivery_immune_tradeoff  # noqa: F401
    from pen_stack.planner.delivery_predict import capsid_fitness, recommend_delivery_plus  # noqa: F401
    # the learned capsid-fitness beats the baseline on both held-out FLIP-AAV splits
    from benchmarks.delivery.harness import run
    assert run()["learned_beats_baseline"] is True
    for p in ("pen_stack/planner/delivery_predict.py", "pen_stack/planner/delivery_immune.py",
              "pen_stack/design/capsid_generate.py", "configs/aav_serotype_tropism.yaml",
              "benchmarks/delivery/harness.py", "benchmarks/delivery/capsid_fitness_metrics.json",
              "benchmarks/delivery/split.json", "benchmarks/delivery/SHA256SUMS",
              "scripts/build_capsid_fitness.py", "docs/delivery_recommender.md",
              "prereg/ws_delivery.yaml", "prereg/SHA256_LOCK_ws_delivery.json"):
        assert (_ROOT / p).exists(), p


def test_offtarget_engine():
    # cross-family off-target nomination + Off-Target-Bench; the 4-assay expansion + chromatin annotation
    from pen_stack.wgenome.offtarget_assay import recommend_assay  # noqa: F401
    from pen_stack.wgenome.offtarget_data import BENCH_SUMMARY
    from pen_stack.wgenome.offtarget_predict import locus_accessibility, nominate_offtargets  # noqa: F401
    # the real learned predictor beats the homology baseline on ALL FOUR assays (full-data result)
    for a in ("guideseq", "circleseq", "changeseq", "siteseq"):
        assert BENCH_SUMMARY[a]["crisot_beats_homology"], a
    # chromatin validated (moderate, cell-type-matched); incremental over CRISOT is annotation, not a re-ranker
    from pen_stack.wgenome.offtarget_data import CHROMATIN_VALIDATION as CV
    assert CV["validated"] is True and CV["effect"] == "moderate"
    assert CV["incremental_over_crisot"]["improves_ranking"] is False and CV["changes_numeric_risk_score"] is False
    for p in ("pen_stack/wgenome/offtarget_data.py", "pen_stack/wgenome/offtarget_predict.py",
              "pen_stack/wgenome/offtarget_assay.py", "benchmarks/offtarget/harness.py",
              "benchmarks/offtarget/offtarget_bench_fixture.csv", "benchmarks/offtarget/offtarget_bench_metrics.json",
              "benchmarks/offtarget/offtarget_calibration.json", "benchmarks/offtarget/split.json",
              "benchmarks/offtarget/SHA256SUMS", "benchmarks/offtarget/chromatin_validation.json",
              "benchmarks/offtarget/chromatin_incremental.json", "scripts/offtarget_chromatin_validation.py",
              "scripts/offtarget_chromatin_matched.py", "scripts/offtarget_chromatin_incremental.py",
              "docs/offtarget.md", "docs/cards/offtarget_data.md",
              "prereg/ws_offtarget.yaml", "prereg/SHA256_LOCK_ws_offtarget.json"):
        assert (_ROOT / p).exists(), p


def test_immune_profiler():
    # MHC-II/CD4 + ADA + writer-as-antigen with real NetMHCIIpan-derived cache and real self-match
    from pen_stack.planner.ada_risk import ada_risk, real_self_match  # noqa: F401
    from pen_stack.planner.immune_mhc2 import mhc2_epitope_load, real_mhc2_load, writer_sequences  # noqa: F401
    # the real NetMHCIIpan-4.0 derived cache ships (licensed binaries never committed)
    assert real_mhc2_load("SpCas9") is not None and "NetMHCIIpan-4.0" in real_mhc2_load("SpCas9")["method"]
    # the real human-proteome self-match discriminates self (albumin 1.0) from foreign (Cas9 0.0)
    assert real_self_match("HumanAlbumin")["human_9mer_match_fraction"] == 1.0
    assert real_self_match("SpCas9")["human_9mer_match_fraction"] == 0.0
    for p in ("pen_stack/planner/immune_mhc2.py", "pen_stack/planner/ada_risk.py",
              "pen_stack/planner/capsid_epitope_oracle.py",
              "configs/writer_sequences.fasta", "configs/mhc_epitope_oracle.yaml",
              "benchmarks/immuno/harness.py", "docs/immune_profiler.md", "prereg/ws_immune2.yaml"):
        assert (_ROOT / p).exists(), p


def test_writer_efficiency():
    # curated writer-efficiency dataset + bench + predictor + guide/variant
    from pen_stack.atlas.guide_design import design_bridge_rna, select_orthogonal_att_pairs  # noqa: F401
    from pen_stack.atlas.writer_efficiency import records  # noqa: F401
    from pen_stack.atlas.writer_predict import WriterEfficiencyModel, evaluate  # noqa: F401
    from pen_stack.atlas.writer_recommend import recommend_writers  # noqa: F401
    from pen_stack.design.writer_variants import hyperactive_recovery  # noqa: F401
    for p in ("pen_stack/atlas/writer_efficiency.py", "pen_stack/atlas/writer_predict.py",
              "pen_stack/atlas/guide_design.py", "pen_stack/atlas/writer_recommend.py",
              "pen_stack/design/writer_variants.py", "data/writer_efficiency.parquet",
              "benchmarks/writer_efficiency/harness.py", "benchmarks/writer_efficiency/split.json",
              "benchmarks/writer_efficiency/SHA256SUMS", "docs/cards/writer_efficiency_data.md",
              "docs/writer_efficiency.md", "prereg/ws_writer.yaml", "scripts/p1_build_writer_eff.py"):
        assert (_ROOT / p).exists(), p


def test_position_effect_model():
    # learned, trained-conformal position-effect model + TPE-Bench
    from pen_stack.twin.data.position_effect import DATASETS, load_position_effect  # noqa: F401
    from pen_stack.twin.position_effect import PositionEffectModel, evaluate, predict_stage_h  # noqa: F401
    for p in ("pen_stack/twin/data/position_effect.py", "pen_stack/twin/position_effect.py",
              "benchmarks/position_effect/harness.py", "benchmarks/position_effect/split.json",
              "benchmarks/position_effect/SHA256SUMS", "configs/twin/position_effect_conformal.json",
              "pen_stack/validate/expr_controls.py", "pen_stack/validate/known_biology_expr.py",
              "pen_stack/validate/heldout_celltype_expr.py", "docs/position_effect.md", "docs/tpe_bench.md",
              "prereg/ws_expr2.yaml", "scripts/p1_build_position_effect.py"):
        assert (_ROOT / p).exists(), p


def test_live_oracles():
    # live oracles: execution/latency map + status surface + model servers + docs
    from pen_stack.oracles.status import execution_map, oracle_status, summary  # noqa: F401
    for p in ("configs/oracles/execution.yaml", "pen_stack/oracles/status.py", "docs/live_oracles.md",
              "docker-compose.models.yml", "model_servers/proteinmpnn/server.py",
              "model_servers/esm3/server.py", "model_servers/rfdiffusion/server.py"):
        assert (_ROOT / p).exists(), p


def test_hybrid_co_scientist_router():
    # the hybrid co-scientist: 4-lane router + metric guide + facts + hybrid llm + preregs
    from pen_stack.web.guide import metric_guide, pen_stack_facts  # noqa: F401
    from pen_stack.web.llm import grounded_reply  # noqa: F401
    from pen_stack.web.router import classify, pen_stack_angles  # noqa: F401
    for p in ("pen_stack/web/router.py", "pen_stack/web/guide.py", "configs/metric_guide.yaml",
              "prereg/ws_hybrid.yaml", "prereg/SHA256_LOCK_ws_hybrid.json"):
        assert (_ROOT / p).exists(), p


def test_web_platform():
    # the Web Platform: grounded co-scientist + UX frontend + Docker self-host + preregs
    from pen_stack.web import extract_grounded_numbers, grounded_reply, run_tools  # noqa: F401
    from pen_stack.web.llm import _deterministic_narrate, _enforce_grounding  # noqa: F401
    for p in ("pen_stack/web/__init__.py", "pen_stack/web/tools.py", "pen_stack/web/llm.py",
              "pen_stack/web/server.py", "tests/unit/test_grounded_chat.py", "docker/web.Dockerfile",
              "web/package.json", "web/src/App.jsx", "web/src/components/ConfidenceBand.jsx",
              "web/src/pages/CoScientist.jsx", "web/README.md",
              "prereg/ws_chat.yaml", "prereg/SHA256_LOCK_ws_chat.json",
              "prereg/ws_frontend.yaml", "prereg/SHA256_LOCK_ws_frontend.json"):
        assert (_ROOT / p).exists(), p


def test_grounding_guard_strikes_ungrounded_numbers():
    # the central grounding gate: a reply never carries a number absent from the tool results
    from pen_stack.web.llm import _enforce_grounding, ungrounded_numbers
    grounded = {"0.28", "1", "4500"}
    cleaned = _enforce_grounding("conf 0.28 but titer 9.99 at 4500 bp", grounded)
    assert "9.99" not in cleaned and "[unverified]" in cleaned
    assert ungrounded_numbers(cleaned, grounded) == []


def test_ai_integration_surface():
    # the AI integration surface: manifests + endpoints + MCP resources + examples + preregs
    from examples.agent_tools import dispatch, tool_specs  # noqa: F401
    from pen_stack.api import capability_manifest, scope_manifest
    cap, sc = capability_manifest(), scope_manifest()
    assert cap["tools"] and all(t["fabricates"] is False for t in cap["tools"])
    assert sc["known_unknowns"] and sc["oracle_scope_cards"] and sc["policy"]
    for p in ("pen_stack/api/manifest.py", "examples/external_agent.py", "examples/mcp_client.py",
              "examples/agent_tools.py", "prereg/ws_manifest.yaml", "prereg/SHA256_LOCK_ws_manifest.json",
              "prereg/ws_openapi.yaml", "prereg/SHA256_LOCK_ws_openapi.json", "prereg/ws_mcp.yaml",
              "prereg/SHA256_LOCK_ws_mcp.json"):
        assert (_ROOT / p).exists(), p


def test_genome_writing_challenge():
    # the Genome-Writing Challenge + the co-scientist over the loop + integrations + preregs
    from benchmarks.genome_writing_challenge.harness import (  # noqa: F401
        Submission,
        evaluate,
        reference_submission,
    )
    from pen_stack.agent.co_scientist import co_scientist_session  # noqa: F401
    for p in ("benchmarks/genome_writing_challenge/harness.py", "benchmarks/genome_writing_challenge/run.py",
              "benchmarks/genome_writing_challenge/README.md", "benchmarks/genome_writing_challenge/SUBMISSIONS.md",
              "docs/challenge.md", "docs/co_scientist_loop.md", "docs/integrations.md",
              "prereg/ws_challenge.yaml", "prereg/SHA256_LOCK_ws_challenge.json", "prereg/ws_cosci2.yaml",
              "prereg/SHA256_LOCK_ws_cosci2.json"):
        assert (_ROOT / p).exists(), p


def test_closed_loop_components():
    # the closed loop: cycle + drift + continual + bench + docs + preregs
    from pen_stack.loop import continual_update, detect_drift, run_loop  # noqa: F401
    from pen_stack.validate.closed_loop import run as _cl_bench  # noqa: F401
    for p in ("pen_stack/loop/__init__.py", "pen_stack/loop/cycle.py", "pen_stack/loop/drift.py",
              "pen_stack/loop/continual.py", "pen_stack/validate/closed_loop.py", "docs/closed_loop.md",
              "docs/autonomy.md", "prereg/ws_loop.yaml", "prereg/SHA256_LOCK_ws_loop.json",
              "prereg/ws_continual.yaml", "prereg/SHA256_LOCK_ws_continual.json", "prereg/ws_drift.yaml",
              "prereg/SHA256_LOCK_ws_drift.json"):
        assert (_ROOT / p).exists(), p


def test_build_interface():
    # the build interface: protocol + ingest + simlab + bench + preregs
    from pen_stack.build import (  # noqa: F401
        ProtocolExportError,
        export_protocol,
        ingest_result,
        run_simulated,
    )
    from pen_stack.validate.protocol_safety import run as _ps_bench  # noqa: F401
    for p in ("pen_stack/build/__init__.py", "pen_stack/build/protocol.py", "pen_stack/build/ingest.py",
              "pen_stack/build/simlab.py", "pen_stack/validate/protocol_safety.py", "docs/build_interface.md",
              "prereg/ws_proto.yaml", "prereg/SHA256_LOCK_ws_proto.json", "prereg/ws_ingest.yaml",
              "prereg/SHA256_LOCK_ws_ingest.json", "prereg/ws_simlab.yaml", "prereg/SHA256_LOCK_ws_simlab.json"):
        assert (_ROOT / p).exists(), p


def test_experiment_designer():
    # the experiment designer: acquire + design + validate + bench + preregs
    from pen_stack.active import (  # noqa: F401
        acquisition_score,
        expected_information_gain,
        immune_voi,
        retrospective_active_learning,
        select_batch,
    )
    from pen_stack.validate.experiment_design import run as _ed_bench  # noqa: F401
    for p in ("pen_stack/active/__init__.py", "pen_stack/active/acquire.py", "pen_stack/active/design.py",
              "pen_stack/active/validate.py", "pen_stack/validate/experiment_design.py",
              "docs/experiment_design.md", "prereg/ws_acq.yaml", "prereg/SHA256_LOCK_ws_acq.json",
              "prereg/ws_aldesign.yaml", "prereg/SHA256_LOCK_ws_aldesign.json", "prereg/ws_alvalidate.yaml",
              "prereg/SHA256_LOCK_ws_alvalidate.json"):
        assert (_ROOT / p).exists(), p


def test_digital_twin():
    # the digital twin: vcell oracle + mechanistic + outcome + calibrate + bench + preregs
    from pen_stack.oracles.vcell import predict_response  # noqa: F401
    from pen_stack.twin import calibrate_outcome, cassette_expression, predict_outcome  # noqa: F401
    from pen_stack.validate.outcome_prediction import run as _twin_bench  # noqa: F401
    for p in ("pen_stack/oracles/vcell.py", "pen_stack/twin/__init__.py", "pen_stack/twin/mechanistic.py",
              "pen_stack/twin/outcome.py", "pen_stack/twin/calibrate.py",
              "pen_stack/validate/outcome_prediction.py", "docs/digital_twin.md",
              "prereg/ws_vcell.yaml", "prereg/SHA256_LOCK_ws_vcell.json", "prereg/ws_mech.yaml",
              "prereg/SHA256_LOCK_ws_mech.json", "prereg/ws_outcome.yaml", "prereg/SHA256_LOCK_ws_outcome.json",
              "prereg/ws_twincal.yaml", "prereg/SHA256_LOCK_ws_twincal.json"):
        assert (_ROOT / p).exists(), p
    # the virtual-cell oracle scope cards are registered
    import yaml
    cards = yaml.safe_load((_ROOT / "configs/oracles/scope_cards.yaml").read_text(encoding="utf-8"))["oracles"]
    assert "state" in cards and "scgpt" in cards and cards["state"]["family"] == "vcell"


def test_generative_designer():
    # the generative designer: space/generate/pareto + live orchestrator + bench + preregs
    from pen_stack.agent.orchestrator_live import orchestrate  # noqa: F401
    from pen_stack.design import candidate_space, generate_designs, neg_immune_risk, pareto_front  # noqa: F401
    from pen_stack.validate.generative_design import run as _gen_bench  # noqa: F401
    for p in ("pen_stack/design/__init__.py", "pen_stack/design/space.py", "pen_stack/design/generate.py",
              "pen_stack/design/pareto.py", "pen_stack/agent/orchestrator_live.py",
              "pen_stack/validate/generative_design.py", "docs/generative_design.md",
              "prereg/ws_gen.yaml", "prereg/SHA256_LOCK_ws_gen.json", "prereg/ws_pareto.yaml",
              "prereg/SHA256_LOCK_ws_pareto.json", "prereg/ws_orch.yaml", "prereg/SHA256_LOCK_ws_orch.json"):
        assert (_ROOT / p).exists(), p


def test_safety_gate():
    # the Guardian safety gate: registry/screen/policy/gate/audit/redteam + Verdict.safety + bench + preregs
    from pen_stack.safety import SafetyVerdict, safety_gate, screen_design, verify_chain  # noqa: F401
    from pen_stack.validate.safety_screening import run as _safety_bench  # noqa: F401
    from pen_stack.verify.schema import Verdict
    assert "safety" in Verdict.model_fields
    for p in ("pen_stack/safety/registry.py", "pen_stack/safety/screen.py", "pen_stack/safety/policy.py",
              "pen_stack/safety/gate.py", "pen_stack/safety/audit.py", "pen_stack/safety/redteam.py",
              "configs/safety/hazard_registry.yaml", "configs/safety/policy.yaml", "configs/safety/probes.yaml",
              "pen_stack/validate/safety_screening.py", "docs/responsible_use.md", "docs/biosecurity.md",
              "prereg/ws_screen.yaml", "prereg/SHA256_LOCK_ws_screen.json", "prereg/ws_policy.yaml",
              "prereg/SHA256_LOCK_ws_policy.json", "prereg/ws_redteam.yaml",
              "prereg/SHA256_LOCK_ws_redteam.json"):
        assert (_ROOT / p).exists(), p


def test_antipeg_immune_profile():
    # anti-PEG oracle + calibration + unified profile + Verdict.immune_profile + preregs
    from pen_stack.planner.antipeg_oracle import antipeg_oracle  # noqa: F401
    from pen_stack.planner.immune_profile import immune_profile  # noqa: F401
    from pen_stack.validate.immune_calibration import calibrate_axis  # noqa: F401
    for p in ("pen_stack/planner/antipeg_oracle.py", "configs/antipeg.yaml",
              "pen_stack/planner/immune_profile.py", "pen_stack/validate/immune_calibration.py",
              "prereg/ws_peg.yaml", "prereg/SHA256_LOCK_ws_peg.json", "prereg/ws_calib.yaml",
              "prereg/SHA256_LOCK_ws_calib.json", "prereg/ws_profile.yaml",
              "prereg/SHA256_LOCK_ws_profile.json"):
        assert (_ROOT / p).exists(), p


def test_seroprevalence_oracle():
    # anti-vector seroprevalence oracle + curated table + scope card + prereg
    from pen_stack.planner.seroprevalence_oracle import computed_preexisting_score, seroprevalence_oracle  # noqa: F401,E501
    for p in ("pen_stack/planner/seroprevalence_oracle.py", "configs/seroprevalence.yaml",
              "prereg/ws_seroprev.yaml", "prereg/SHA256_LOCK_ws_seroprev.json"):
        assert (_ROOT / p).exists(), p


def test_innate_sensing():
    # computed innate-sensing scorer + scope card + prereg
    from pen_stack.planner.innate_sensing import computed_innate_score, innate_sensing  # noqa: F401
    for p in ("pen_stack/planner/innate_sensing.py", "prereg/ws_innate.yaml",
              "prereg/SHA256_LOCK_ws_innate.json"):
        assert (_ROOT / p).exists(), p


def test_capsid_epitope_oracle():
    # computed capsid epitope oracle + committed summary + sequences + scope card + prereg
    from pen_stack.planner.capsid_epitope_oracle import capsid_epitope_oracle, computed_capsid_immune_score  # noqa: F401,E501
    for p in ("pen_stack/planner/capsid_epitope_oracle.py", "configs/capsid_epitope_oracle.yaml",
              "configs/capsid_sequences.fasta", "scripts/p53_build_epitope_oracle.py",
              "prereg/ws_epitope.yaml", "prereg/SHA256_LOCK_ws_epitope.json"):
        assert (_ROOT / p).exists(), p


def test_genotoxicity_oracle():
    # computed genotoxicity oracle + committed summary + scope card + prereg
    from pen_stack.planner.genotoxicity_oracle import computed_genotox_score, genotoxicity_oracle  # noqa: F401
    for p in ("pen_stack/planner/genotoxicity_oracle.py", "configs/genotoxicity_oracle.yaml",
              "scripts/p52_build_genotox_oracle.py", "prereg/ws_genotox.yaml",
              "prereg/SHA256_LOCK_ws_genotox.json"):
        assert (_ROOT / p).exists(), p


def test_delivery_immunology():
    # delivery-immunology planner + per-vehicle immune profiles + verify surfacing
    from pen_stack.planner.delivery_immunology import recommend_delivery, safety_efficacy_profile  # noqa: F401
    for p in ("pen_stack/planner/delivery_immunology.py", "prereg/ws_immune.yaml",
              "prereg/SHA256_LOCK_ws_immune.json"):
        assert (_ROOT / p).exists(), p


def test_co_scientist_core():
    # co-scientist: plan/multi/crit/scope/cite/gen + bench reference solver
    from pen_stack.agent.cite import cited_rationale, generalise  # noqa: F401
    from pen_stack.agent.co_scientist import critique_and_revise, propose_strategies, scope_ledger  # noqa: F401
    from pen_stack.validate import bench_coscientist_tasks  # noqa: F401
    for p in ("docs/co_scientist.md", "pen_stack/agent/co_scientist.py", "pen_stack/agent/cite.py",
              "prereg/ws_plan.yaml", "prereg/ws_crit.yaml", "prereg/ws_cite.yaml",
              "prereg/SHA256_LOCK_ws_plan.json", "prereg/SHA256_LOCK_ws_crit.json",
              "prereg/SHA256_LOCK_ws_cite.json"):
        assert (_ROOT / p).exists(), p


def test_no_fabrication_under_full_reasoning_stack():
    # the central gate, asserted at release: the matured co-scientist never fabricates
    from pen_stack.validate.bench_coscientist_tasks import run
    rep = run()
    assert rep["co_scientist_grounded_rate"] == 1.0 and rep["no_fabrication"] is True


def test_world_model_graph():
    # world-model graph + gated ingest + cell-type coverage + graph bench
    from pen_stack.graph import build_graph  # noqa: F401
    from pen_stack.graph.cell_types import coverage_card  # noqa: F401
    from pen_stack.graph.ingest import gate_admit  # noqa: F401
    from pen_stack.validate import bench_graph_tasks  # noqa: F401
    for p in ("docs/world_model.md", "configs/cell_types.yaml", "pen_stack/graph/schema.py",
              "prereg/ws_graph.yaml", "prereg/ws_mon.yaml", "prereg/ws_ct.yaml", "prereg/ws_ba_v45.yaml",
              "prereg/SHA256_LOCK_ws_graph.json", "prereg/SHA256_LOCK_ws_mon.json",
              "prereg/SHA256_LOCK_ws_ct.json", "prereg/SHA256_LOCK_ws_ba_v45.json"):
        assert (_ROOT / p).exists(), p


def test_oracle_mesh_atlas():
    # oracle mesh + writer-verification + mesh atlas, docs + prereg present
    from pen_stack.atlas import writer_verify  # noqa: F401
    from pen_stack.oracles import OracleResult  # noqa: F401
    from pen_stack.wgenome import mesh_features  # noqa: F401
    for p in ("docs/oracles.md", "docs/writer_verification.md",
              "configs/oracles/scope_cards.yaml", "pen_stack/oracles/schema.py",
              "prereg/ws_o.yaml", "prereg/ws_wv.yaml", "prereg/ws_atlas.yaml",
              "prereg/SHA256_LOCK_ws_o.json", "prereg/SHA256_LOCK_ws_wv.json",
              "prereg/SHA256_LOCK_ws_atlas.json"):
        assert (_ROOT / p).exists(), p


def test_verifier_and_rules():
    # rule base + verifier importable, docs + prereg present
    from pen_stack.rules import load_ruleset
    from pen_stack.verify import verify  # noqa: F401
    assert len(load_ruleset().rules) >= 9
    for p in ("docs/verify.md", "docs/rules.md", "docs/delivery.md",
              "prereg/ws_r.yaml", "prereg/ws_v.yaml", "configs/delivery_vehicles.yaml"):
        assert (_ROOT / p).exists(), p


def test_core_docs_exist():
    for p in ("docs/uncertainty.md", "docs/scope.md", "docs/mechanistic_constraints.md", "docs/BACKLOG.md"):
        assert (_ROOT / p).exists(), p


def test_core_prereg_locks_present():
    for ws in ("uq", "ep", "mc", "ba"):
        assert (_ROOT / f"prereg/ws_{ws}.yaml").exists(), ws
        assert (_ROOT / f"prereg/SHA256_LOCK_ws_{ws}.json").exists(), ws


def test_bench_task_coverage():
    import yaml
    cfg = yaml.safe_load((_ROOT / "benchmarks/genome_writing_bench/tasks.yaml").read_text(encoding="utf-8"))
    assert cfg["version"] >= "0.3"
    ids = {t["id"] for t in cfg["tasks"]}
    assert {"multi_write_type_legality", "adversarial_robustness", "rule_grounded_legality"} <= ids

# NOTE: manuscripts/ is intentionally gitignored - drafts live outside the public repo - so the release
# test does NOT assert their presence (they are absent in a clean CI checkout / a clone, by design).
