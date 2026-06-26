# Changelog

All notable changes to PEN-STACK are documented here. This file follows
[Keep a Changelog](https://keepachangelog.com/).

## [7.1.3] - 2026-06-26 - Designer correctness: Guardian biosecurity + calibrated confidence

### Fixed
- **CRITICAL (Designer / Guardian biosecurity):** Hazardous cargo functions (e.g. furin-cleavage viral
  tropism-enhancement, dominant-negative tumor-suppressor ablation) passed the Designer as "Safety: Clear" with
  full survivor tables. Several root causes, all fixed:
  - The hazard registry (`configs/safety/hazard_registry.yaml`) had **no signatures** for engineered viral tropism
    enhancement or oncogenic tumor-suppressor ablation. Added `FUNC-VIRAL-TROPISM-ENHANCE` (furin cleavage /
    receptor-binding / tropism, high severity) and `FUNC-ONCOGENIC-SUPPRESSOR` (dominant-negative TP53 / RB / PTEN,
    apoptosis-checkpoint ablation, high severity), both DURC / HHS-P3CO categories.
  - **Oncogenic-manipulation PATTERN screen** (`oncogenic_manipulation` in the registry +
    `HazardRegistry.oncogenic_flags`): a flat keyword list is brittle to paraphrase — a red-team pass found the
    Guardian caught only **1/8** mechanism/synonym phrasings ("R175H p53 abolishing transactivation", "PTEN
    knockout", "RAS G12D constitutive activation", "hTERT immortalization", "APC frameshift", "EGFR
    ligand-independent activation", "NF1+BAX/BAK knockout"). The pattern screen flags the *combination*
    `(tumor-suppressor + disruptive verb)` OR `(oncogene + activating signature)` OR `immortalization`, which
    catches **8/8** while the deliberate asymmetry spares therapy with **no allow-list** — restoring a suppressor or
    silencing an oncogene matches neither, so "p53 correction to restore apoptosis", "TRAC/CCR5 knockout",
    "knock-down of mutant KRAS" stay clear (**11/11** benign). Disposition is escalate (dual-use → human review).
  - **Keyword matcher hardened** (`_kw_match`): a plain substring test made the ricin abbreviation `"rip"` fire
    inside **"transc-rip-tion"** (a word in almost every editing design → benign cassettes false-refused as ricin),
    and let a hyphenated `"furin-cleavage"` slip past the space-form keyword. Matching is now separator-insensitive
    (`-`/`_`/space unified) and word-boundary anchored, fixing both the false positive and the evasion.
  - The goal-based candidate path (`pen_stack/design/space.py::candidate_space`) **dropped** the goal's
    `cargo_function`, so the Guardian in `verify()` screened nothing. It is now propagated onto every swept
    candidate. The `/generate` endpoint additionally screens the goal's cargo function FIRST and returns an explicit
    biosecurity refusal (`refused: true` + the safety verdict) so an empty table is correctly attributed to a
    refusal, not a silent "no candidates".
- **CRITICAL (Designer / calibration):** Confidence was a constant `1.00 · [0.56, 0.71]` for every input because the
  page hardcoded fake planner scores (0.7 / 0.6 / 0.5) on each candidate. The page now submits the design GOAL and
  the engine plans real writable sites with grounded per-locus safety / durability / writer-activity, so the
  confidence band is genuinely calibrated (it differs by locus/vehicle, e.g. F9 → `[0.866, 0.972]`, and is absent
  for a refused design). `web/src/pages/Designer.jsx` rewritten to send a goal and render the refused / empty /
  survivor states distinctly.
- **Designer (cell types without a measured atlas):** a goal in a cell type with no writability atlas (cd8_t /
  pbmc / h1_hesc / ipsc) returned an empty table, because the planner-backed `candidate_space` needs `plan_write`.
  `generate_designs` now falls back to `space.vehicle_sweep(goal)`: it sweeps the capacity-compatible vehicles,
  carries `cargo_function` (the Guardian still screens), runs full legality + biosecurity discrimination, and
  ABSTAINS on the calibrated confidence (no fabricated band) — surfaced as "abstained, no measured atlas for this
  cell type". `candidate_space` still returns `[]` without the atlas; `generate_designs(candidates=[])` still
  returns `[]`.
- **Designer (administration context):** the vehicle sweep now filters by the goal's `in_vivo` flag using the
  curated `in_vivo` / `ex_vivo` route flags in `configs/delivery_vehicles.yaml` (an ex-vivo goal keeps
  lentivirus / electroporation / eVLP; an in-vivo goal keeps AAV / LNP / HDAd / HSV / eVLP). Grounded from the
  curated palette, not a clinical claim; `in_vivo=None` keeps all (existing callers/tests unchanged).

## [7.1.2] - 2026-06-25 - PEN-CHAT: chat-response latency fix

### Fixed
- Chat response time was unnecessarily high because every General-lane request paid for an Ollama embedding
  round-trip on the query side, and the LLM call ran with a generous 150 s timeout / 450-token cap suited to the
  engine-grounded design lane, not a textbook answer. Three minimal changes, no behaviour change for the grounded
  lanes:
  - `pen_stack/rag/embed.py` adds an LRU-cached `embed_query()` (256 entries) so a repeated phrasing skips the
    embedder; `pen_stack/rag/retrieve.py` uses it.
  - `pen_stack/web/llm_provider.py` now accepts `kind="general"`, which selects `PEN_STACK_LLM_TIMEOUT_GENERAL`
    (45 s default, was 150 s) and `OLLAMA_NUM_PREDICT_GENERAL` / `NEMOTRON_MAX_TOKENS_GENERAL` (280 / 400, was
    450 / 700). The default-kind path used by the engine-grounded design / explain / meta lanes is unchanged
    (`PEN_STACK_LLM_TIMEOUT` default lowered 150 → 90).
  - The General-lane and PEN-RAG cited-answer callers (`pen_stack/rag/ground.py`, `pen_stack/web/llm.py`) now pass
    `kind="general"`.
- No grounding-guard change; the LLM stays non-load-bearing and the per-lane provenance labels are unchanged.

## [7.1.1] - 2026-06-24 - PEN-CHAT: General-lane helpfulness fix + benchmark-validity correction

### Fixed
- The General lane over-abstained: it declined simple/social ("hi") and general-knowledge ("what is DNA")
  questions because P-WS1 made corpus retrieval a GATE on the whole lane. Retrieval is now **additive**
  (`pen_stack/rag/ground.py`): the lane ANSWERS general + social questions, clearly labelled
  "general - not PEN-STACK-verified" (a labelled general answer is honest, not a fabrication); a corpus hit
  upgrades to "literature-cited"; abstention is reserved for a SPECIFIC unsourceable empirical claim. The "general"
  provenance chip is restored in the web chat.

### Changed
- Benchmark-validity correction: the head-to-head headline moves from "answers-without-grounding" (which rewarded
  over-abstention) to the **false-grounding rate** (a non-engine fact presented as a PEN-STACK result; 0.0 by
  construction). Abstention is re-scoped to specific unsourceable empirical claims; the routing/grounding/safety
  sets now include positive general + social cases that require a helpful, labelled answer (a regression guard).
  `prereg/ws_penchat.yaml` amended + re-locked accordingly.

## [7.1.0] - 2026-06-24 - PEN-CHAT: the grounded conversational system

Consolidates the four-lane chat (WS-HYBRID) with PEN-RAG into a fully-grounded, provenance-partitioned
conversational agent: every surfaced fact is engine-computed or retrieved-and-cited, no claim originates from
model weights, and the property is MEASURED, not asserted. The LLM is a swappable, non-load-bearing narrator.

### Added
- **Grounded General lane (PEN-RAG)** (`pen_stack/rag/{corpus,embed,retrieve,ground}.py`). The general lane no
  longer answers from unsourced trained knowledge: it retrieves over a provenance-tagged corpus
  (`data/rag_corpus.parquet`, built only from real DOI-backed repo content) with a committed embedding matrix
  (`nomic-embed-text` via Ollama; exact cosine, no FAISS at this scale) and a deterministic lexical fallback,
  answers under citation-or-silence, and **abstains** below a retrieval-confidence threshold. General answers are
  labelled `literature-cited` or `abstained`, never a PEN-STACK-computed result.
- **Swappable LLM provider abstraction** (`pen_stack/web/llm_provider.py`): one interface over local Ollama / cloud
  Nemotron; the grounded result (lane, provenance, sources, numbers) is invariant to the provider.
- **Lane + provenance memory**: a follow-up to a grounded answer stays grounded.
- **Evaluation suite** measuring the no-fabrication claim: `benchmarks/chat_{routing,grounding,safety,headtohead}`
  (routing-safety 0.0, citation coverage 1.0, 0 unsupported claims, false-grounding 0.0, dual-use refusal 1.0,
  injection-hold 1.0). Pre-registered + SHA-locked in `prereg/ws_penchat.yaml`.
- The chat is registered as a capability (`chat_answer`, `fabricates: False`); provenance / citation / abstention /
  refusal chips in the web chat.

### Changed
- The pre-route biosecurity screen now escalates a build/express intent over any flagged dual-use hazard term even
  when the specific agent is not catalogued; the router was made conservative so a write request never leaks to the
  ungrounded lane.

## [7.0.0] - 2026-06-22 - Closed loop: a biosecurity-gated, Level-3 self-driving-lab engine

The capstone. Turns the in-silico closed loop into a genome-writing-specific, biosecurity-gated, autonomy-honest
(Level 3) self-driving-lab engine: a cloud-lab connector, a benchmark of the experiment designer against the
public optimizers, and a validation-campaign engine that points active learning at the measurements which would
earn the program's first outcome-validated axis. It consumes the WriteSpec and pairs with the biosecurity gate.
Full autonomy is not claimed; the wet run is the named bottleneck.

### Added
- **Cloud-lab connector** (`pen_stack/build/cloudlab.py`). `submit_gated` bridges the build interface to a cloud
  lab. The biosecurity gate runs BEFORE any submission: a flagged or illegal design raises and emits no protocol
  (a ricin design is refused), returning a structured refusal an agent can branch on; a cleared design returns a
  mock / dry-run job receipt. A returned readout is admitted only through an explicit human-in-control gate.
- **SDL-brain benchmark** (`pen_stack/active/brains.py`). Benchmarks the EIG/VOI experiment designer against the
  public self-driving-lab optimizers BayBE (Apache-2.0) and Atlas on a shared acquisition task, reported verbatim
  with both cited. The designer shows a positive mean information-gain advantage over random whose bootstrap CI is
  rep-sensitive and includes 0 at higher rep counts; reported as not-CI-significant, not hidden.
- **Validation-campaign engine** (`pen_stack/active/campaign.py`). Orders the candidate
  (cassette x locus x cell type) expression measurements by expected information gain, names the
  `validate.calibrate_axis` gate they would flip, and emits an executable, cloud-lab-submittable campaign spec.
  The campaign measures independent data, never the model's own outputs.
- **Loop-Bench** (`benchmarks/loop/`) reporting the three gates, and surfaces: REST `GET /api/campaign`,
  `POST /api/cloudlab`, `GET /api/brains`; MCP `validation_campaign`, `cloudlab_submit`; `docs/closed_loop.md`.

### Notes
- The loop is Level 3 (human in control); Level 4-5 is not claimed. The biosecurity gate is necessary, not
  sufficient (the full sequence screen is the downstream BioFirewall).
- A real wet run, and thus the first outcome-validated axis, needs a cloud-lab partner and budget; the connector
  and the executable campaign are the mechanism, the partner is the bottleneck, surfaced not hidden.

## [6.14.0] - 2026-06-22 - WriteSpec: a typed, ontology-backed intent layer with a grounded extractor and a feasibility check

Replaces the keyword parser with a typed, machine-checkable genome-writing request (an SBOL3 profile), a grounded
prose-to-spec extractor that labels every inference and never fabricates intent, and a feasibility check. This is
the agentic front-end: one contract the whole stack consumes. A WriteSpec is a request, not a claim.

### Added
- **The WriteRequest type** (`pen_stack/spec/writespec.py`, `schemas/writespec.json`). A typed model carrying the
  write semantics (write-type, cargo with Sequence-Ontology roles, target gene/locus/att-site/phenotype, cell
  type, constraints) plus a per-field provenance map (explicit / inferred / user / unresolved). Lossless JSON
  round-trip; SBOL3 round-trip via the real `sbol3` library (the `[spec]` extra; native Components + SO roles for
  interoperability); GenBank export for a cargo with a sequence; and `to_legacy_design`, the adapter that lets
  every existing stage consume a WriteRequest without a rewrite.
- **Vocabulary resolvers** (`pen_stack/spec/resolvers/`). Free text to canonical id: HGNC genes (atlas-grounded),
  Cellosaurus / Cell Ontology cell types, Sequence Ontology feature roles, MONDO phenotypes, ChEBI molecules,
  GRCh38 coordinates. Every curated id was verified against the live ontology services before commit; an
  unresolved term stays null, never invented.
- **Grounded extractor + clarifying-question planner** (`pen_stack/spec/extract.py`, `clarify.py`). A
  deterministic backbone (so the benchmark is reproducible) that labels every inferred field, asks a clarifying
  question for anything underspecified or ambiguous, and keeps unresolved terms null.
- **Feasibility check** (`pen_stack/spec/satisfy.py`). Wraps reachability (the atlas), deliverability (the
  delivery recommender), and legality (the verification proof object) into feasible / infeasible plus named
  blocking constraints and repair hints; feasibility is necessary, not sufficient (not efficacy).
- **WriteSpec-Bench** (`benchmarks/writespec/`). The first prose-to-write-spec corpus, grounded in real
  experiments, with an ambiguity subset and a sealed held-out. Reported verbatim: sealed-test structural fidelity
  1.0 and value accuracy 0.96 versus a 0.46 keyword-dict baseline; inferred-field labelling recall 1.0.
- **Surfaces**: REST `POST /api/writespec`, MCP `writespec_parse`, the manifest tool, the web "Describe a Write"
  builder page, and `docs/writespec_profile.md` + `docs/writespec_bench.md`.

### Notes
- Feasibility rules out unreachable / undeliverable / illegal, not whether the write will work.
- The extractor backbone is deterministic; an LLM pass is optional and adds no ground truth (it may only propose
  values that still pass the resolvers).

## [6.13.0] - 2026-06-22 - Oracle mesh: binding-affinity dimension, per-oracle reliability, disagreement-to-uncertainty

Hardens the foundation-model oracle mesh under one result contract. Adds a binding-affinity dimension
(Boltz-2), surfaces each oracle's published reliability reported verbatim from public benchmarks, and makes
cross-oracle disagreement widen the reported interval. Every oracle output stays a candidate, never ground
truth.

### Added
- **Binding-affinity oracle** (`pen_stack/oracles/affinity.py`). Wraps the Boltz-2 protein-ligand affinity head
  (MIT, `10.1101/2025.06.14.659707`): a binder probability and a predicted affinity value with native
  uncertainty taken from the model's own outputs. The head is protein-small-molecule only, so protein-protein
  and protein-DNA pairs are returned as out-of-scope (extrapolating). The backend runs off the request path and
  is cached; an uncached request defers (cache-or-abstain) rather than blocking or fabricating. A grounded,
  in-domain example is committed: 4-hydroxytamoxifen binding the ERT2 ligand-binding domain (the inducible-writer
  switch), predicted as a high-confidence binder (binder probability 0.99, complex pLDDT 0.94).
- **Per-oracle reliability registry** (`pen_stack/oracles/reliability.py`, `configs/oracles/reliability.yaml`).
  Each oracle's published benchmark accuracy, reported verbatim with citation: the Boltz-2 affinity head's
  FEP+ Pearson r of about 0.62 (paper-reported) is the verified anchor. These are the wrapped models' published
  numbers, not a claim about this stack's accuracy and not re-computed; where a verbatim score was not verified
  the value is left null with the cited benchmark as the pointer.
- **Disagreement to uncertainty.** Cross-oracle disagreement widens the reported interval (native uncertainty
  plus half the cross-oracle spread); a check confirms the widening is monotonic in the spread.
- **Held-oracle runner** (`pen_stack/oracles/structure_run.py`) for the structure oracles over writer-substrate
  and att-site complexes: off the request path, cache-or-abstain.
- **Oracle-Bench** (`benchmarks/oracle/`) reporting the three gates, and surfaces: `GET /api/oracles` extended
  with reliability and the disagreement check, `POST /api/oracle/affinity`, MCP `oracle_query`, the manifest
  `oracle_query` tool, the web Oracle Mesh page, and `docs/oracle_mesh.md`.

### Notes
- Affinity predictions are candidates with native uncertainty, not measured binding constants; reliability is
  surfaced so a confident-looking value is not over-trusted.
- The structure oracles over full complexes (AlphaFold3 / Boltz-2 / Chai-1 / Protenix) remain held: run
  separately on GPU or cloud and cached, never inline on the request path.

## [6.12.0] - 2026-06-21 - Verification service: published rule spec, proof object, standards-aligned biosecurity

Hardens `verify(design)` into a formal verification service. The rule base becomes a published, citable spec;
`verify_proof()` returns a repair-oriented proof object an agent can fix a failed design from; and the
biosecurity gate is mapped to the community synthesis-screening standards.

### Added
- **Published rule spec** (`pen_stack/rules/spec.py`, `benchmarks/verify/rule_spec.json`, `docs/rule_spec.md`).
  The rule base exports as a machine-readable, citable document. A parity check confirms the exported spec
  round-trips to the exact ruleset the solver loads (0 mismatches), every rule names a registered evaluator,
  and every rule carries a DOI or a note.
- **Repair-oriented proof object** (`pen_stack/verify/proof.py`). `verify_proof(design)` returns three axes,
  legality, confidence and biosecurity, reported separately, each with a status, the rule or signature that
  fired, evidence, and a repair hint; the collapsed verdict is `None`. `repair_from_proof` fixes a
  failed-on-legality design using only the proof object and re-verifies it. Biosecurity hazards are
  acknowledged and routed to human review, never auto-repaired.
- **Biosecurity standards alignment** (`pen_stack/safety/standards.py`). Maps the Guardian screen kinds and
  decisions onto the IBBIS Common Mechanism categories and `ScreenStatus` (Pass / Warning / Flag) and onto
  SecureDNA's pass/deny outcome, with a concordance report (8/8 concordant on the labelled probe set).
  References: Common Mechanism (Wheeler et al. 2024, `10.1089/apb.2023.0034`); SecureDNA (`arXiv:2403.14023`).
- **Verify-Bench** (`benchmarks/verify/`) reporting the three gates, and surfaces: REST `POST /api/verify/proof`,
  MCP `verify_proof`, manifest tool `verify_proof`, the web Verify page (per-axis green/amber/red with the
  violated rule, its citation, and the suggested fix), and `docs/verify_service.md`.

### Notes
- The verdict covers legality, feasibility and biosecurity, not efficacy (efficacy stays a downstream
  prediction with its own uncertainty). The biosecurity hook is the in-design gate; the full sequence-screening
  pipeline is BioFirewall, and the standard alignment is a concordance, not a certification.
- The plan paired this with a Stage A WriteSpec / SAT repair loop. Stage A is not yet built, so the proof-object
  repair loop here is self-contained; the WriteSpec coupling is a documented future integration.

## [6.11.0] - 2026-06-20 - Cross-modality deliverability and a learned capsid-fitness model

Delivery moves from an 8-vehicle rule palette to a cross-modality recommender. It adds a learned,
benchmarked AAV capsid-fitness model, a serotype-to-tissue tropism prior grounded in approved therapies, and an
immune-coupled dose tradeoff, without fabricating tropism. All datasets were independently verified.

### Added
- **Learned AAV capsid-fitness on FLIP-AAV** (`pen_stack/planner/delivery_predict.py`, `scripts/build_capsid_fitness.py`,
  `benchmarks/delivery/`). Trained on the FLIP-AAV benchmark (Dallago 2021; Bryant 2021 packaging fitness,
  `10.1038/s41587-020-00793-4`; Ogden 2019 `10.1126/science.aaw2900`). It beats a mutation-burden baseline on
  both held-out splits: `sampled` Spearman 0.920 vs 0.522 (CI [0.387, 0.411]); `mut_des`
  (mutant to designed) 0.814 vs 0.752 (CI [0.061, 0.064]). The 217 MB/split FLIP data stays on the VM; the derived
  metrics and the reproducible build script are committed. The ~3 MB model itself is gitignored, regenerated via
  `scripts/build_capsid_fitness.py` and mounted into the deployed app (like `position_effect.pkl`); the axis abstains
  gracefully when absent. Predicted fitness is a candidate for the measured packaging axis, not in-vivo tropism.
- **Serotype-to-tissue tropism priors** (`configs/aav_serotype_tropism.yaml`) from approved AAV therapies (AAV9 to CNS,
  AAVrh74 to skeletal muscle vs AAVRh74var to liver: different capsids, kept separate; AAV5 to liver; AAV2 to retina/
  putamen via local injection). This is a grounded prior for an approved serotype and a known-unknown (abstain) for a novel
  capsid. Casgevy/Lyfgenia carry no serotype prior (not-AAV controls).
- **Immune-coupled dose tradeoff** (`pen_stack/planner/delivery_immune.py`) fuses deliverability with the Stage G
  immune profile and surfaces dose vs immunogenicity per vehicle as a vector (`collapsed_score=None`, never fused).
- **Verify-gated generative capsids** (`pen_stack/design/capsid_generate.py`): fitness-filtered VP1 variants,
  candidates only; abstains without the model.
- **Surfaces:** REST `POST /delivery`, `POST /capsid_fitness`, and `GET /delivery/tropism`; MCP `delivery_recommend`;
  manifest `recommend_delivery` and `capsid_fitness`; a `capsid_fitness` scope card; a `delivery` Challenge task
  (serotype to tissue); preregistration `ws_delivery.yaml`.

### Limitations
- The capsid-fitness model is a one-hot gradient-boosting model, not a protein-LM (it passes the gate; a protein-LM is
  the upgrade path). Capsid-fitness covers AAV only (VLP/LNP data is thinner). In-vivo human tropism is
  a known-unknown except for the approved-therapy priors; novel capsids abstain on tropism. alpha-retro-VLP is exploratory.

## [6.10.4] - 2026-06-20 - Chromatin incremental-value test (annotation, not a re-ranker)

This patch closes out the chromatin work. v6.10.3 validated accessibility as a moderate standalone
predictor; v6.10.4 tests whether it adds incremental value on top of the CRISOT sequence score, i.e. whether
it should re-rank.

### Added
- **Incremental-value analysis** (`scripts/offtarget_chromatin_incremental.py`; result in
  `benchmarks/offtarget/chromatin_incremental.json`). On GUIDE-seq (HEK293T-matched), per off-target CRISOT plus
  accessibility: (A) a conditional logistic regression `active ~ z(CRISOT) + z(accessibility)` and (B) a
  leave-one-guide-out held-out AUPRC of CRISOT-only vs a CRISOT+accessibility combiner, tested at two candidate
  imbalances (1:16 and a realistic 1:123). Result: accessibility carries a small, real conditional signal
  (coef ~0.35, bootstrap CI excludes 0 at both imbalances) but adds no held-out ranking improvement over CRISOT
  (AUPRC gap CI includes 0 at both: -0.0025 [-0.011, +0.005] and +0.0027 [-0.014, +0.021]).

### Decision
- Chromatin is a validated annotation, not a re-ranker. The CRISOT sequence score already captures the
  practically-relevant nomination ranking; a CRISOT+accessibility combiner does not improve held-out AUPRC, so it is
  not wired into the numeric risk score (`CHROMATIN_VALIDATION.changes_numeric_risk_score = False`). The fitted
  combiner coefficients are recorded but intentionally not applied. Ledger and docs updated.
- This completes the chromatin context work (v6.10.1 wired it, v6.10.2 cross-cell weak, v6.10.3 cell-type-matched
  validated moderate, v6.10.4 incremental tested, annotation-only). Nothing about chromatin remains open or
  undisclosed.

## [6.10.3] - 2026-06-20 - Chromatin context: cell-type-matched validation (validated, moderate)

This patch settles the chromatin test. v6.10.2's controlled experiment was ambiguous (GUIDE-seq positive, TTISS
reversed) on a cross-cell-type K562 proxy; v6.10.3 re-runs it with a cell-type-matched track.

### Added / changed
- **Cell-type-matched validation** (`scripts/offtarget_chromatin_matched.py`; result in
  `benchmarks/offtarget/chromatin_validation.json` phase2). Downloaded the matched ENCODE HEK293T DNase-seq track
  (`ENCFF529BOG`; HEK293T matches GUIDE-seq's HEK293 and TTISS's HEK293T), queried it at each off-target's 1 kb bin
  (pyBigWig), and recomputed the AUROC. Cell-type matching lifts the canonical WT-Cas9 cell-based assay GUIDE-seq
  from AUROC 0.58 (cross-cell K562) to 0.671 (matched, CI [0.642, 0.701]); the in-vitro negative control stays null
  (0.494). The cross-cell proxy was dampening a real effect.
- Verdict: chromatin is validated (moderate, cell-type-matched) for WT-Cas9 cell-based off-target activity
  (`offtarget_data.CHROMATIN_VALIDATION` now `validated=True`, `effect="moderate"`). The caveats, all in-code and
  in the docs: the effect is moderate (the sequence/CRISOT score still dominates nomination); it does not
  transfer to TTISS (0.383, the expected outlier, a Cas9-variant specificity assay driven by variant fidelity, not
  WT chromatin); and chromatin is still surfaced as a validated annotation that does not yet change the numeric
  risk score (a calibrated CRISOT+accessibility combination is the remaining, deferred refinement).
- Reclassified the chromatin axis from "weak/inconsistent" to "validated (moderate, cell-type-matched)" with the
  matched evidence and the caveats.

## [6.10.2] - 2026-06-20 - Chromatin context: controlled validation (weak/inconsistent result)

This patch validates the chromatin axis, then scopes it to what the data supports. v6.10.1 wired a real
Stage B accessibility read but had not demonstrated it carries signal. v6.10.2 runs a controlled experiment and
reports the result: it is not a clean win.

### Added
- **A controlled chromatin validation** (`benchmarks/offtarget/chromatin_validation.json`,
  `scripts/offtarget_chromatin_validation.py`). Off-target protospacers mapped to hg38 (GRCh38.fa, exact match both
  strands, 98.5% mapped); AUROC of the Stage B K562 ATAC/DNase accessibility for active-vs-inactive off-targets per
  assay, with in-vitro assays as a negative control (cell-free, so no chromatin). Result: the in-vitro controls hug
  0.5 (method sound, no spurious signal); the canonical cell-based assay GUIDE-seq is a textbook modest positive
  (AUROC 0.58, CI [0.550, 0.613]) even with a cross-cell-type K562 proxy; but the second cell-based assay TTISS
  reverses (0.346). Verdict: weak and inconsistent, chromatin is not a validated quantitative axis on this data
  (the cross-cell-type proxy is the likely cause; a cell-type-matched accessibility track would settle it, deferred).

### Changed
- The chromatin-accessibility modifier is now an explicit annotation only, labelled `validated=false`: it reads
  the real Stage B track (or a caller-supplied scalar) and notes the qualitative Lazzarotto-2020 direction, but it
  does not change the numeric off-target risk score. `offtarget_data.CHROMATIN_VALIDATION` carries the result.
- Corrected the v6.10.1 entry that had marked chromatin "FIXED"; that was too strong. It is now recorded as
  tested, weak/inconsistent, documented annotation, not a validated axis.

This is a negative result reported in full.

## [6.10.1] - 2026-06-20 - Off-target rigor pass and retroactive audit (v6.7-v6.9)

This patch completes the Stage E plan and documents every remaining deviation. It closes the v6.10.0 gaps and
re-audits v6.7/v6.8/v6.9 (plan vs shipped vs code) and corrects the findings. No item is reported complete if it
is a silent substitution, partial, or deferral.

### Added / changed (Stage E completion)
- **Off-Target-Bench expanded to four unbiased assays.** Added CHANGE-seq (Lazzarotto 2020, `10.1038/s41587-020-0555-7`)
  and SITE-seq (Cameron 2017, `10.1038/nmeth.4284`) on independent broad guide panels (20 and 11 guides). The real
  CRISOT-Score (MD-physics, assay-agnostic so leakage-clean) beats the homology baseline on all four:
  AUPRC 0.646/0.520/0.541/0.521 vs 0.467/0.266/0.249/0.233; per-guide bootstrap CI excludes 0 on each.
- **Chromatin wired to the real Stage B track and relabelled.** `locus_accessibility(chrom, bin, ct)` reads
  `phase_1/features/chromatin_{ct}.parquet` (ATAC/DNase) when present and abstains otherwise; the docs now say
  "chromatin-accessibility modifier" (not "chromatin-aware engine"), since the bare wheel and the deployed atlas do not ship the
  raw track, so the modifier is inactive there.
- **Off-target task added to the Genome-Writing Challenge** (`benchmarks/genome_writing_challenge/harness.py`):
  non-circular (label = wet-lab Active call), data-gated on the fixture; the reference solver nominates correctly.
- **Substitutions:** CRISOT is used instead of the plan-named CCLMoff/CRISMER (CRISMER ships no license;
  CCLMoff is GPU and trained on these assays, so it leaks; CRISOT is the leakage-clean, license-clean, CPU choice). A
  genomic-coordinate locus split is not possible (harmonized data is coordinate-free), so held-out-guide and cross-assay are used.

### Fixed (retroactive audit)
- **v6.9:** dropped the inaccurate "OOD-gated" claim in the MHC-II axis status (it is coverage-gated, abstains
  when uncached, with no distributional OOD gate); corrected the stale `AXIS_STATUS["mhc2_writer"].reason` and the
  `immune_mhc2.py` module docstring (they still described the dropped v6.9.0 P1-anchor proxy as "the method"; the
  production axis is the real NetMHCIIpan-4.0). The plan-named MHC-II tool ensemble and the IEDB/ImmunoSeq/FVIII
  ADA datasets were not used (single-tool NetMHCIIpan-4.0; the recovery bench is a 4-protein sanity check, not an
  IEDB held-out leaderboard); the 6.9.1 to 6.9.2 MHC-II metric changed from peptide-fraction to residue-coverage.
- **v6.8:** v6.8.0's attB was a poly-G/C schematic (replaced with the real Bxb1 attB in v6.9.2);
  inter-curator agreement is N/A (single contributor); "at least 1 external submission" is unmet (forward-looking).
- **v6.7:** corrected the "chromosome-Mondrian" served-interval wording (per-chromosome Mondrian qhats are computed,
  but the global qhat is served, which is correct since a query has no chromosome at serve time); recorded the prereg
  consolidation and the deferred HEK293T-OOD demo / scope-manifest entry.

## [6.10.0] - 2026-06-20 - Cross-writer-family off-target nomination

Off-target moves from a single-family bridge pseudosite scan to a cross-writer-family,
chromatin-aware nomination engine grounded in unbiased genome-wide assays, completing the safety triad
(site B, writer C, off-target E). Nomination is framed as not a clearance: every candidate
ships with the empirical assay that would confirm it.

### Added
- **Off-Target-Bench** (`benchmarks/offtarget/`): a real, leakage-controlled nomination benchmark over canonical
  Cas9 guides (EMX1/VEGFA1-3/FANCF/HEK293) with experimentally validated off-targets from GUIDE-seq
  (Tsai 2015, `10.1038/nbt.3117`) and CIRCLE-seq (Tsai 2017, `10.1038/nmeth.4278`). Held-out-guide split, per-assay
  provenance, SHA256SUMS. On real data with a real tool, the licensed CRISOT-Score predictor
  (Chen et al., Nat Commun 2023, `10.1038/s41467-023-42695-4`; XGBoost RNA-DNA fingerprint) beats the sequence-
  homology baseline: GUIDE-seq AUPRC 0.646 vs 0.467 (gap +0.179, CI [0.015, 0.340]); CIRCLE-seq 0.520 vs
  0.266 (gap +0.253, CI [0.140, 0.361]); per-guide bootstrap CI excludes 0 on both assays.
- `pen_stack/wgenome/offtarget_data.py`: validated assay/predictor provenance, a grounded mismatch-to-active-fraction
  risk calibration (real-data: GUIDE-seq 0-1mm to 100% active, 2mm to 76%, 3mm to 23%, 4mm to 3.3%), the bench fixture loader.
- `pen_stack/wgenome/offtarget_predict.py`: `nominate_offtargets(writer_family, ...)`. Nuclease (mismatch-
  calibrated risk band plus the real cached CRISOT score plus a documented chromatin modifier, Lazzarotto 2020);
  serine integrase (cryptic pseudo-attB scan on the real documented Bxb1 attB core GCGGTCTC/GT);
  bridge (delegates to the existing Perry-DMS pseudosite engine). Abstains without inputs; never fabricates sites.
- `pen_stack/wgenome/offtarget_assay.py`: validation-assay recommender (GUIDE/CHANGE/CIRCLE-seq for nucleases;
  Cryptic-seq/HIDE-seq for integrases; a documented gap for bridge recombinases, since no published genome-wide
  unbiased off-target assay or predictor exists, verified).
- **Surfaces:** REST `POST /offtarget` and `GET /offtarget/assay`; MCP `offtarget_scan`; manifest `nominate_offtargets`
  (fabricates=False); an `offtarget_nomination` scope card; and a web Off-Target page.

### Limitations
- Nomination is not a clearance; genome-wide candidate enumeration needs the on-VM Cas-OFFinder/genome scan (this
  engine scores, ranks, and risk-bands supplied candidates). The CRISOT predictor is CC-BY-NC: it runs only on the
  VM and its weights are never redistributed; only derived scores are cached (CI-safe). Bridge/integrase off-target
  is data-thin and unmodeled and is flagged extrapolative; IntQuery (Tome Biosciences) is a paper-only reference.

## [6.9.2] - 2026-06-19 - Real-tool rigor pass across the immune and writer axes (no proxies, no heuristics)

A top-to-bottom audit replaces every remaining proxy/heuristic in the immune and writer-design stack with
the real on-VM tool (gold-standard, licensed) or an abstention. No silent fallbacks. All licensed binaries stay on
the VM; only derived numbers are cached.

### Changed
- **MHC-I capsid axis re-grounded on NetMHCpan-4.1** (`pen_stack/planner/capsid_epitope_oracle.py`). The primary
  capsid CD8 predictor is now the gold-standard licensed NetMHCpan-4.1 (%Rank_EL<=0.5, residue coverage, 12-allele
  panel; `configs/mhc_epitope_oracle.yaml` `mhc1`); the v5.3 MHCflurry value is kept as an explicit, reported
  cross-check (never silently substituted). Both agree AAV is the least CD8-immunogenic capsid
  (AAV `capsid_immune_score` 0.4585 NetMHCpan / 0.2803 MHCflurry; the predictor disagreement is surfaced, not hidden).
- **ADA-risk re-grounded** (`pen_stack/planner/ada_risk.py`). `ada_risk = real NetMHCIIpan-4.0 density x foreignness`,
  where foreignness is the protein origin (the authoritative central-tolerance signal). Unknown origin or uncached
  density now abstains (no k-mer guess, no heuristic), replacing the v6.9.0 albumin-only self-tolerance
  heuristic. The real human-proteome 9-mer self-match (computed on the VM over the full UniProt reference
  proteome, 20,431 proteins / 10.4 M 9-mers) is reported as a cross-check: human albumin 1.0 (self), the
  foreign writers (SpCas9/ISCro4/Bxb1) and capsids 0.0 (non-self), a clean self/non-self separation.
- **MHC-II axis no longer falls back to a production proxy** (`pen_stack/planner/immune_mhc2.py`). `mhc2_epitope_load`
  uses the real NetMHCIIpan-4.0 cache by antigen name and otherwise abstains; the documented promiscuous-binder
  estimate is retained as `mhc2_proxy_estimate` for offline triage only (explicitly labelled, not the production axis).
- **Real Bxb1 attB written** (`pen_stack/atlas/guide_design.py`). The PASTE/PASSIGE pegRNA 3' extension now writes the
  real documented Bxb1 minimal attB verbatim (FlyBase FBto0000359; Ghosh, Kim & Hatfull, Mol Cell 2003;
  8-bp common core GCGGTCTC around the central GT crossover) instead of the schematic poly-G/poly-C arms. Integrases
  without a bundled documented site expose only the central core (never a fabricated full sequence).
- `pen_stack/planner/immune_profile.py`: the writer-as-antigen card surfaces `foreignness`, the real
  `self_match_human_proteome` cross-check, and the MHC-II/ADA backends (this replaces the removed `self_tolerance` field).

### Deviations from the v6.9 pre-registration (`prereg/ws_immune2.yaml`)
- The pre-registered "1 - self_match_fraction from a human-proteome k-mer filter" foreignness fallback is
  dropped: foreignness is the authoritative origin, and an unknown origin abstains rather than imputing from a
  k-mer match (the real self-match is reported only as a cross-check). This is a stricter rule.

### Data / tests
- `configs/mhc_epitope_oracle.yaml`: corrected `self_match` (the v6.9.x cache had a FASTA-keying bug that collapsed
  the 20,431-protein proteome to 1 protein, zeroing every self-match including albumin); recomputed correctly on the VM.
- `tests/unit/{test_ws_immune2,test_ws_epitope,test_ws_writer,test_ws_rel}.py` updated for the abstain semantics,
  the NetMHCpan-4.1 primary capsid value plus MHCflurry cross-check, the real attB, and the 6.9.2 version pins.

## [6.9.1] - 2026-06-20 - Real NetMHCIIpan-4.0 / NetMHCpan-4.1 MHC epitope load (replaces the v6.9.0 proxy)

This patch is a rigour upgrade. v6.9.0's MHC-II axis was a documented heuristic proxy (P1-anchor density). The
gold-standard licensed predictors were already on the VM, so v6.9.1 computes the MHC-II epitope load with real
NetMHCIIpan-4.0 (and MHC-I with NetMHCpan-4.1) over a frequent HLA panel, and re-grounds the axis on the real
values. The licensed binaries are never committed or distributed; only the derived fractions are
cached (`configs/mhc_epitope_oracle.yaml`), exactly like the v5.3 MHCflurry cache.

### Changed
- `pen_stack/planner/immune_mhc2.py`: `mhc2_epitope_load(seq, name)` now uses the real NetMHCIIpan-4.0 EL
  %Rank<=2 cache (over 7 frequent HLA-II alleles) when the antigen is cached; the documented promiscuous-binder
  proxy remains only as the offline/CI fallback for uncached sequences. `real_mhc2_load(name)` exposes the cache.
- `ada_risk`, `immune_profile` (writer-as-antigen), and `benchmarks/immuno` thread the antigen name to real values.
- `configs/mhc_epitope_oracle.yaml` (committed): derived epitope fractions for the writer and capsid antigens.

### Result (the real tool is more discriminating than the proxy)
- Real NetMHCIIpan-4.0 strong-binder fraction: SpCas9 0.153, Bxb1 0.152, ISCro4 0.112, AAV2 0.114 vs
  human albumin (self) 0.066, the lowest. The gold-standard tool shows the self protein has a genuinely lower
  MHC-II load and the foreign writers higher, a signal the heuristic proxy flattened (~0.08-0.10 for all). The
  immunogenic-vs-tolerated recovery is unchanged (foreign well above self) but now on real predictions.

### How it ran (no host install; per the VM Docker rule)
- `penmhc:tools` (debian + tcsh + gawk + perl) with `~/netmhc` (the licensed tools) mounted, NMHOME fixed at
  runtime; `scratch/v691_mhc_compute.py` runs both predictors and writes the derived cache. The axis stays a
  population-level proxy (frequent-HLA panel, not a patient-HLA magnitude, a known-unknown).

## [6.9.0] - 2026-06-20 - Immune profile: MHC-II/CD4, ADA, and writer-as-antigen

This minor feature release extends the immune profile from CD8/MHC-I-only to a full T-cell profile: MHC-I plus
MHC-II/CD4 plus ADA risk with self-tolerance filtering, scored over the writer enzyme as a distinct antigen,
still population-level, OOD-gated, and never collapsed. It wraps the v5.6 unified profile. No fabrication: real
UniProt sequences, a grounded documented method, proxy-labelled axes.

### Added: the MHC-II and ADA axes
- `pen_stack/planner/immune_mhc2.py`: a grounded, dependency-free promiscuous MHC-II binder density (documented
  P1 hydrophobic anchor, Stern & Wiley 1994; secondary pockets, Southwood 1998) over capsid and writer sequences plus
  the bundled real writer/control FASTA. `configs/writer_sequences.fasta`: real UniProt for SpCas9 (Q99ZW2), ISCro4
  bridge recombinase (D2TGM5), Bxb1 integrase (Q9B086), human albumin self control (P02768).
- `pen_stack/planner/ada_risk.py`: ADA-risk = MHC-II epitope density x foreignness with a JanusMatrix-style
  self-tolerance filter (origin authoritative; human-proteome k-mer filter otherwise). It recovers
  immunogenic-vs-tolerated: foreign writers score above the human self control (clean separation).

### Changed: the unified profile
- `pen_stack/planner/immune_profile.py`: adds `mhc2_writer` and `ada_writer` axes and a `writer_as_antigen` card
  with `dominant_antigen` and `writer_dominant_risk` (which fires for a foreign writer, especially non-viral delivery
  where there is no capsid antigen). `collapsed_score` stays `None` (asserted). `immune_calibration.AXIS_STATUS`
  registers the two new axes as mechanistic/population proxies.

### Added: Immuno-Bench and calibration
- `benchmarks/immuno/harness.py`: the immunogenic-vs-tolerated recovery track (non-circular: label = protein
  origin) plus a `calibrate_axis` ADA pass that remains a proxy at public-data power (no manufactured validation).
- `tests/unit/test_ws_immune2.py` (CI-safe; pure-Python method plus committed sequences). `prereg/ws_immune2.yaml`.

### Limitations
- Every axis is a population-level proxy, never a patient-specific ADA titer or realized CD4 magnitude (known-
  unknowns). The MHC-II method is sequence-intrinsic presentation potential, not a trained allele-specific predictor.
  The self-tolerance k-mer filter is seeded by the bundled human reference (the full human proteome is substitutable on the
  VM); the authoritative foreignness signal is the protein origin. Axes are a vector, never fused.

## [6.8.0] - 2026-06-20 - Cross-family writer-efficiency engine and Writer-Efficiency Bench

This minor feature release upgrades Stage C (pick the writer) from a curated-KB ranking to a prediction plus
design layer: the first curated writer-efficiency benchmark, a learned cross-family efficiency predictor,
integrated guide/att design, and serine-integrase variant critique. It wraps the Writer Atlas and v4.0 writer-verification.
No fabrication: every efficiency is a real published number with a DOI and a verbatim quote.

### Added: the curated dataset and benchmark
- `pen_stack/atlas/writer_efficiency.py` plus `data/writer_efficiency.parquet` (SHA-locked): ~45 records / 9 DOIs /
  4 families, each row with a DOI, a verbatim quote, and a source-access grade (39 pmc_verbatim, 1 abstract, 5 secondary).
  Sources: PASTE (Yarnall *Nat Biotechnol* 2023), (ee)PASSIGE (Pandey/Liu *Nat Biomed Eng* 2025), hyperactive
  integrases (Hew *Nucleic Acids Res* 2024 e64), evoCAST (*Science* 2025), ShCAST (*Science* 2019), enIS621
  (*Nat Commun* 2026), ISCro4 (*Science*).
- `benchmarks/writer_efficiency/`: the Writer-Efficiency Bench, a sealed, SHA-locked held-out-family plus
  held-out-locus track set plus a baseline leaderboard plus a submission harness. `docs/cards/writer_efficiency_data.md`.

### Added: the learned predictor and the gate
- `pen_stack/atlas/writer_predict.py`: interpretable-feature HistGradientBoosting plus a family-blocked split-conformal
  interval, candidate-flagged. The pre-registered gate: it beats the KB family-mean baseline on held-out
  locus (MAE 11.7 vs 15.2, paired-bootstrap CI excludes 0; rho +0.38 vs -0.26) and ranks families better on
  held-out family (rho +0.52 vs -0.20), but the held-out-family MAE gain is not significant at N=42/4-families, so
  the KB ranking is retained as primary, the predictor ships candidate-flagged, and the dataset plus bench are the
  contribution. The negative is reported.

### Added: guide design and variant critique
- `pen_stack/atlas/guide_design.py`: bridge-RNA TBL/DBL loops (Durrant 2024), pegRNA+attB (Yarnall 2023; Bxb1
  core GT), orthogonal att-pair selection (Roelle 2023 GA/GT), with round-trip and invariant recovery tests.
- `pen_stack/design/writer_variants.py`: extends v4.0 writer-verification to serine-integrase hyperactive mutants
  (Hew 2024 / Keravala 2009); recovers Bxb1 `c22` and PhiC31 P2/P3 retrospectively; defers the
  LM-vs-conservation blind claim (LM naturalness is not engineered hyperactivity).

### Added: the recommender surface
- `pen_stack/atlas/writer_recommend.py` plus manifest tool `recommend_writers`: ranks families (KB-grounded primary)
  plus candidate predicted efficiency with a conformal interval plus an auto-designed guide. Efficiency is never extrapolated
  to a family absent from the dataset (KB-only there).

### Limitations
- Predicted efficiencies are candidates with intervals, never asserted activity. 4 families is the binding
  statistical limit, reported. Range efficiencies stored as midpoints (raw string retained);
  secondary-source rows flagged and droppable (strict subset).

## [6.7.0] - 2026-06-19 - Learned, trained-conformal Stage H and TPE-Bench

This minor feature release upgrades the digital twin's Stage H expression/outcome layer from a validation-failing
closed-form heuristic to a learned, trained-conformal, decomposable position-effect model, and ships the
held-out benchmark the expression capability never had. Wrap, don't rebuild: it extends `twin`, `wgenome.uncertainty`,
`wgenome.ood`, and `benchmarks`. No fabrication: every metric is from a real CV run on real TRIP supervision, and
the cross-cell-type transfer claim is data-gated, never faked.

### Added: the learned model and trained conformal
- `pen_stack/twin/data/position_effect.py`: a unified position-effect schema plus a dataset registry with verified
  accessions/DOIs (TRIP live; PatchMPRA/MPIRE/lentiMPRA/Leemans registered and recorded `available=False` until
  fetched), z-normalization within (dataset x cassette), domain-blocked plus held-out-cell-type splits, a leakage check.
- `pen_stack/twin/position_effect.py`: `PositionEffectModel` (factored `f_cassette` plus `g_context`, LightGBM),
  `evaluate()` (chromosome-blocked CV vs the v3.x durability head plus cassette-only, paired-bootstrap CIs,
  separability), split-conformal calibration (`ConformalRegressor`, chromosome-Mondrian, OOD-widened),
  `predict_stage_h()` serving seam. Result (real TRIP): expression rho 0.428 to 0.469 (CI excludes 0);
  held-out conformal coverage 0.885 vs 0.90 nominal.
- `configs/twin/position_effect_conformal.json`: the shipped calibration (qhat plus N plus held-out coverage).
- `scripts/p1_build_position_effect.py`: regenerates the model plus conformal artifacts (real CV report).

### Changed: Stage H integration
- `pen_stack/twin/outcome.py`: when a chromatin context is supplied and the artifact is present, `predict_outcome`
  serves the learned trained-conformal interval plus `p_silenced` plus an OOD tier (`position_effect` block,
  `stage_h_mode`); with no context/artifact it falls back to the heuristic band, backward compatible (the
  v5.9 relative-scale contract is intact).

### Added: TPE-Bench and controls
- `benchmarks/position_effect/`: TPE-Bench, a sealed, SHA-locked held-out-chromosome track plus a baseline
  leaderboard (cassette-only / durability head / factored). The leave-one-cell-type-out
  transfer track is scaffolded and data-gated (no fabricated transfer number).
- `pen_stack/validate/{expr_controls,known_biology_expr,heldout_celltype_expr}.py`: a label-shuffle-to-chance control,
  an H3K9me3-heterochromatin-to-silencing recovery, and the data-gated transfer harness.
- `tests/unit/test_ws_pe.py`: CI-safe (synthetic planted signal); the real-TRIP claim runs on a checkout, skips in CI.

### Limitations
- Public data cannot flip expression to outcome-validated (the v6.5 wall); v6.7 ships the learned and calibrated
  upgrade plus the benchmark plus the data-gating, not a manufactured result. Cross-cell-type transfer needs the additional
  human datasets (a data-acquisition step), reported as such. Wet-lab validation omitted by scope.

## [6.6.0] - 2026-06-16 - License-clean provenance (COSMIC to CancerMine)

This minor release is a provenance refactor: no new science, no capability lost. The shipped artifact now sources the
oncogene/TSG/driver list from CancerMine (CC0) instead of COSMIC Cancer Gene Census (free for academia but
no-redistribution). Copyright protects the compiled database, not the fact that a gene is an oncogene, so
sourcing the list from a CC0 compilation removes all licensing doubt while keeping the same capability. This is prep for
the BioFirewall release, whose open repo vendors PEN-STACK's hazard data.

### Changed
- `pen_stack/data/ingest_safety_annot.py`: `load_cancermine()` (CC0) is the default oncogene/TSG source
  (HUGO to coords via GENCODE, `--min-citations` precision knob); `load_cosmic()` stays available but off by
  default (bring-your-own-license, local enrichment only).
- `configs/genotoxicity_oracle.yaml`: regenerated from CancerMine; provenance and DOIs updated (CancerMine
  10.1038/s41592-019-0422-y). `safety_{ct}.pkl` plus the Writable-Genome atlas regenerated on CancerMine features
  (re-deposited on Zenodo, superseding the COSMIC-derived deposit).

### Added
- **`DATA_LICENSES.md`**: every source by license by redistribution-status by where-used.
- `tests/unit/test_data_licenses.py`: a CI license gate that fails if a restricted source (COSMIC/OncoKB) is the
  shipped derived-data source or a raw restricted gene-list is committed; CancerMine is the default.
- `scripts/fetch_licensed_sources.py`: a bring-your-own-license fetcher for COSMIC/OncoKB (local-only, validation).

### Notes
- Metrics may shift (CancerMine has broader coverage than CGC), reported. The genotoxicity axis is a
  mechanism-grounded proxy (not outcome-validated) before and after; the swap changes only the source.

## [6.5.0] - 2026-06-15 - Comprehensive expression model and proxy-validation pass

This minor feature release has two threads, one principle (no fabrication):

### Added: a comprehensive, literature-cited expression model
- `configs/expression/promoters.yaml`: the twin's promoter palette expands from 5 to 31 promoters (constitutive plus
  tissue-specific: liver TBG/LP1/hAAT, neuron hSyn/CaMKIIa, muscle MHCK7/MCK/CK8, astrocyte GfaABC1D, SFFV/MND/
  MSCV/RSV, and more). Each entry carries `strength` plus context plus assay plus citation plus confidence, because promoter
  strength has no universal scalar (it depends on cell type by vector by readout), so a single number is encoded
  with its context, never as a universal truth.
- `configs/expression/modifiers.yaml`: a modifier layer (WPRE, intron, polyA, Kozak, codon-optimization/CAI,
  CpG-silencing) as literature priors/ranges, applied as a bounded uplift range (never a point multiplier, since
  the chimeric intron is ~20x for one transgene, ~3x for another). `twin/mechanistic.py` consumes both.

### Added: a proxy-to-outcome validation harness
- `scripts/calibrate_immune_axes.py` plus `configs/calibration/preexisting_nab_independent.yaml`: runs the existing
  `calibrate_axis` gate (N>=6 AND bootstrap Spearman CI excludes 0) against independent measured data.

### Result (the deliverable)
- No immune or expression axis flips to outcome-validated. Pre-existing NAb tested vs an independent cohort
  (Navarro-Oliveros 2024, Basque): rho=0.12, CI includes 0, geography-dependent. Relative-expression tested vs an
  independent promoter study (Damdindorj 2014): rho=0.12, CI includes 0, promoter strength is context-dependent
  (Damdindorj found CMV strongest; Qin found the opposite). Genotoxicity (3 vectors), CD8 (5 capsids), anti-PEG
  (1), and innate (0 fixed) are structurally below the N>=6 gate. The labels stay proxy with empirical backing;
  flipping them would require measured-outcome data at a statistical power the public literature does not provide.

### Tests
- `tests/unit/test_ws_express.py`: the palette is comprehensive and cited; context is encoded; the modifier profile is a
  bounded range; the proxy does not falsely claim cross-study validation (the no-fabrication gate holds).

## [6.4.3] - 2026-06-12 - Chat vehicle-parse fix (AAVS1 no longer hijacks the vehicle)

This patch fixes a parsing bug. `web/tools.py::parse_goal` matched the delivery vehicle by substring, so the safe-harbour nickname
AAVS1 (which contains "aav") wrongly selected the AAV vehicle even when the user said lentivirus or
LNP, producing the wrong immune profile (e.g. genotoxicity 1.0 instead of lentivirus's 0.481). Fix: strip the
safe-harbour nicknames (AAVS1/H11/HIPP11/ROSA26) from the vehicle-search text before matching, so the user's
stated vehicle wins. Explicit "AAV" still selects AAV. A new test locks all three cases.

## [6.4.2] - 2026-06-12 - Co-Scientist chat: real writer recommendations and self-explanatory values

This patch fixes a stale/confusing chat experience reported from the live app. Three problems, three fixes:

1. **The chat dossier was generic and barely changed per query.** `web/tools.py::parse_goal` hardcoded
   `chrom="chr19"` (so a goal about ITGB2, chr21, was mis-located) and `run_tools` never called the planner,
   so a "which writer can integrate N kb in GENE" question got a vehicle-keyed immune profile but no named
   writer. Fix: `parse_goal` now resolves the gene's real chromosome (`planner.gene_region`, atlas-gated,
   falls back offline), and `run_tools` runs the planner and attaches a `plan` block: the recommended writer
   family, top site, safety/durability/score, cargo-capacity fit, and delivery, all engine-computed. It says so
   when the gene isn't in the atlas ("not found, check the HGNC symbol"); never fabricated.
2. **The LLM narration produced `[unverified]` spam.** With no writer in the tool results, the model invented
   one (`AAV9-CRISPR` plus made-up numbers) and the grounding guard struck them all. Fix: the system prompt now
   forbids inventing a writer/vehicle/table/number, and if the guard still strikes 2 or more numbers the reply falls
   back to the fully-grounded deterministic narration, so the spam never reaches the user.
3. **Values and the "extrapolating" badge weren't self-explanatory.** Each immune axis now carries a
   plain-language `meaning` ("0.55 on a 0-1 scale, moderate; higher = fewer patients excluded; this is a
   proxy, not validated against a measured outcome"), the deterministic narration uses it, and
   `ImmuneProfileCard` renders it plus a one-line legend explaining that "extrapolating" means a proxy estimate.

### Added
- `tests/unit/test_ws_chat.py`: chrom resolution, axis-meaning, real writer plan, and the no-`[unverified]`-spam
  fallback are locked by new tests.

## [6.4.1] - 2026-06-12 - Defence-in-depth: pre-route safety screen

This patch closes a screening gap. The grounded co-scientist chat ran the Guardian (biosecurity gate) only in the design lane (via
`run_tools`); a hazardous request with no design signal (no vehicle/locus) routed to `general`/`explain`/`meta`
and was never screened. Fix: `pen_stack/web/llm.py::_pre_route_safety` runs the Guardian, framing-stripped, the
authority on the decision, at the top of `grounded_reply()`, before lane routing. A `refuse`/`escalate`
verdict short-circuits to a clear decline (`mode="safety"`, with the decision in `tool_results`). Benign
hazard-adjacent biology (vaccines, generic pathogen questions) is not blocked: the Guardian clears it and
routing continues. A broad regex only decides whether to invoke the Guardian; a false trigger is harmless.

### Added
- `tests/unit/test_ws_chat.py`: `test_pre_route_safety_screens_a_hazardous_general_query` and
  `test_pre_route_safety_does_not_over_refuse_benign_questions` lock both sides of the screen.

## [6.4.0] - 2026-06-12 - Live Oracles (the foundation models actually execute)

The oracle mesh goes live. The foundation-model adapters that were deferred contracts now run real backends,
without touching the no-fabrication invariant (generated outputs stay candidates, OOD inputs are flagged, a down
backend defers). Live execution is opt-in via `PEN_STACK_ORACLE_NET=1`; with the flag unset (CI/offline) every
oracle behaves exactly as before. This is a minor feature release on the stable 6.x API.

### Added: live oracles
- **Evo2-40B (hosted):** `oracles/genome.py::generate_dna` calls NVIDIA's hosted Evo2-40B (real generated DNA plus
  per-token probability). ~1-3 s.
- **AlphaGenome (hosted):** `oracles/genome.py::variant_effect` connected to the existing v3.1
  `wgenome.AlphaGenomeProvider` (added `score_variant`; no duplicate client), a real regulatory variant-effect
  magnitude. ~2-10 s. (AlphaGenome already ran live in v3.1 for expression/tracks/contact, 416 cached predictions.)
- **ProteinMPNN / ESM3-open / RFdiffusion (local GPU):** `model_servers/{proteinmpnn,esm3,rfdiffusion}` small
  FastAPI servers on the VM GPU (reuse `penstack:phase1.5` / `rfdiffusion:base`); `oracles/protein_design.py`
  HTTP-calls them. ProteinMPNN ~1-9 s, ESM3 ~1-2 s warm, RFdiffusion ~1-2 min. `docker-compose.models.yml` starts
  them on demand.
- **Execution and latency surface:** `configs/oracles/execution.yaml` plus `oracles/status.py` (`oracle_status`,
  `summary`) plus `GET /oracles` plus the chat meta facts: per-oracle execution, latency class
  (instant/seconds/slow/long_job), and live status, so the assistant states the cost before running anything.

### Held / deferred
- **AlphaFold3, Boltz-2, Chai-1, Protenix:** held, they need a rented A100/H100 (24-80 GB; AF3 also ~1 TB
  databases). They run separately on cloud, never on the 16 GB VM and never in the request path.
- **Arc STATE / scGPT:** the package is verified installable (`pip install arc-state`; SE-600M embeds cells), but a
  trustworthy perturbation outcome needs the State-Transition model plus a reference scRNA pipeline, and even
  SOTA doesn't beat naive baselines (Arc VCC), so the magnitude stays a known-unknown, deferred
  (a uniform gated hook is added via `PEN_STACK_VCELL_URL` for when an ST server is stood up).

### Verified on the VM (RTX A4000)
Evo2-40B generation ~1.2 s; AlphaGenome variant score `chr22:36201698 A>C` max|effect| 3.15 over 14,652 tracks
in 3.6 s; ProteinMPNN designed real ubiquitin-fold sequences (global_score ~0.80) in ~9 s; ESM3-open completed the
ubiquitin sequence from a partial prompt in 1.4 s warm; RFdiffusion diffused a real 60-residue backbone in ~105 s.
All generated outputs remain candidates (`as_claim()` raises).

## [6.3.1] - 2026-06-12 - Router fix: general "how does it work" no longer misrouted to the meta lane

This patch corrects routing. It was found by a full-stack test pass (every oracle plus every endpoint plus the 4
chat lanes plus general/biological-intelligence questions).

### Fixed
- **Router meta-lane over-capture.** A general-biology question phrased "and how does it work / cut DNA?"
  (e.g. *"what is CRISPR-Cas9 and how does it cut DNA?"*) matched the meta pattern `how (do|does) (you|it|this|pen)`
  and was answered from PEN-STACK capability facts instead of general knowledge. Narrowed the bare-pronoun meta
  trigger to `how (do|does) (you|pen)` so a general "how does it ..." routes to the general lane (labelled,
  with an engine pointer); a pen-stack-scoped "how do you compute X" stays meta (the verb-qualified pattern is
  unchanged). Regression cases added to `tests/unit/test_ws_chat.py::test_router_classifies_the_four_lanes`.

### Verified (v6.3 test pass)
- **Oracle mesh (42/42, engine-direct):** ViennaRNA computes a real MFE fold (-38.3 kcal/mol); AlphaGenome,
  Evo2, vcell (Arc-STATE), AF3/Boltz/Chai/Protenix, and RFdiffusion/ProteinMPNN/ESM3 either compute or defer
  with the OOD gate plus provenance intact, never fabricate; the generative-candidate `as_claim()` guard
  raises. Computed immune layers reproduce orderings from data: genotoxicity LV 0.481 < gammaretro 0.177
  (LMO2/SCID-X1), capsid AAV 0.28 > Ad 0.18, CpG O/E rich > poor, seroprevalence AAV 0.55 / Ad5 0.35, anti-PEG
  0.515; full `verify()` clears a clean design, rejects a 7 kb single-AAV (alt lentivirus legal), refuses ricin,
  rejects an RNP-over-AAV, and flags multiplex translocation risk 0.95.
- **App surface (live, LLM on):** every endpoint 200 plus a grounded shape; the 4 chat lanes route correctly with the
  grounding guard clean on the grounded lanes (0 ungrounded numbers, Nemotron backend).

## [6.3.0] - 2026-06-12 - The Hybrid Co-Scientist (grounded engine plus general intelligence)

The chat gains general and biological intelligence without loosening the no-fabrication core. A 4-lane router
keeps grounded engine output and general trained-knowledge in separate, explicitly-labelled lanes, so a
general-knowledge fact can never be mistaken for a PEN-STACK result. Numbers now come with their meaning,
reference range, and how they were computed; the conversation has memory. This is a minor feature release on the stable
6.x API, SHA-locked.

### Added
- A deterministic 4-lane chat surface: `pen_stack/web/router.py` (classifier: `design` / `explain` / `meta` /
  `general`, biased to the engine whenever a design signal is present) plus `pen_stack/web/guide.py`
  (`metric_guide()` interpretation cards plus `pen_stack_facts()` assembled from live engine data) plus a rewritten
  `pen_stack/web/llm.py::grounded_reply` that dispatches per lane and returns `{mode, provenance, grounded, ...}`.
- **`configs/metric_guide.yaml`:** grounded interpretation for every engine number (genotoxicity, CD8 epitope,
  innate, pre-existing NAb, anti-PEG, confidence, relative expression, and the safety decisions): what it means, the
  scale plus direction, reference bands, how it is computed, and its validation status. The chat now explains a value
  (scale / what's good-or-bad / reference range / method), not just prints it.
- **Lanes and provenance:** `design`/`explain`/`meta` are engine-grounded (the grounding guard runs over the tool
  results, the metric guide, or the live facts); `general` answers from the LLM's trained knowledge, is labelled
  "General knowledge, not PEN-STACK-verified", attributes no number to PEN-STACK, and points to the engine
  wherever PEN-STACK could compute a concrete answer (`pen_stack_angles`).
- **Conversation memory:** the last turns are passed to every lane so follow-ups ("what does that 0.55 mean?")
  resolve against the prior dossier; the frontend keeps history in-session until refresh and renders a per-message
  provenance badge (grounded vs general) plus the "PEN-STACK can compute this" pointers.
- Tests: `tests/unit/test_ws_chat.py` covers the 4-lane router, the general lane labelled/unattributed/pointered, the
  meta lane grounded in live facts, the explain lane interpreting prior values without a fresh design, the metric
  guide complete. Preregistration `ws_hybrid` plus SHA lock; deposit `phase_6.3/`.

### Notes
- The core is untouched. The guard still runs on every PEN-STACK-attributed number; we added a general lane,
  we did not loosen the grounded lane. The cost is that general-lane answers carry the LLM's fallibility,
  made safe by the explicit label and by redirecting to the engine for anything computable.

## [6.2.4] - 2026-06-12 - Faster grounded narration (LLM backends) (patch)

Performance plus a real fix, from benchmarking the narration backends on the deployment GPU (RTX A4000). The
LLM only narrates over engine tool results (the grounding guard runs regardless), so latency is the thing to
tune. Measured (real grounded prompt): Ollama qwen2.5:7b = ~50s warm / 120s cold (3.4 tok/s, a workstation
GPU is slow for an LLM); qwen2.5:3b = ~27s; llama3.2:3b = ~17s; hosted Nemotron-49B = ~5s. All keep the
grounding guard clean (0 ungrounded). The old Nemotron fallback model (`llama-3.1-nemotron-70b-instruct`) now
404s, i.e. the fallback was silently broken.

### Fixed / changed (`pen_stack/web/llm.py`)
- **Nemotron model corrected** to `nvidia/llama-3.3-nemotron-super-49b-v1` (the 70B name was retired, so the
  fallback 404'd). Restores a working, ~5s hosted backend.
- **Default local model qwen2.5:7b to qwen2.5:3b-instruct** (~2x faster narration, grounding unchanged).
- **`keep_alive` (default 30m)** so the model stays resident on the GPU and idle calls don't pay the cold start.
- **Configurable backend order** `PEN_STACK_LLM_ORDER` (default `ollama,nemotron` = local/private-first;
  `nemotron,ollama` = speed-first ~5s). `web/.env.example` documents all knobs.

## [6.2.3] - 2026-06-12 - Scope matcher covers functional titer and durability (patch)

A coverage fix (from the 20-query acceptance suite, `phase_6.2/PEN-STACK_ACCEPTANCE_TESTS.md`). The
known-unknowns matcher (`configs/known_unknowns.yaml`) had no entry for functional titer / absolute in-vivo
expression magnitude and its durability terms were too narrow ("how long will it last in a patient"), so
common measured-endpoint questions ("what functional titer (% of normal)?", "how long will episomal AAV
expression last?") were not explicitly deferred. The no-fabrication spine already held (no titer/half-life was
ever emitted, and the immune profile lists `patient_specific_titer`), but the matcher should flag these
proactively.

### Added / Fixed
- `configs/known_unknowns.yaml`: a new known-unknown `in_vivo_expression_magnitude` (functional titer / % of normal
  / absolute expression, a measured clinical endpoint, never predicted; PEN-STACK gives the relative mechanistic
  proxy plus immune context); broadened `long_term_clinical_durability` match-terms/patterns to catch "how long will
  ... last/persist", "durability", "half-life". Regression test
  `tests/unit/test_ws_api.py::test_scope_defers_titer_and_durability_questions`.

### Acceptance suite result
- 20/20 behave as specified at the engine level: grounded where earned, refusing where unsafe (ricin/botulinum),
  abstaining/deferring where appropriate (titer, durability, phenotype), no fabricated number. T10 (RNP/AAV) and T12
  (multiplex translocation) are enforced via `delivery.cargo_form_compatible` and `multiplex.translocation_risk`
  on the structured design fields (`writer_output_form`, `edits`).

## [6.2.2] - 2026-06-12 - Safe-harbour locus-nickname resolution (patch)

A usability fix. Site Finder / `/plan` / `/writable` returned 0 plans for `AAVS1` because it is a genomic
safe-harbour locus nickname, not an HGNC gene symbol, so the gene-to-coordinate lookup (`gene_coords`, 60,888
symbols) could not resolve it: an empty result, but unhelpful for the most-typed safe harbour. (The cell-type
atlases are complete; real symbols like `PCSK9`/`HBB`/`CCR5`/`CLYBL` resolved fine.)

### Fixed
- `pen_stack/planner/optimize.py`: `resolve_gene()` maps well-documented safe-harbour nicknames to their host
  gene (`AAVS1` to `PPP1R12C` 19q13.42; `H11`/`Hipp11` to `EIF4ENIF1` 22q12) at every gene-to-coordinate lookup
  (`gene_region`, `plan`, `crosslink.loci_for_gene`); real symbols pass through unchanged. Regression test
  `tests/unit/test_ws_api.py::test_safe_harbour_nickname_resolves_to_host_gene`.

## [6.2.1] - 2026-06-12 - JSON-safe atlas/crosslink endpoints (patch)

A bug fix. The `/atlas`, `/writable`, and `/crosslink/loci` endpoints returned raw DataFrame records, which
leak non-finite floats (`NaN`/`inf`) present in `atlas.parquet`; the JSON encoder rejects these
(`ValueError: Out of range float values are not JSON compliant`, so HTTP 500). Surfaced on the v6.2 Web Platform's
Writer Atlas and Site Finder pages.

### Fixed
- `pen_stack/server/api.py`: a `_records()` helper serializes DataFrame rows JSON-safely (via pandas `to_json`,
  so `NaN`/`inf` become `null` and numpy scalars become native), applied to `/atlas`, `/writable`, `/crosslink/loci`.
  Regression test `tests/unit/test_ws_api.py::test_records_helper_is_json_safe_with_non_finite_floats`.

## [6.2.0] - 2026-06-11 - The Web Platform (the human surface)

A post-1.0 adoption surface for bench scientists. A complete, friendly web application: a grounded co-scientist
chat plus structured feature pages, over the same typed v6.1 API the AI surface uses. The LLM narrates and
routes but never sources a number; every quantitative answer renders with its confidence band, provenance, and
an explicit ledger of what PEN-STACK can't tell you. This is a minor release on the stable 6.0 API, SHA-locked.

### Added
- **Backend:** `pen_stack/web/server.py`, one FastAPI gateway that mounts the v6.1 engine surface under
  `/api` (so the frontend has one base URL and one OpenAPI) and adds the grounded `/chat` (plus SSE `/chat/stream`),
  CORS, and static serving of the built frontend (`web/dist`). A `/health` for the live grounded indicator.
- **Chat (the hard gate):** `pen_stack/web/tools.py` (the deterministic engine tool-runner: parse a goal,
  run `verify`/`safety`/`immune_profile`/scope, return a grounded dossier; `extract_grounded_numbers` is the allow-list)
  and `pen_stack/web/llm.py` (the grounded co-scientist: Ollama, then Nemotron, then deterministic narrator, with
  `_enforce_grounding` striking any numeric token the model can't trace to a tool result). A reply's numbers are
  always engine-sourced; `tests/unit/test_ws_chat.py` asserts no number in a reply is absent from the tool
  results, and that the deterministic narrator works with both LLMs offline.
- **Frontend:** `web/` (React/Vite plus Tailwind): the UX component library (`ConfidenceBand`,
  `ProvenanceChip`, `ScopeLedger`, `SafetyBadge`, `ImmuneProfileCard`), so a number is never shown without its
  uncertainty plus provenance, and the scope ledger appears on every answer.
- **Pages:** 11 feature pages over the typed API: Co-Scientist, Site Finder, Writer Atlas, Designer,
  Verify, Delivery & Immunity, Digital Twin, Guardian, Experiments, Challenge, Scope & About. Each renders
  through the UX library and degrades gracefully when the LLM is offline.
- **Deploy:** `docker/web.Dockerfile` (multi-stage: a node:20 stage builds the frontend, a slim Python
  serves UI plus API from one origin) plus a `web` service in `docker-compose.yml`: one-command self-host
  (`docker compose up web ollama`, open `http://localhost:8000`). `web/.env.example`, `web/README.md` quickstart.
- Read-only Challenge surface for the web page: `GET /api/challenge/{tasks,leaderboard}` (public tasks plus the
  PEN-STACK reference leaderboard; submissions are still scored offline, never accepted over HTTP).
- Preregistration `ws_{chat,frontend}` plus SHA locks; deposit `phase_6.2/`.

### Notes
- The LLM never sources a number. It explains, compares, and routes over the engine's tool outputs; the
  grounding guard strips any value it can't trace, and the app runs in a deterministic, no-LLM mode (the science
  lives in the engine, not the model). This cycle improves usability/adoption, not validation; a real-data
  result and a first lab user remain the standing bottleneck. No new science; contracts under the 1.0 commitment.

## [6.1.0] - 2026-06-11 - The AI Integration Surface

A post-1.0 adoption surface for AI builders. Not new capability: the introspectable, documented, dependable
contract that lets an external agent discover what PEN-STACK offers and what it refuses to answer. This is a minor
release on the stable 6.0 API, SHA-locked.

### Added
- **Capability and scope manifests (the differentiator):** `pen_stack/api/manifest.py`: `capability_manifest()`
  (machine-readable: the stable tools, inputs/outputs, all `fabricates=False`, guarantees, stability) and `scope_manifest()`
  (machine-readable: the known-unknowns registry plus every oracle scope card, i.e. what PEN-STACK refuses to
  answer). Generated from the live registry/scope cards (never hand-written); internal matcher fields not leaked.
- **OpenAPI:** `pen_stack/server/api.py`: `GET /capabilities` plus `GET /scope` plus `POST /verify /safety /immune
  /generate /predict /suggest /session`; FastAPI auto-generates the OpenAPI 3.1 spec at `/openapi.json`.
- **MCP:** `pen_stack/agent/mcp_server.py`: the self-describing resources `pen-stack://capabilities` plus
  `pen-stack://scope`, plus the engine tools (`safety_screen`, `immune_profile`, `generate_designs`,
  `predict_outcome`, `suggest_experiment`, `co_scientist_session`). A hazardous design returns a structured
  refusal an agent branches on.
- **Examples:** a runnable golden path: `examples/external_agent.py` (REST: discover scope, submit, branch on
  safety/legality), `examples/mcp_client.py` (MCP), `examples/agent_tools.py` (framework-agnostic tool specs built
  from the live manifest plus an in-process dispatcher to the validated engine).
- Docs: `docs/integrations.md` rewritten as "Integrate PEN-STACK in your AI" (the four guarantees plus the scope
  contract plus REST/MCP/framework quickstarts); preregistration `ws_{manifest,openapi,mcp}` plus SHA locks; deposit `phase_6.1/`.

### Notes
- Scope is data, not a disclaimer. The scope manifest makes the scope machinery itself an API, the thing
  that makes trustworthy autonomy something another system can build on. This cycle lowers the barrier to
  adoption; it does not, by itself, create it: outreach plus a real result remain the standing bottleneck. No new
  science or validation; contracts versioned plus deprecation-policed under the 1.0 commitment.

## [6.0.0] - 2026-06-11 - 1.0, First Stable (the graduation)

The Closed-Loop arc is complete (7/7), and PEN-STACK graduates to "1.0, First Stable." The public API,
exercised across every surface (verify, safety, generative design, twin, experiment design, build interface,
closed loop, co-scientist, and the Genome-Writing Challenge), is documented and frozen with a deprecation
policy. "First Stable" is earned, not declared: it is cut only after the closed loop is demonstrated (v5.12),
the benchmark is public (v5.13), and the integration surface ships.

### Changed
- **`Development Status :: 5 - Production/Stable`** (was Beta). Version 6.0.0 (MAJOR).
- The public API is documented and frozen with a deprecation policy: **`docs/STABILITY.md`** (semver from 6.0.0;
  deprecations warn at least 1 MINOR before removal in a MAJOR; the `OracleResult`/`Verdict`/`SafetyVerdict`/immune-profile
  contracts and invariants, including `collapsed_score is None` and the no-fabrication guard, are stable across 6.x).
- The Genome-Writing Challenge is public.

### Notes
- "1.0, First Stable" is a commitment to API stability, not a claim of solving genetic engineering. The
  unknown funnel remains, made legible (scope flags, known-unknowns, baselines, no fabrication), not
  hidden. The high version numbers of the program's fast youth finally meet a real stability commitment.

## [5.13.0] - 2026-06-11 - The Standard (Genome-Writing Challenge plus Co-Scientist II)

This cycle aims to make PEN-STACK the field's reference: an open, recurring, held-out benchmark
others build to, and to give scientists a co-scientist that drives the whole loop with immune-risk first-class.
SHA-locked. (The v6.0.0 "1.0, First Stable" graduation follows.)

### Added
- **The Genome-Writing Challenge** (`benchmarks/genome_writing_challenge/`): an open,
  recurring, held-out leaderboard (the CASP / Virtual-Cell-Challenge model). `evaluate(Submission, round_id)`
  scores an external `predict_fn(public_input) -> answer` on a held-out round whose labels it never sees; labels
  are computed by the validated PEN-STACK layers (rules / v5.7 Guardian / v5.6 immune profile) so no task uses a
  circular label; a no-fabrication audit runs on every submission; task families include an immune-risk
  task grounded in the v5.6 oracles. A one-command runner (`run.py`); a reference submission anchors the leaderboard.
- **The matured co-scientist** (`pen_stack/agent/co_scientist.py::co_scientist_session(goal, cell_state)`)
  drives the whole loop: safe, legal, calibrated designs, then predicted outcomes, then suggested
  experiments, then exportable protocols, returning the Pareto strategies, calibrated `predicted_outcomes`,
  per-axis immune profiles (first-class), `suggested_experiments`, citations (resolve by construction),
  a complete scope ledger, and the per-design safety decision. The scientist/lab decides; the co-scientist
  drives. No number is fabricated; hazardous candidates are discarded.
- **The integration surface:** MCP server tools, the Challenge submission API, and a worked reference
  example (`docs/integrations.md`). The standing adoption criterion (at least 1 external integration plus at least 1 external
  submission) depends on outreach, the non-code bottleneck flagged since v3.1; the surface is shipped.
- Docs: `docs/{challenge,co_scientist_loop,integrations}.md`; preregistration `ws_{challenge,cosci2}` plus SHA locks; deposit
  `phase_5.13/`.

### Notes
- A standard requires a community: PEN-STACK provides the open, reproducible, held-out benchmark and the
  integration surface; adoption depends on outreach. The co-scientist drives and presents (including the
  immune-risk profile with its known-unknowns); the scientist and lab decide.

## [5.12.0] - 2026-06-11 - The Closed Loop (autonomy Level 3)

This release integrates everything into one continual design/build/test/learn cycle,
humans/lab in control, no fabrication, drift-aware. It reaches autonomy Level 3 (the program's ceiling).
SHA-locked.

### Added
- **The loop** (`pen_stack/loop/cycle.py`): `run_loop(goal, cell_state, ...)` orchestrates every prior cycle each
  round: generate (v5.8), decide/batch (v5.10), safety-gated export (v5.7 plus v5.11), run (sim-lab v5.11 /
  real lab), ingest (v4.5 gate), drift (v5.12), continual learn (v5.12). Gated: safety, build, and
  belief-admission each await the `approver`. Returns `autonomy_level=3`, `human_in_control=True`,
  `no_fabrication=True`. A hazardous candidate is discarded by the safety-gated pipeline before it is ever run.
- **Drift** (`pen_stack/loop/drift.py`): `detect_drift(designs, results)` compares the v5.9 twin's predictions
  vs observed readouts; growing miscalibration leads to `severity:"high"` and `inflate_intervals` (widen, don't over-trust).
- **Continual learning** (`pen_stack/loop/continual.py`): `continual_update(...)` recalibrates trust plus twin plus immune
  proxies on admitted outcomes only; each update is versioned and reversible (`rollback_to`); high drift
  widens intervals; an admitted immune measurement with a CI can graduate a v5.6 proxy to outcome-validated.
  This is recalibration, not foundation-model retraining.
- **Demo and autonomy criteria:** `loop_converges_faster_than_random` reports the active-vs-random convergence with a
  bootstrap CI (retrospective/simulated, reported either way); `docs/autonomy.md` asserts the Level-3 criteria
  (closed loop, human in control at every gate, anomaly flagging, no fabrication) and that Levels 4/5 are
  not claimed.
- **Bench v0.3.8:** a new `closed_loop` hard-gate task. The gate is the loop's integrity (gated
  end-to-end run plus no-fabrication plus Level-3 human-in-control plus drift detection plus versioned/reversible continual
  learning); an ungated autopilot fails by construction. Convergence reported informationally.
- Docs: `docs/{closed_loop,autonomy}.md`; preregistration `ws_{loop,continual,drift}` plus SHA locks; deposit `phase_5.12/`.

### Notes
- The loop is Level 3: closed, but with humans/lab in control at every gate, not autonomous. It runs in
  silico via the sim-lab (a real lab attaches at the same interface); continual learning recalibrates rather than
  retrains; drift covers calibration/residual shift, not all failures; the convergence demo is retrospective/
  simulated, reported with CIs.

## [5.11.0] - 2026-06-11 - The Build Interface (digital-to-physical bridge)

This release makes designs executable and results ingestible: loop-ready, lab-optional,
safety-gated, with the immune-risk profile attached as protocol metadata. SHA-locked.

### Added
- **Protocol export** (`pen_stack/build/protocol.py`): `export_protocol(design, experiment, target, actor)` for
  Opentrons / PyLabRobot / cloud-lab. It runs `verify()` first: a safety-`refuse` or illegal design raises
  `ProtocolExportError` (no export path for a flagged design); a cleared design is emitted as a DRAFT
  ("human/lab review required") carrying the v5.6 immune profile plus provenance in its metadata. Never auto-run.
- **Ingest** (`pen_stack/build/ingest.py`): `ingest_result(result, ...)` validates a result (assay / readout /
  provenance) and turns it into a quarantined measured edge Candidate; the only path into the curated
  world-model is the v4.5 gate (`gate_admit`): automated checks AND explicit human approval. No auto-edit
  (Principle 1). Immune measurements can begin validating the v5.6 proxies on a later pass.
- **Sim-lab** (`pen_stack/build/simlab.py`): `run_simulated(protocol_ir, design, cell_state)` executes a
  protocol in silico (samples from the v5.9 twin plus measurement noise), labelled `SIMULATED`, so the closed
  loop (v5.12) runs end-to-end (export, sim, ingest) without hardware; it never enters the world-model as
  measured truth.
- **Bench v0.3.7:** a new `protocol_safety` hard-gate task (`pen_stack/validate/protocol_safety.py`):
  a cleared design exports with immune metadata, a safety-refused/illegal design is blocked, and the simulated
  loop completes with quarantined SIMULATED results; an ungated exporter (which would emit the hazardous protocol)
  fails by construction.
- Docs: `docs/build_interface.md`; preregistration `ws_{proto,ingest,simlab}` plus SHA locks; deposit `phase_5.11/`.

### Notes
- PEN-STACK emits protocols and ingests results; it does not run experiments. Protocols are drafts requiring
  human/lab review, results enter only through the gate, and the simulated lab is for development / loop-validation,
  never a substitute for real data. Export is hard-blocked for anything the safety gate flags.

## [5.10.0] - 2026-06-11 - The Experiment Designer (active learning / EIG)

The "Learn" brain of a self-driving lab: turn "I'm uncertain" into "run
this experiment next." It reads the calibrated v5.9 twin's uncertainty plus the v5.6 immune labels, scores each
candidate experiment by expected information gain, assembles a diverse batch, and proves on held-out data, with
CIs, that this learns faster than random/greedy (reporting plainly when it does not). SHA-locked.

### Added
- **Acquisition** (`pen_stack/active/acquire.py`): `expected_information_gain` (reducible uncertainty from the twin's
  predictive distribution; `>= 0`, monotone in uncertainty), `predictive_entropy` (from the twin's interval width),
  and `immune_voi` (value of information for validating an immune proxy axis, v5.6): an experiment that
  would measure a still-proxy axis is high-VOI (it turns proxy to outcome-validated). `acquisition_score` is fully
  traceable to twin quantities plus v5.6 labels; deterministic; no fabricated values.
- **Batch design** (`pen_stack/active/design.py`): `select_batch` greedily maximises acquisition minus a
  redundancy penalty (shared design facets), giving a diverse batch (not k copies of the most-uncertain point);
  each experiment carries its expected info gain.
- **Validation** (`pen_stack/active/validate.py`): `retrospective_active_learning` simulates active vs random vs
  greedy campaigns on a held-out split, reports mean±CI learning curves and a bootstrap CI on the curve-area
  gap; `active_beats_random` only when the CI excludes zero, else the not-yet-useful negative is reported.
- **Bench v0.3.6:** a new `experiment_design` hard-gate task. The gate is the Learn engine's
  properties (twin-sourced EIG monotone in uncertainty plus immune-VOI for proxy validation plus a diverse
  batch plus retrospective active-vs-random with reps and CI); a random selector fails by construction. Active-beats-
  random is reported informationally.
- Docs: `docs/experiment_design.md`; preregistration `ws_{acq,aldesign,alvalidate}` plus SHA locks; deposit `phase_5.10/`.

### Notes
- The experiment designer is only as good as the v5.9 twin plus the v5.6 labels it queries; its advantage is validated
  retrospectively with CIs and reported plainly when absent. It chooses informative experiments but does
  not run them; prospective benefit awaits a lab partner (v5.11+). No autonomy claim.

## [5.9.0] - 2026-06-11 - The Digital Twin (calibrated outcome prediction)

The missing layer: what does the cell do after the write? Predicted with
calibrated uncertainty. The twin computes what mechanism allows, adds an in-distribution virtual-cell estimate
(OOD-gated), screens immune outcome from the v5.6 profile, and is explicit about its boundary at phenotype.
SHA-locked.

### Added
- **Virtual cell** (`pen_stack/oracles/vcell.py` plus scope cards `state`/`scgpt`): `predict_response(cell_state,
  perturbation, model)` wraps Arc STATE / scGPT under the v4.0 `OracleResult` contract. A
  perturbation-response prediction is a candidate, OOD-gated (a context outside the documented envelope is marked
  `extrapolating`), cached/deferred (value `None` when absent, never fabricated). It encodes the field's own result
  (Arc Virtual Cell Challenge): perturbation models don't yet consistently beat naive baselines.
- **Mechanism** (`pen_stack/twin/mechanistic.py`): `cassette_expression` = `promoter_strength x copy_number x
  accessibility` (closed-form steady state); assumptions plus scope flags attached; physics where computable, not
  a phenotype.
- **Outcome** (`pen_stack/twin/outcome.py`): `predict_outcome(design, cell_state)` fuses mechanism plus an
  in-distribution virtual-cell response plus the v5.6 immune profile into one prediction with an interval that
  widens under OOD, an immune-outcome dimension, and an explicit phenotype / in-vivo-magnitude boundary.
  In-vivo durability may be conditioned on the grounded pre-existing-NAb axis (no invented immune numbers);
  `output_kind="candidate"`.
- **Calibration** (`pen_stack/twin/calibrate.py`): `calibrate_outcome(...)` reports calibration two-sided: interval
  coverage plus a bootstrap CI on the MAE gap vs a naive mean baseline; the twin "beats" naive only when the CI
  excludes zero, else the negative is reported verbatim; it abstains at `N < 3`.
- **Bench v0.3.5:** a new `outcome_prediction` hard-gate task (`pen_stack/validate/outcome_prediction.py`):
  the gate is the twin's calibration properties (two-sided calibration plus OOD widening plus immune dimension plus
  phenotype out-of-scope), which an overconfident predictor fails by construction; twin-vs-naive skill is reported
  informationally on a labelled synthetic stream (no public perturbation-outcome calibration set exists).
- Docs: `docs/digital_twin.md`; preregistration `ws_{vcell,mech,outcome,twincal}` plus SHA locks; deposit `phase_5.9/`.

### Notes
- The twin is a hypothesis engine, not an oracle of truth: predictions are candidates with intervals;
  phenotype, in-vivo behaviour, immunogenicity magnitude, and durability beyond the computable stay
  scope-flagged. The interval is a heuristic band, not a trained conformal interval (no public outcome
  calibration set). Immune-outcome is sourced from v5.6, never invented.

## [5.8.0] - 2026-06-11 - The Live Agent and Generative Designer

PEN-STACK turns from a checker into a grounded designer: it generates
candidate end-to-end writing systems, keeps only those that pass safety plus legality plus calibration
(verifier-as-discriminator), and returns the Pareto frontier of real tradeoffs, in which immunogenicity-risk
is, for the first time, a grounded axis sourced from the v5.6 profile rather than a placeholder. SHA-locked.

### Added
- **Generation** (`pen_stack/design/{space,generate}.py`): `generate_designs(goal|candidates)` proposes candidates
  (`candidate_space` = the validated Phase-3 planner by the compatible delivery palette) and the v3.3 `verify()`,
  now safety-gated (v5.7) plus legality plus calibration plus immune-profiled, disposes. A candidate survives only
  if legal AND safe (`clear`/`flag`); hazardous (`refuse`/`escalate`) and illegal proposals are discarded,
  never returned (the `as_claim()` guard generalised to whole designs). Survivors carry calibrated confidence,
  the v5.6 immune profile, the safety decision, and `output_kind="candidate"`, never asserted to work.
- **Pareto** (`pen_stack/design/pareto.py`): `pareto_front(designs)` over `(efficiency, durability, safety,
  deliverability, neg_immune_risk, neg_cost)`. `neg_immune_risk` is grounded by the v5.6 profile: the
  worst-case per-axis in-scope score with the per-axis uncertainty carried as a band; the profile is never
  collapsed into one number and the in-vivo magnitude stays scope-flagged (`in_vivo_magnitude_unknown`).
- **Orchestration** (`pen_stack/agent/orchestrator_live.py`): `orchestrate(goal)`: plan, generate, call an oracle
  (cache-first/replayable) for a critique signal, dispose via `verify()`, refine. Every number is tool-sourced;
  a seed-locked replay reproduces the trace (replay is the CI default); no fabrication.
- **Bench v0.3.4:** a new `generative_design` hard-gate task (`pen_stack/validate/generative_design.py`):
  on a frozen mixed pool (benign plus a hazardous ricin payload plus illegal oversize/mRNA-incompatible), the grounded
  designer returns only legal, safe, calibrated, immune-profiled survivors on a grounded-immune-axis Pareto frontier,
  while an ungrounded generator ships hazardous/illegal designs and fails by construction.
- Docs: `docs/generative_design.md`; preregistration `ws_{gen,pareto,orch}` plus SHA locks; deposit `phase_5.8/`.

### Notes
- A generated output is a candidate, never a claim; novelty is bounded by the oracles' validity and the
  rules' legality, and never asserted to work. The immune-risk Pareto axis is a worst-case screen; the
  per-axis v5.6 profile (with its validation labels) remains authoritative; in-vivo magnitude is a known-unknown.

## [5.7.0] - 2026-06-11 - The Guardian (biosecurity / dual-use safety gate)

This release makes PEN-STACK safe by
construction before it moves toward "build": every design submitted to `verify()` first passes a biosecurity / dual-use screening gate that
refuses or escalates select-agent, pandemic-pathogen, and controlled-toxin signatures, with function-based and
chimera checks that catch AI-designed homologs that homology alone would miss, while legitimate therapeutic designs
pass untouched. It is orthogonal to (and complementary with) the v5.1-v5.6 immune-risk profile. SHA-locked.

### Added
- **Screens** (`pen_stack/safety/{registry,screen}.py` plus `configs/safety/hazard_registry.yaml`): a curated,
  version-pinned `HazardRegistry` (`registry_version`) and three or more screens returning typed, provenanced
  `ScreenHit`s: `function_flag` (toxin / pathogen-essential functions, the screen that catches AI-homologs
  at low identity), `taxon_flag` (regulated-pathogen taxa), `chimera_context` (hazardous assembly of benign
  parts plus split-hazard), and `sequence_homology` (delegated to a wrappable external screener: IBBIS Common
  Mechanism / SecureDNA-style; the in-repo baseline is a no-op). Signatures are function/family/taxon-level
  only (public Pfam accessions plus public control-list references: 42 CFR 73 / 7 CFR 331 / 9 CFR 121 / Australia
  Group / HHS P3CO/DURC), no hazard sequences, no synthesis/enhancement detail. All 14+ Pfam accessions were
  independently verified against EBI InterPro before reliance; one error (PF01375, mislabeled anthrax, which is
  heat-labile/cholera enterotoxin) was caught and corrected; anthrax PA was re-sourced from UniProt P13423.
- **Policy** (`pen_stack/safety/{policy,gate,audit}.py` plus `configs/safety/policy.yaml`): `SafetyVerdict`
  {clear, flag, refuse, escalate}; `safety_gate(design, actor=...)` = strip-framing, screen, decide, audit;
  ambiguous dual-use (gain-of-function) escalates to human review (HHS P3CO/DURC), not auto-refuse; an
  append-only, hash-chained, tamper-evident `audit_log` (plus `verify_chain`) storing a design digest, not the
  design. Re-framing as "defensive research" cannot flip refuse to clear (the artifact decides, not the wording).
- **Integration:** `Verdict.safety: SafetyVerdict`; `verify(design, actor=...)` runs the gate first and a
  `refuse` short-circuits (the design is returned un-evaluated, not scored/critiqued). No-fabrication holds:
  hits come only from the versioned registry.
- **Red team** (`pen_stack/safety/redteam.py`): an adversarial harness (AI-homolog, split-hazard, reframing,
  chimera) plus reframing-stability pairs; reports set size plus caught count.
- **Bench v0.3.3:** a new `safety_screening` hard-gate task (`pen_stack/validate/safety_screening.py`):
  benign therapeutics 0 false refusals, hazards refused/escalated at correct severity, evasions never `clear`;
  beats a no-safety baseline (1.0 vs 0.33) by construction. Frozen probes/registry/policy SHA-locked into the
  bench. The bench is now 17/17 available, planner beats naive on 13/13.
- Docs: `docs/responsible_use.md` plus `docs/biosecurity.md`; preregistration `ws_{screen,policy,redteam}` plus SHA locks;
  deposit `phase_5.7/` (execution summary plus an independent data/ID verification record).

### Notes
- The safety gate is a defensive safeguard, not a guarantee, and not a substitute for institutional
  biosafety / IBC review; signatures are versioned and exploit detail is intentionally not published.
- It is orthogonal to the immune-risk profile: the Guardian asks "is this design hazardous/dual-use?"; the immune
  profile asks "will the patient react?". Both attach to every `Verdict`; neither subsumes the other.

## [5.6.0] - 2026-06-11 - Immunology completion and calibration (anti-PEG, proxy labels, unified profile)

This release finishes the delivery-immunology arc (v5.1-v5.5): it adds the missing anti-PEG axis, calibrates the
proxies, and exposes a unified per-design immune-risk profile that never collapses into one number.
SHA-locked.

### Added
- **Anti-PEG** (`pen_stack/planner/antipeg_oracle.py` plus `configs/antipeg.yaml`): pre-existing/induced anti-PEG
  antibodies gate re-dosing of PEGylated LNP. Population prevalence range (25-72%) gives
  `preexisting_antipeg_score = 1 - midpoint/100`, range surfaced as `native_uncertainty`; abstains for
  non-PEGylated vehicles. Serosurvey DOIs Crossref-verified (Chen 2016 `10.1021/acs.analchem.6b03109`, Yang &
  Lai `10.1002/wnan.1339`, Armstrong `10.1002/cncr.22739`, Kozma `10.1016/j.addr.2020.07.024`). Scope card `antipeg`.
- **Calibration** (`pen_stack/validate/immune_calibration.py`): `calibrate_axis()` (Spearman rho plus percentile
  bootstrap CI) labels an axis outcome-validated only when the CI excludes zero, else `weak_proxy`, and
  `mechanistic_proxy` when N < 6. With no sufficient public paired (proxy, observed) dataset, every axis is
  labelled a mechanistic/population proxy; the label travels with the profile. (No fabricated
  outcome data; the machinery is proven on synthetic input.)
- **Profile** (`pen_stack/planner/immune_profile.py` plus `Verdict.immune_profile`): a per-design vector
  of all axes (genotoxicity, CD8 epitope, innate, pre-existing NAb, anti-PEG), each with its own value plus
  uncertainty plus scope plus validation label. `collapsed_score is None` (never fused, asserted); known-unknowns
  listed; abstaining axes report `None`.
- **Extras:** a documented qualitative route/immune-privilege modifier (eye/CNS lower realized
  immunogenicity vs systemic; Streilein 2003 `10.1038/nri1224`; no fabricated magnitude); CD4/MHC-II helper
  epitopes, pre-existing capsid-specific T-cell immunity, and complement/CARPA registered as
  known-unknowns. `prereg/ws_{peg,calib,profile}.yaml` plus SHA locks.

### Changed
- Version 5.5.0 to 5.6.0 (minor, additive); `cite.curated_dois()` ingests the anti-PEG plus immune-privilege DOIs.

### Scope invariant (unchanged)
- Every axis is a relative-risk screen (sequence/mechanistic or population proxy), labelled as such until
  outcome-validated; the profile is never collapsed into one number; patient-specific titer, post-dose-1
  induced immunity, and exact in-vivo magnitude stay known-unknowns.

## [5.5.0] - 2026-06-10 - Anti-vector seroprevalence oracle (the last immune axis, from data)

This release completes the computable delivery-immunology axes. Pre-existing humoral immunity (B-cell /
neutralizing antibody) to a viral capsid is the one immune axis that cannot be computed from sequence: it is a population
prevalence from natural exposure. v5.5 grounds it in published serosurvey data. SHA-locked.

### Added
- **Seroprevalence table** (`configs/seroprevalence.yaml`): curated population NAb/IgG seroprevalence per serotype
  as ranges (region/age/assay variation) with DOIs: AAV (Calcedo 2009, Boutin 2010), adenovirus type 5
  (Mast 2010), HSV-1 (Looker 2015), VSV (negligible).
- **Seroprevalence oracle** (`pen_stack/planner/seroprevalence_oracle.py`): `seroprevalence_oracle(vehicle,
  serotype=None)` returns an `OracleResult`. `preexisting_score = 1 - midpoint(seroprevalence)/100`; the range width is
  surfaced as `native_uncertainty`. Non-viral becomes 1.0 by mechanism; unknown abstains.
- **Wired into the pre-existing axis:** `safety_efficacy_profile()` folds the computed seroprevalence score
  into the `preexisting_immunity` sub-axis only for in-vivo vehicles (serum NAb neutralises the vector in
  vivo; ex-vivo transduction in a dish is not reached by host antibody, so it is reported but muted). `seroprevalence_score`
  surfaces the raw value.
- **Result (from data):** adenovirus has the highest pre-existing seroprevalence (40-90%, score 0.35), AAV
  intermediate (30-60%, 0.55), VSV/lentivirus negligible (0-5%, 0.975), the documented ordering quantified
  from serosurveys. `prereg/ws_seroprev.yaml`.

### Changed
- Version 5.4.0 to 5.5.0 (minor, additive data-grounded oracle); `cite.curated_dois()` ingests the
  seroprevalence DOIs.

### Scope invariant (unchanged)
- This is a population prevalence (a range; region/age/assay-dependent), not a given patient's NAb titer /
  sero-status (a clinical test, patient-specific, a known-unknown); the humoral (B-cell) axis only,
  distinct from the v5.3 T-cell epitope load. No patient-specific magnitude predicted.

## [5.4.0] - 2026-06-10 - Computed innate-sensing scorer (completes the computable immune axes)

The third computed delivery-immunology signal, after v5.2 genotoxicity and v5.3 capsid epitope load. Innate
sensing of a delivered nucleic acid is computed directly from the cargo sequence: CpG O/E for DNA (TLR9),
U-richness plus dsRNA for mRNA (TLR7/RIG-I), covering every cargo form. SHA-locked.

### Added
- **Innate scorer** (`pen_stack/planner/innate_sensing.py`): `cpg_observed_expected()` (Gardiner-Garden &
  Frommer) plus `innate_sensing(seq, cargo_form)` returning an `OracleResult`. DNA gives CpG O/E (vertebrate genome ~0.2
  tolerated; non-depleted DNA is TLR9-stimulatory), `innate_score = max(0, 1 - CpG_O/E)`. mRNA gives uridine
  fraction plus ViennaRNA dsRNA pairing (graceful when ViennaRNA absent), flagged partial/`extrapolating`.
  RNP is minimal/transient. Abstains on empty / unrecognised input (never fabricates). Pure sequence
  computation, no external data, runs in CI.
- **Surfaced in `verify()`:** when a design supplies `cargo_seq`, the computed innate load is attached as a
  `cargo_innate_sensing` scope flag (cargo form from the writer output form, else the vehicle's first
  compatible form) and added to `delivery_profile.cargo_innate`. No confidence added; the realized in-vivo
  innate response stays a known-unknown.
- Scope card `innate_sensing`; `prereg/ws_innate.yaml`. `cite.curated_dois()` ingests the innate provenance
  DOIs (CpG-TLR9 10.1073/pnas.161293498, CpG-depleted AAV 10.1172/JCI68205, RNA modification
  10.1016/j.immuni.2005.06.008, plus Krieg 1995 / Hornung 2006).

### Changed
- Version 5.3.0 to 5.4.0 (minor, additive computed scorer).

### Scope invariant (unchanged)
- This is a sequence-intrinsic motif-load signal. The realized in-vivo innate response magnitude in a patient is
  not modelled (known-unknown); the mRNA score is partial because the dominant evasion lever,
  nucleoside modification (m1-pseudouridine), is a manufacturing choice not derivable from sequence; DNA
  methylation state is likewise out of scope. No magnitude predicted.

## [5.3.0] - 2026-06-10 - Computed capsid epitope-load oracle (covers all vectors)

v5.2 computed genotoxicity only meaningfully touches integrating vectors. v5.3 brings the NetMHC-style
calculation to the adaptive (CD8 T-cell) axis: the fraction of a viral vector's capsid/envelope that is
presentable across a frequent HLA-I panel (MHCflurry), so the computed immune signal covers all 8 vehicles
(5 viral computed, 3 non-viral by mechanism). SHA-locked.

### Added
- **Build** (`scripts/p53_build_epitope_oracle.py`, runs in a dedicated `penstack:mhcflurry` image):
  slides 9-mers across each capsid/envelope antigen and predicts MHCflurry 2.0 affinity %rank per allele across
  12 frequent HLA-I alleles; `epitope_fraction_strong` = residues covered by a strong binder (%rank <= 0.5);
  `capsid_immune_score = 1 - epitope_fraction_strong`. Sequences UniProt-verified and committed
  (`configs/capsid_sequences.fasta`): AAV2 VP1 P03135, Ad5 hexon P04133, VSV-G P03522, HSV-1 gD P57083 plus gB
  P06437. Emits the small committed summary `configs/capsid_epitope_oracle.yaml` (MHCflurry plus raw sequences stay
  on the VM, CI-safe).
- **Oracle** (`pen_stack/planner/capsid_epitope_oracle.py`): `capsid_epitope_oracle(vehicle)` returns
  an `OracleResult` (`output_kind="baseline"`, scope card `capsid_epitope`). Non-viral vehicles become 1.0 by
  mechanism; unknown / sequence-less abstains.
- **Wired into the adaptive axis:** `safety_efficacy_profile()` folds the computed capsid score into the
  adaptive (CD8) sub-axis only for in-vivo vehicles. The computed score is intrinsic antigen
  presentability; for ex-vivo lentivirus (whose VSV-G envelope is intrinsically epitope-dense but barely
  seen by the host ex vivo) it is reported but not folded (`adaptive_source = computed_ex_vivo_muted`), the
  documented tier kept. `capsid_presentability_score` surfaces the raw computed value.
- **Result:** the AAV2 capsid is the least epitope-dense (0.72) and Ad5 hexon among the most (0.82); HDAd's in-vivo
  immune score drops accordingly, the documented adaptive ordering reproduced from sequence. `prereg/ws_epitope.yaml`.

### Changed
- Version 5.2.0 to 5.3.0 (minor, additive computed oracle); `cite.curated_dois()` ingests the epitope
  provenance DOIs (MHCflurry 10.1016/j.cels.2020.06.010, HLA-I supertypes 10.1186/1471-2172-9-1).

### Scope invariant (unchanged)
- This is a population-level, sequence-intrinsic presentation signal (does the capsid contain HLA binders), not
  the realized in-vivo / patient-HLA-specific T-cell response (a known-unknown), and CD8/MHC-I only (not
  antibody / neutralizing-antibody). No magnitude predicted.

## [5.2.0] - 2026-06-10 - Computed genotoxicity oracle (data, not a documented tier)

The v5.1 genotoxicity axis was a documented ordinal tier; for integrating vectors that signal is in fact
computable from data the stack already holds. v5.2 adds a computed genotoxicity oracle: the observed
enrichment of a vector class's integration sites near COSMIC oncogenes, answering through the v4.0
OracleResult contract. SHA-locked.

### Added
- **Build** (`scripts/p52_build_genotox_oracle.py`, runs on the VM where the data lives): computes,
  per integrating vector class, `P(integration site within 50 kb of a COSMIC Cancer-Gene-Census oncogene)` and
  its enrichment over genome background, from VISDB per-virus catalogues by the Phase-1 oncogene annotation
  (COSMIC CGC v104). Emits the small, auditable, committed summary `configs/genotoxicity_oracle.yaml` (raw
  catalogues stay on the VM; only the statistics ship, CI-safe).
- **Oracle** (`pen_stack/planner/genotoxicity_oracle.py`): `genotoxicity_oracle(vehicle)` returns an
  `OracleResult` (`output_kind="baseline"`) with `genotox_score = min(1, 1/enrichment)`, native uncertainty
  (CI on the observed fraction), the `delivery_genotoxicity` scope card, and `extrapolating` for small-n
  classes. Non-integrating vehicles become 1.0 by mechanism; no computed class abstains (never fabricates).
- **Wired into the v5.1 balance:** `safety_efficacy_profile()` now prefers the computed genotox_score for
  integrating vectors and falls back to the documented tier otherwise (`genotox_source` records which).
- **Result (from data):** lentiviral (HIV) integration is 2.08x enriched near oncogenes (n=88,743, robust)
  vs 5.65x for gammaretroviral (MLV, the LMO2/SCID-X1 comparator, small-n flagged), reproducing the
  lentivirus-safer-than-gammaretrovirus ordering from VISDB by COSMIC, and the computed lentivirus score
  (0.48) validates the v5.1 documented "moderate" tier (0.5). `prereg/ws_genotox.yaml`.

### Changed
- Version 5.1.0 to 5.2.0 (minor, additive computed oracle); `cite.curated_dois()` ingests the genotox
  provenance DOIs (VISDB 10.1093/nar/gkz867, COSMIC CGC 10.1038/s41568-018-0060-1, HIV/MLV integration biology).

### Scope invariant (unchanged)
- This is a relative integration-preference signal. The in-vivo clonal-expansion / leukemogenesis outcome
  in a patient is not modelled and stays a known-unknown (`delivery_genotoxicity` scope card); the immune
  magnitude likewise stays `in_vivo_immunogenicity`. No magnitude is predicted.

## [5.1.0] - 2026-06-10 - Delivery immunology (the safety/efficacy balance)

The delivery palette gains a documented, cited, qualitative immune plus safety plus efficacy profile per vehicle,
so the substrate can make the safety/efficacy tradeoff legible and user-weightable, without ever predicting an
immune magnitude (that stays a declared known-unknown). SHA-locked.

### Added
- **Config** (`configs/delivery_vehicles.yaml` v1.1): an `immune_safety` block on all 8 vehicles
  (`preexisting_immunity`, `neutralizing_antibody`, `innate_immune`, `adaptive_immune`, `genotoxicity`,
  `efficacy`, `tradeoff`, `immune_dois`): documented ordinal low/moderate/high priors, every `immune_doi`
  Crossref-verified and in the curated-DOI set (citations resolve by construction).
- **Planner** (`pen_stack/planner/delivery_immunology.py`): `safety_efficacy_profile()` reports two
  separate safety sub-axes: `immune_score` (immunogenicity; reversible, eligibility/re-dosing) and
  `genotox_score` (insertional/oncogenic; permanent), never collapsed, with a top-line
  `safety_score = min(immune_score, genotox_score)` (precautionary worst-axis). `recommend_delivery(cargo_form,
  cargo_bp, safety_weight, in_vivo)` ranks the eligible palette along the safety/efficacy frontier by a
  user-supplied weight. It reproduces the stated tradeoff: AAV is dinged on immunogenicity, lentivirus on
  genotoxicity. `prereg/ws_immune.yaml`.
- **Verify** (`Verdict.delivery_profile` plus a `delivery_immune_profile` scope flag): `verify()` now
  surfaces the documented profile and tradeoff for a chosen vehicle, always attaching the standing
  `in_vivo_immunogenicity` known-unknown flag, never adding confidence, never predicting a magnitude.

### Changed
- Version 5.0.0 to 5.1.0 (minor, additive delivery-immunology layer); `cite.curated_dois()` now also ingests
  the per-vehicle `immune_dois`.

### Scope invariant (unchanged)
- The in-vivo immune magnitude (patient/construct-specific response) remains a declared known-unknown
  (`configs/known_unknowns.yaml: in_vivo_immunogenicity`) and is never predicted. v5.1 exposes only
  documented ordinal priors plus a transparent, user-weighted ranking; it makes the boundary legible, it does
  not close it.

## [5.0.0] - 2026-06-09 - The Co-Scientist (capstone)

The reasoning ceiling rises while the grounding floor stays fixed: a co-scientist that proposes multiple
distinct strategies, critiques and revises its own plans, cites its reasoning, and itemises what it cannot
assess, with no-fabrication holding across the full reasoning stack (the central gate). Each component is SHA-locked.

### Added
- **Planning and multi-strategy** (`pen_stack/agent/co_scientist.py`): `propose_strategies()` returns 2-3 materially
  distinct strategies (at least 2 design axes differ, measured by `distinctness()`, not reworded), each
  independently legal plus confidence-tagged; `deliberate()` benchmarks the deliberative planner vs the
  deterministic baseline. `prereg/ws_plan.yaml`.
- **Critique and scope:** `critique()` / `critique_and_revise()` (the critic only flags plus swaps a design
  choice, never invents a number; revisions re-verified) plus `critique_falsifiability()` (improves flawed plans
  illegal to legal, 0 spurious revisions on clean) plus `scope_ledger()` (per-recommendation: what was/wasn't
  assessed, the known-unknowns itemised). `prereg/ws_crit.yaml`.
- **Citation and generalisation** (`pen_stack/agent/cite.py`): `cited_rationale()` (citations drawn from the curated
  world-model, resolve by construction) plus `citations_grounded()` guard (rejects any DOI not in the curated
  set) plus `generalise()` (adjacent tasks grounded-or-refused). `prereg/ws_cite.yaml`.
- **Bench v0.3.2:** a `co_scientist_grounded` reference-solver task: grounded rate 1.0 vs ungrounded 0.0;
  no-fabrication across the full stack. `docs/co_scientist.md`.

### Changed
- Version 4.5.1 to 5.0.0 (major, the substrate matured into a grounded co-scientist); bench 0.3.1 to 0.3.2.

## [4.5.1] - 2026-06-09 - ID-correctness patch: cell-type ontology IDs

### Fixed
Two of the three new v4.5 Tier-A cell-type ontology IDs in `configs/cell_types.yaml` were wrong (verified via
EBI-OLS): `EFO:0002322` resolved to the RPMI8226 myeloma line (not a T cell) and `EFO:0004146` to an
obsolete myopathy term (not hepatocyte). Corrected to the canonical, non-obsolete Cell Ontology terms:
primary_T_cell to `CL:0000084` (T cell), hepatocyte to `CL:0000182` (hepatocyte). iPSC (`EFO:0004905`),
K562 (`EFO:0002067`), HepG2 (`EFO:0001187`) verified correct, as was the ISPpu10 back-test record (Europe PMC
PPR1218813, "ISPpu10 is a structure-gated bridge RNA recombinase..."). No result/test change (the IDs are
coverage-card metadata; `cell_types.py` reads coverage, not the ontology id).

## [4.5.0] - 2026-06-09 - The Living World-Model (knowledge graph plus gated living loop)

v4.5 promotes the flat tables into a queryable knowledge graph that keeps itself current. Each component is
SHA-locked. The agent proposes; a gate disposes, so no process auto-edits curated truth.

### Added
- **Knowledge graph.** `pen_stack/graph/{schema,build,query}.py`: typed nodes
  (writer/locus/cargo/vehicle/cell_type/write_type/outcome) plus typed edges
  (reaches/deliverable_by/performs/durable_in/carries/used_writer/observed_at), each carrying evidence kind
  (measured > curated > predicted) plus confidence plus scope plus provenance. Built deterministically from the v4.0
  curated tables (94 nodes / 288 edges), a pure-Python JSON store. Multi-hop queries return provenanced paths;
  `deliverable_by` reproduces the v3.3 verifier (0 parity mismatches). REST `POST /graph/query` plus MCP
  `graph_query`. `docs/world_model.md`; `prereg/ws_graph.yaml`.
- **Gated living loop.** `pen_stack/graph/ingest.py`: Candidate plus Quarantine (propose never mutates
  a graph), `automated_checks` plus `gate_admit(approved, admitted_by)` as the sole admission path with versioned
  records; the back-test surfaces ISPpu10 (Europe PMC PPR1218813). No auto-edit path (asserted). `prereg/ws_mon.yaml`.
- **Cell-type expansion.** `configs/cell_types.yaml` Tier-A (iPSC/ESC, primary T cells, hepatocytes)
  with coverage cards plus a Tier-B roadmap; `pen_stack/graph/cell_types.py` graceful degradation (partial coverage
  caps confidence) plus cross-cell-type OOD labelling. `prereg/ws_ct.yaml`.
- **Graph reasoning bench.** `graph_multihop_reasoning` (bench v0.3.1): graph reasoning accuracy 1.0
  vs ungrounded 0.0, every answer a provenanced path. `prereg/ws_ba_v45.yaml`.

### Changed
- Version 4.0.3 to 4.5.0; bench 0.3 to 0.3.1; README updated for v4.5; M1/M2 plus world-model note updates.

## [4.0.3] - 2026-06-09 - ID-correctness patch: UniProt plus Pfam plus ontology audit

### Fixed
A whole-repo audit of structured IDs (verified against InterPro, UniProt, EBI-OLS, mygene):
- **`pen_stack/mech/pfam_whitelist.yaml` (v1.2.1 to v1.2.2):** the 26 Pfam accessions were all correct, but
  13 of 22 `example_uniprot` proteins did not actually contain their claimed domain (membership checked
  against each protein's UniProt Pfam cross-references), including a marine-worm Histone H3 (PF13586), a
  mouse mannosyltransferase (PF05621/TniB), I-AniI (a LAGLIDADG enzyme) mislabelled HNH (PF01844), a
  glycine-betaine transporter and a Tn3 transposase mis-filed as rve, and an obsolete 404 accession
  (PF08721), despite the header claiming a spot-check. All corrected to reviewed/curated proteins whose
  UniProt entry genuinely carries the domain (e.g. ISCro4 `D2TGM5`, Tn5 `Q46731`, Tn7-TnsA `P13988`, Bxb1
  integrase `Q9B086`, McrA `P24200`); the audit-status header was corrected to stop over-claiming.
- **`configs/atlas_families.yaml`** (drives family expansion in `expand.py`): IS621 `A0A0F6B5L8` (a
  betaine transporter) to `A0A2X3M8B0` (IS621 transposase); phiC31 `Q9T2A6` (a plant NAD(P)H
  oxidoreductase) to `Q9T221` (phiC31 integrase). The Pfam-query signatures and discovery DOIs were
  already correct.

### Verified clean
The 4 EFO cell-type IDs map correctly (EFO:0002067=K562, EFO:0001187=HepG2, EFO:0002784=GM12878,
EFO:0005483=ES-Bruce4); all GSH gene symbols are valid HGNC symbols; all 26 Pfam accessions resolve with the
correct domain name.

## [4.0.2] - 2026-06-09 - Citation-correctness patch: full-repo DOI audit

### Fixed
A full sweep of all 56 DOIs in the repo (verified via Crossref plus doi.org) found six incorrect or
non-existent citations, all now corrected to verified, topically-correct references:
- `configs/gsh_validated_heldout.yaml` H11 locus: `10.1371/journal.pone.0113481` (resolved to an unrelated
  cardiology paper) to `10.1093/nar/gkt1290` (Zhu et al. 2014, *DICE*, NAR 42:e34, the paper that
  characterized human H11 on chr22q12.2 between DRG1 and EIF4ENIF1).
- `configs/delivery_vehicles.yaml` plus `configs/rules/{delivery,payload}.yaml`: `10.1089/hum.2017.084`
  (non-existent), `10.1089/hum.2009.213` (non-existent), `10.1038/sj.gt.3302529` (unrelated erratum) to
  `10.1128/JVI.79.15.9933-9944.2005` (Grieger & Samulski, AAV packaging capacity),
  `10.1128/JVI.72.2.926-933.1998` (multiply-deleted adenovirus vectors), `10.1038/nbt1101-1067`
  (Wade-Martins, HSV-1 amplicon large-capacity).
- `pen_stack/validate/bench_writetype_tasks.py` provenance: `10.1038/s41586-023-06756-4` (diabetes program)
  and `10.1126/science.abm1123` (freshwater fish) to `10.1016/j.cell.2022.03.045` and
  `10.1128/JVI.79.15.9933-9944.2005`.

The remaining 50 DOIs resolve correctly; three legacy DOIs in `mech/pfam_whitelist.yaml` (Rice 1995 Cell,
Kholodii 1997 Res Microbiol, Prudhomme 2002 J Bacteriol) carry full author/year/journal references and are
real classic papers whose pre-modern DOIs do not resolve at doi.org, left unchanged (a registration artifact,
not an error).

## [4.0.1] - 2026-06-09 - Data-correctness patch: writer-verification panel verified against Perry 2025

### Fixed
- **The frozen writer-verification panel is now verbatim from the measured Perry 2025 ISCro4 DMS.** The offline-fallback panel
  in `atlas/writer_verify.py` previously used illustrative Z-scores (2.6/2.1/1.7) and invented control
  variants (G15D/P88R/L120E), and `_CORE_RESIDUES` used illustrative arginines. Replaced with the real values
  from `science.adz0276` Table S3: the top-3 enhancers N322P (Z 0.754), H50K (0.742), R278M (0.709), real
  near-neutral variants (V21R, S312Q, G286T), the most-deleterious variants (R132E -5.40, R137E -5.12,
  R195D -4.98), and the documented catalytic residues D11/E60/D102/D105/S241 ("Residue Groups" sheet). The
  real-DMS path (on the VM/Drive) was already correct; only the offline fallback constants were illustrative.
  Added `test_ws_wv.py::test_frozen_panel_matches_real_perry_dms_table_s3` to guard against drift.

## [4.0.0] - 2026-06-09 - The Oracle Mesh (on top of the foundation models) plus writer verification

A major bump: the substrate now composes the biomolecular foundation models under one contract and verifies
the writer enzyme itself. Each component is SHA-locked. No de-novo writer invention: score
and critique only (the pen-assemble lesson).

### Added
- **The oracle mesh.** `pen_stack/oracles/` with `OracleResult{value, provenance(model+version),
  native_uncertainty, scope_card, in_scope, extrapolating, output_kind, available, cached}`. Adapters:
  `genome.py` (AlphaGenome OOD-gated; Evo2 likelihood=claim / generation=candidate; ChromBPNet/Borzoi
  baseline), `structure.py` (AlphaFold3/Boltz-2/Chai-1/Protenix plus `consensus()` that widens the interval on
  cross-oracle disagreement), `protein_design.py` (RFdiffusion/ProteinMPNN/ESM3, all candidates), `rna.py`
  (ViennaRNA, real, hard fold-legality), `energetics.py` (bridge off-target, MC3 gate >=0.77).
  `configs/oracles/scope_cards.yaml` (11 models); deterministic version-pinned `oracle_cache/`. Guard:
  the generative candidate `as_claim()` raises. `docs/oracles.md`; `prereg/ws_o.yaml`.
- **Writer verification.** `pen_stack/atlas/writer_verify.py`: DMS- and structure-grounded variant
  scoring (measured=claimable, unmeasured=not), `blind_recovery` recovers N322P/H50K/R278M above
  measured-worse controls, and `critique_candidate` (fold/active-site/deliverable/reachable) wired into
  `verify()` as `Verdict.writer_critique`, always `no_claim=True`. `docs/writer_verification.md`;
  `prereg/ws_wv.yaml`.
- **Mesh upgrade plus delivery oracle.** `wgenome/mesh_features.py` (OOD-gated feature hook plus blind
  re-validation reporting parity vs v3.x when oracles are deferred) plus a computable
  `delivery.aav_packaging_margin` soft rule (titre drops near the AAV capsid limit). `prereg/ws_atlas.yaml`.

### Changed
- Version 3.4.0 to 4.0.0; `Verdict` gains `writer_critique`; M1 plus writer-verification note plus M2 updates.

## [3.4.0] - 2026-06-09 - The Environment (train/eval surface plus bench v0.3 plus outcome-calibration)

v3.4 turns the thin Gym interface into a full environment an AI agent can be trained and graded in, ships
Genome-Writing Bench v0.3 (multi-write-type plus adversarial robustness), and tests whether plan-confidence
actually predicts documented outcomes. Each component is SHA-locked. The environment is an
interface plus an evaluation harness (a near-one-shot decision), no RL-superiority claim.

### Added
- **The genome-writing environment.** `pen_stack/env/genome_writing_env.py` upgraded to a full
  `gymnasium.Env`: a 5-stage MDP (write_type, site, writer, cargo, delivery) whose step validity comes
  from the v3.3 verifier and whose reward is the legality gate times the L4 calibrated plan confidence, with a
  reserved abstain action for a justified refusal. `pen_stack/env/policies.py` (random plus greedy-planner).
  Passes `gymnasium.utils.env_checker.check_env`; greedy(planner) >= random and greedy-legal on the frozen
  seed set. `docs/environment.md`; `prereg/ws_env.yaml` plus lock.
- **Genome-Writing Bench v0.3.** `multi_write_type_legality` routes plus judges legality across all 6
  non-insertion write types (accuracy 1.0, ungrounded 0.0); `adversarial_robustness` probes T13-T16
  (out-of-scope-in-disguise, contradictory constraints, prompt-injection, distribution-shift): the
  verifier-backed agent passes 4/4 vs an over-confident baseline 0/4, no-fabrication holds including under
  injection. Leaderboard v0.3 robustness contrast. `prereg/ws_bench.yaml` plus lock.
- **Plan-confidence calibrated against documented outcomes.** `pen_stack/validate/outcome_calibration.py`:
  a plan-level reliability diagram plus ECE plus bootstrap-CI selective prediction on the DOI writer panel. The
  result: useful for ranking (high-confidence 0.30 vs low-confidence 0.0 documented-choice recovery, gap
  CI95 [0.17, 0.43], monotone) but poorly calibrated in absolute terms (ECE 0.71). Feeds M-UQ.
  `prereg/ws_cal.yaml` plus lock.

### Changed
- Version 3.3.0 to 3.4.0; bench 0.2.1 to 0.3; README updated for v3.4; M2/M-UQ manuscript updates.

## [3.3.0] - 2026-06-09 - The Verifier (a type checker for genome writes)

v3.3 lifts the laws of genome writing into a versioned, machine-readable rule base and exposes a single
`verify(design) -> Verdict` call (legal/illegal plus named rule plus calibrated confidence plus scope) over Python,
REST, and MCP. Each component is SHA-locked.

### Added
- **Rule base plus solver.** `pen_stack/rules/{schema,evaluators,loader,solver}.py` plus `configs/rules/*.yaml`
  (9 rules across reachability/fold/payload/multiplex/delivery), each id/kind/mechanism/param/provenance(DOI)/
  test. Evaluators delegate to the existing validated functions; a parity test proves no decision changed.
  Legality and confidence are kept as distinct axes.
- **Delivery palette.** `configs/delivery_vehicles.yaml` plus `planner/delivery_vehicles.py`: 8 vehicles
  (AAV single/dual, lentivirus, HDAd, HSV amplicon, LNP-mRNA, eVLP, electroporation) with capacity/integration/
  cargo-form/DOIs; delivery rules (hard rejects plus soft penalties plus an immunogenicity-magnitude scope flag).
- **Write-type router.** `planner/router.py` plus `configs/write_types.yaml`: dispatches insertion/
  excision/inversion/replacement/regulatory_rewrite/landing_pad_install/multiplex; unsupported types defer.
- **Verification service.** `pen_stack/verify/{service,schema}.py`: `verify(design) -> Verdict`; `POST
  /verify` plus MCP `verify_write`; `docs/verify.md`. No fabrication (every number tool-sourced).
- **Bench v0.2.1 plus agent.** T12 rule-grounded legality-with-explanation (verifier reason accuracy 1.0
  vs ungrounded 0.0); the agent submits its plan to the verifier. Bench 12/12 available, planner beats baseline
  8/8.
- **Docs:** `docs/verify.md`, `docs/rules.md`, `docs/delivery.md`.

### Changed
- Version 3.2.0 to 3.3.0 (pyproject, `__init__`, CITATION.cff). README updated for v3.3; bench badge v0.2.1.

## [3.2.0] - 2026-06-08 - A calibrated, self-aware co-scientist

The v3.2 cycle makes the genome-writing funnel trustworthy: every value carries a calibrated confidence,
an extrapolation flag, and, where the biology is beyond any tool here, an explicit out-of-scope deferral.
Each workstream is pre-registered (`prereg/ws_{uq,ep,mc,ba}.yaml`, SHA-locked) and reports its
negatives. The Genome-Writing Bench bumps to v0.2.

### Added
- **Calibrated uncertainty plus OOD.** Conformal prediction intervals (durability expression) and APS /
  Mondrian prediction sets (safety, silenced) wrapping the existing heads with no retraining
  (`pen_stack.wgenome.uncertainty`); an OOD detector that widens intervals out-of-distribution
  (`pen_stack.wgenome.ood`); selective prediction plus plan-level confidence
  (`pen_stack.validate.selective_prediction`). Held-out coverage 0.895 vs 0.90 nominal; risk-coverage accuracy
  0.739 to 0.930 under abstention. OOD across human cell types is weak (0.65-0.73), reported as a heuristic.
- **Epistemic scoping.** A three-tier status (grounded-confident / grounded-extrapolating /
  not-computable) on every agent output (`pen_stack.agent.epistemic`); a known-unknowns registry plus a scope
  matcher (`configs/known_unknowns.yaml`, `pen_stack.agent.scope`, `docs/scope.md`) that defers out-of-scope
  questions (deferral 1.0, false-defer 0.0); abstention in the agent. The no-fabrication gate is intact.
- **Mechanistic filters.** A hard target-site/PAM/att-site reachability reject
  (`pen_stack.planner.target_site`, `configs/target_sites.yaml`; controls 9/9); vehicle-specific
  delivery-sequence penalties (`pen_stack.planner.delivery_constraints`); and an off-target energetics
  model (`pen_stack.bridge.offtarget_energetics`) that beats the 0.77 baseline at held-out AUROC 0.88 on the
  comparable (core-disrupted) construction and ships as the default ranker. A reviewer-driven re-run
  (`by_negative_construction`) shows that gap is mostly the core-penalisation artifact; with the core held
  matched the non-core substitution-identity gain is real but modest (delta ~0.04, 0.687 vs 0.646). Both AUROCs
  carry a favourable-negative-set caveat (decoys derived from real off-targets; no non-recombining background).
- **Bench v0.2 plus uncertainty-aware agent.** Four trust tasks (T8 calibration, T9 selective prediction,
  T10 OOD honesty, T11 out-of-scope refusal) contrasting the uncertainty-aware agent with an over-confident
  baseline (4/4); PEN-Agent emits confidence plus epistemic status plus abstains; UI surfaces them. Bench re-SHA-locked.
- **Gymnasium interface (optional).** A thin `gymnasium.Env` over the planner (`pen_stack.env`,
  `[env]` extra) for agent-developer interoperability, interface only, no RL superiority claimed.
- **Docs:** `docs/uncertainty.md`, `docs/scope.md`, `docs/mechanistic_constraints.md`; M-UQ methods note plus
  M1/M2 manuscript updates. The Opentrons workstream is deferred to `docs/BACKLOG.md`.

### Changed
- Version 3.1.0 to 3.2.0 (pyproject, `__init__`, CITATION.cff). README updated for v3.2; badges plus bench
  v0.2. The bridge off-target default ranker is now the energetics model when its penalty table is present.

## [3.1.0] - 2026-06-04 - Publishable contributions plus an adopted benchmark

The v3.1 cycle completes (workstreams A-H). It hardens the planning benchmark, surrounds the
models with strong baselines, adds a predicted-structure safety axis, and ships the first benchmark and
grounded agent for the genome-writing side. Every workstream is pre-registered (`prereg/ws_*.yaml`,
SHA-locked) and reports its negatives.

### Added
- **Strong baselines plus safety primary-metric switch.** An endogenous-expression baseline (TRIP-trained
  Spearman 0.51 vs AlphaGenome ES-Bruce4 proxy 0.43), a multi-mark ablation (all-marks >= best single), and a
  published GSH rule-set: safe-harbour discrimination (learned 0.92, 95% CI [0.82, 0.98] vs distance-rule
  0.38, delta CI excludes zero) is now the primary safety metric; the circular `genotoxic_cis` AUROC is a
  labeled diagnostic. (`pen_stack.wgenome.gsh_baseline`, `pen_stack.validate.durability_baselines`.)
- **AlphaGenome integration.** A hosted-API provider with an offline cache; predicted-vs-measured track
  validation (HepG2 ATAC Pearson 0.85) with a score-level low-confidence flag; a 3D structural-risk
  axis from contact-map deltas (`pen_stack.wgenome.{providers,chromatin_seq,structure3d}`,
  `pen_stack.validate.seq_vs_measured`).
- **Cargo Polish.** A cargo-sequence silencing-risk scan (`pen_stack.planner.cargo_polish`).
- **Genome-Writing Bench v0.1 plus PEN-Agent.** The first writing-side benchmark (`benchmarks/`,
  `bench/run.py`) with deterministic scorers, a leaderboard, and a real LLM-agent baseline; a grounded
  write-planning state machine with a no-fabrication hard gate (`pen_stack.agent.pen_agent`).
- **Local recalibration / private-data adaptation.** Gated recalibration / fine-tuning on private
  data, in-container; the adapted model activates only if it beats the released model AND a no-skill
  baseline; the released model is provably unchanged (`pen_stack.adapt`).
- **Multiplex plus guide QC.** A pairwise translocation-risk screen (`pen_stack.planner.multiplex`,
  surfaced in PEN-Agent) and a bridge-RNA guide ranker (`pen_stack.bridge.guide_qc`).
- **Release plus dissemination.** README/badges updated for v3.1, `docs/quickstart.md`,
  `docs/positioning.md`, the leaderboard submission guide, the dissemination log, and version 3.1.0.

### Changed
- The planning benchmark's `recovery_at_k` ranking is now deterministic (stable sort plus tie-breakers).
- The LLM stack defaults to the local Ollama model on the compute tier with an automatic hosted-Nemotron
  fallback, a cooldown cache, and bounded timeouts (no more multi-minute stalls when a provider is absent).

## [3.1.0a0] - 2026-06-04 - De-circularize the planning benchmark (gate)

The v3.1 cycle (publishable contributions plus an adopted benchmark) opens with its gate: de-circularizing the
Phase-3 planning benchmark before anything builds on it.

### Changed
- **The Phase-3 "discriminating-stratum recovery@10 = 1.00 vs 0.00 (McNemar p, CI)" is now labeled
  definitional, not predictive,** everywhere (README, manuscript abstract, `prereg/paper3.yaml`,
  `validate/paper3_benchmark.py` docstring). An on-target identity term dominates the score, so the planner
  ranks the goal's own gene first by construction. Documented in `docs/benchmark_circularity.md`.
- The intent result is reframed as a specification-compliance correctness table (`validate/intent_specification.py`,
  7/7), with no recovery/p-value/CI language.

### Added (the non-circular replacements)
- **Blind safe-harbour site discovery (the new lead result):** `validate/blind_gsh_discovery.py` plus
  `configs/gsh_validated_heldout.yaml` (5 DOI-validated held-out GSH, gene-anchored to hg38) plus a
  frozen/SHA-locked `data/gsh_matched_controls.parquet`. Run genome-wide (no on-target term), the planner's
  writability separates validated GSH from matched-context controls at AUROC 0.92 (safety-only 0.50).
- **Diversified writer-family recovery:** `validate/writer_recovery.py` plus `data/writer_panel.csv` (8 writes,
  4 families, DOIs). recovery@1 = 1.0 vs prevalence 0.25 (smallest-capacity DSB-free writer that fits
  the cargo).
- **Within-locus ranking** (descriptive): `validate/within_locus_ranking.py`, AAVS1 documented bin at the
  93rd within-locus percentile (top quartile); CLYBL at the 34th (a negative result).
- **Consolidated report** `scripts/p3_benchmark_report.py` to `out/ws_a_report.md`; `prereg/ws_a.yaml` plus
  SHA lock. Gate G-A is met: blind AUROC reported, no circular claims remain.

## [Unreleased] - 2026-06-03 - Reframing, repository polish, coverage, hybrid LLM

### Added
- **Hybrid LLM backend** (`pen_stack/rag/llm.py`, `configs/llm.yaml`): a strong hosted model for
  reasoning/agent/Q&A (NVIDIA Nemotron, OpenAI-compatible, free) with automatic fallback to the local
  Ollama model, then to the deterministic no-LLM path. One `provider` switch. The agent and RAG were
  refactored onto a single provider-agnostic `chat()` (NVIDIA tool-call IDs and Ollama native message
  threading both handled). The LLM stays non-load-bearing (every number/citation still comes from
  validated tools), so the model choice does not affect scientific reproducibility; it only improves
  orchestration (Nemotron planned a goal in 2 tool calls vs the local 7B's 8-call loop). Core scientific
  compute stays local/VM and uses no LLM. API keys are read from an env var or a gitignored file and
  are never committed.

### Changed
- **Paper 4 reframed to its scope.** `pen-bridge` is positioned as the first measured-data-validated
  tool that nominates and ranks candidate off-target locations for bridge recombinases, a
  screening tool, not a quantitative safety calculator. The AUROC 0.77 vs 0.62 result is stated with
  its caveat (favourable negative set; mostly tests core integrity), and the magnitude limitation
  (sequence-risk does not rank recombination amount, rho ~0.30) is named as the single most important
  limitation. Application-Note tier, first-of-its-kind for an unoccupied gap; the Writable Genome remains
  the flagship. Manuscript plus `prereg/paper4.yaml` plus summaries updated.
- **Variant-effect reframed:** the DMS recovers KNOWN enhancers (a catalogue feature), it is not a novel
  variant-design method; EVOLVEpro is the engine to wrap when generating new variants.
- **Repository made clean ASCII:** removed all decorative emojis and em/en dashes and other non-ASCII
  punctuation across code, docs, configs, and manuscripts (box-drawing tree characters kept).

### Added
- 72-system ortholog characterisation (`bridge/ortholog_screen.py`), explicitly descriptive (Table S1 has
  no activity label): sequence-similarity organisation vs the validated standout ISCro4 (IS621 ranks most
  similar, a sanity check). Exploratory secondary result, N ~72.
- Coverage: CI runs `pytest --cov`, uploads to Codecov, and publishes a self-hosted coverage badge
  (`tools/make_coverage_badge.py` to `.github/badges/coverage.svg`). Unit-test coverage of the core logic
  is 69% (integration-only modules that need GPU/VM/network/LLM are excluded via `[tool.coverage.run]`).
- Professional, emoji-free README with connected-repo badges (genome-atlas / mech-class / pen-score /
  pen-assemble / pen-compare), an architecture diagram, and the problem/gaps explanation.

## [3.0.0a5] - 2026-06-02 - Phase 1.5 (Bridge-recombinase off-target engine, Paper 4)

The first public instrument: a bridge-recombinase off-target screening tool.

### Added
- **Off-target engine** (`pen_stack/bridge/offtarget.py` plus `configs/bridge_offtarget_profile.yaml`):
  a genome-wide hg38 pseudosite scan (CT-core seed, per-chromosome, memory-bounded) plus a position-weight
  risk model grounded in the published mechanism. Beats naive Hamming: AUROC 1.00 vs 0.59 at
  separating core-preserving (real-risk) from core-disrupting (abolished) sites. Exposes
  `predict_offtargets(family, site)`, completing the Phase-3 Planner cargo hook.
- **Fold / cross-loop QC** (`bridge/fold_qc.py`): a ViennaRNA fold (verified MFE on a 190-nt design) plus
  TBL/DBL cross-loop complementarity.
- **Activity framework** (`bridge/activity.py`): an exploratory DMS plus 72-system trainer (deferred; data paywalled).
- **`pen-bridge`** (`bridge/pipeline.py`, `bridge/cli.py`, `/bridge/design` API): wraps the Arc
  BridgeRNADesigner (verified) and adds the off-target plus QC layer.
- `validate/paper4_validation.py` plus `scripts/p4_genome_scan.py`; `prereg/paper4.yaml` plus SHA lock.

### Notes
- **Phase 1.5 complete.** The pre-registered criteria were met (or gated): the off-target engine,
  the ViennaRNA fold, and the designer wrap are verified on the VM (real hg38 scan: chr22 in ~21 s). The blind
  recall of Perry 2025's measured off-targets and the DMS/activity model are gated on the paywalled
  Perry 2025 supplementary (drop in via `ingest.load_offtarget_profile`). This completes the deferred Phase-2
  Section 2.4 and Phase-3 Section 3.2 hooks. 68 tests green; ruff clean. All program phases (0, 1, 1.5, 2, 3) now done.

## [3.0.0a4] - 2026-06-02 - Phase 3 (The Write Planner plus agentic platform, Paper 3)

Inverse design plus the paper-defining recovery@k benchmark plus the agentic platform.

### Added
- **Inverse-design optimiser** (`pen_stack/planner/optimize.py`, `configs/intent_weights.yaml`): an
  `edit_intent`-conditioned objective whose `target_gene_sign` flips whether hitting the target gene is
  penalised or rewarded, so the same TRAC site ranks #1 (knock-in) vs #101 (safe-harbour).
- **Cargo/delivery** (`planner/cargo.py`, `planner/delivery.py`): a donor spec plus size check plus a delivery rule
  table; bridge/seek off-target via an optional Phase-1.5 hook (pending until 1.5).
- **End-to-end Planner** (`planner/pipeline.py`, `report.py`, `/plan` API, `pen-stack plan` CLI): ranked,
  fully traceable plans with per-field provenance.
- **Two-stratum recovery@k benchmark** (`validate/paper3_benchmark.py`, `data/benchmark_panel.csv`,
  `prereg/paper3.yaml`): discriminating stratum planner 1.00 vs baseline 0.00, McNemar p=0.0156, gap CI
  [1.0,1.0] excludes zero; control tie 0.67=0.67. The panel is cited to Europe-PMC-verified sources.
- **Forward hypotheses** (`validate/forward_hypotheses.py`): date-stamped novel F8/SERPINA1/CISH/HBA1
  proposals plus a grounded cited ranking.
- **Agentic platform:** `agent/tools.py` plus `agent/orchestrator.py` (Ollama tool-calling, an auditable trace,
  no-fabrication, refusals), `agent/mcp_server.py` (fastmcp), `docker-compose.yml` plus `docker/ui.Dockerfile`
  plus a Streamlit Agent page plus `docs/DEPLOY.md`/`docs/MCP.md`, `validate/agent_eval.py`.
- Shipped `data/curated/gene_coords.parquet` (GENCODE-derived) so tools work in any container.

### Notes
- **Phase 3 complete.** The pre-registered criteria were met (`prereg/paper3.yaml` plus `SHA256_LOCK_phase3.json`).
  The agent is verified on the VM in LLM mode (no-fabrication plus plan-equivalence plus refusals all pass). 63 tests
  green; ruff clean. Wet-lab (3.7) skipped, non-gating. The bridge off-target hook completes with Phase 1.5.

## [3.0.0a3] - 2026-06-02 - Phase 2 (Writer Atlas plus Unified Stack, Paper 2)

The broad, cross-family Writer Atlas, the writer-to-locus cross-link, and the installable platform.

### Added
- **Writer Atlas** (`pen_stack/atlas/expand.py`, `atlas.parquet`): 33,370 systems across 8 families
  (31,885 IS110/IS1111 orthologs plus curated cores/reps), every row confidence-tagged plus at least 1 source DOI,
  targeting metadata inherited from the WT-KB. `configs/atlas_families.yaml` drives the UniProt queries.
- **Mechanism at scale** (`pen_stack/mech/`): ported the audited 18-family Pfam whitelist v1.2.1; composite
  co-occurrence rules; core agreement 1.00 vs audited labels; conflicting calls go to a review queue.
- **Therapeutic readiness** (`pen_stack/score/therapeutic.py`): deliverability/cargo/human-cell axes,
  components retained (ISCro4 326aa to AAV).
- **Cross-link** (`pen_stack/atlas/crosslink.py`): bidirectional writer-to-locus queries; AAVS1 held-out
  check passes (0.90 writability plus bridge-reachable). Per-family caches for k562/hepg2/hspc.
- **Variant proposal** (`pen_stack/atlas/variant_propose.py`): a point-mutation framework plus a retrospective
  harness, no chimeras; DMS model pluggable (Phase 1.5).
- **PEN-MONITOR** (`pen_stack/monitor/`): a Europe PMC living-database engine; the back-test surfaces ISPpu10;
  never auto-edits the atlas; every candidate cited.
- **Grounded RAG** (`pen_stack/rag/`, `pen_stack/agent/guardrails.py`): numbers from tool calls, claims
  cited, clinical directives refused; an optional Ollama/Qwen phrasing layer (presentation only).
- **Stack:** unified CLI subcommands, a FastAPI server (`pen_stack/server/api.py`), a Streamlit platform UI
  (Writer Atlas plus Ask pages), an mkdocs site plus 4 use-case tutorials. 46 tests green; ruff clean.

### Notes
- **Phase 2 complete.** The pre-registered criteria were met (`prereg/paper2.yaml` plus `SHA256_LOCK_phase2.json`);
  the atlas Zenodo DOI is pending author upload. Verified on the VM (Docker): API, UI (:8501), RAG with Qwen.

## [3.0.0a0] - 2026-06-01 - Phase 0 (in progress)

A fresh v3.0 monorepo. It supersedes the v1.0 platform repository (archived) and consolidates the five prior
repositories (`genome-atlas`, `mech-class`, `pen-score`, `pen-assemble`, `pen-compare`) as provenance.

### Added
- A monorepo scaffold: 13 modules (`atlas`, `mech`, `score`, `wgenome`, `planner`, `bridge`, `monitor`,
  `rag`, `agent`, `ui`, `data`, `validate`, `server`), `pyproject.toml`, a Docker image spec, the `penctl`
  laptop-to-VM orchestrator, CI, `configs/`, `prereg/`.
- `docs/INFRA.md`: the three-tier (laptop / VM / Drive) Docker-only, SFTP-only workflow.
- `configs/llm.yaml`: a single LLM switch (Ollama plus Qwen2.5-7B-Instruct, Apache-2.0).
- `configs/datasets.yaml`: pinned dataset accessions plus verified IDs (see VERIFICATION_REPORT_v3.0).
- **WT-KB** (`pen_stack/atlas/`): 8 fully-sourced writer families with reachability tiers; the schema enforces the at-least-1-DOI sourcing rule.
- **Re-grounded axes** (`pen_stack/score/recalibrate.py`, `configs/score_axes.yaml`): `S_Cargo` from measured bp, `S_Prog` from targeting modality, `length_aa` backfilled, no per-enzyme overrides.
- **Canonical universe** (`pen_stack/atlas/universe.py::assemble`): one path joining the 1,058-entity universe plus WT-KB plus crosswalk; a cross-module consistency test.
- **Descriptive scorecard** (`pen_stack/atlas/scorecard.py`): reframed from the circular certification; blind concordance recovers ISCro4 as the bridge standout without naming it. 21 tests green.

### Notes
- Independent verification of all datasets/IDs/DOIs/tools completed: no critical errors in the v3.0 plan
  (full report in `Final_Part_v3.0/VERIFICATION_REPORT_v3.0.md`).
- **Phase 0 complete.** All pre-registered success criteria were met (`prereg/phase0.yaml` plus SHA lock).
