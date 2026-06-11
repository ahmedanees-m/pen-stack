# Changelog

All notable changes to PEN-STACK are documented here. This file follows
[Keep a Changelog](https://keepachangelog.com/) and the program's phase structure.

## [5.12.0] - 2026-06-11 - v5.12 release: The Closed Loop (autonomy Level 3)

**Closed-Loop arc, Cycle 6 of 7.** Integrate everything into one continual design→build→test→learn cycle —
humans/lab in control, no fabrication, drift-aware. Reaches **autonomy Level 3** (the program's honest ceiling).
Workstreams WS-{LOOP,CONTINUAL,DRIFT} (+ WS-DEMO, WS-AUTONOMY), SHA-locked.

### Added
- **WS-LOOP** — `pen_stack/loop/cycle.py`: `run_loop(goal, cell_state, …)` orchestrates every prior cycle each
  round — generate (v5.8) → decide/batch (v5.10) → **safety-gated** export (v5.7 + v5.11) → run (sim-lab v5.11 /
  real lab) → ingest (v4.5 gate) → drift (v5.12) → continual learn (v5.12). **Gated**: safety, build, and
  belief-admission each await the `approver`. Returns `autonomy_level=3`, `human_in_control=True`,
  `no_fabrication=True`. A hazardous candidate is discarded by the safety-gated pipeline before it is ever run.
- **WS-DRIFT** — `pen_stack/loop/drift.py`: `detect_drift(designs, results)` compares the v5.9 twin's predictions
  vs observed readouts; growing miscalibration → `severity:"high"` → `inflate_intervals` (widen, don't over-trust).
- **WS-CONTINUAL** — `pen_stack/loop/continual.py`: `continual_update(...)` recalibrates trust + twin + immune
  proxies on **admitted outcomes only**; each update is **versioned + reversible** (`rollback_to`); high drift
  widens intervals; an admitted immune measurement **with a CI** can graduate a v5.6 proxy → outcome-validated.
  Recalibration, **not** foundation-model retraining.
- **WS-DEMO + WS-AUTONOMY** — `loop_converges_faster_than_random` reports the active-vs-random convergence with a
  bootstrap CI (retrospective/simulated, honest either way); `docs/autonomy.md` asserts the **Level-3 criteria**
  (closed loop · human in control at every gate · anomaly flagging · no fabrication) and that Levels 4/5 are
  **not** claimed.
- **WS-BENCH** — bench **v0.3.8**: new `closed_loop` hard-gate task — the gate is the loop's integrity (gated
  end-to-end run + no-fabrication + Level-3 human-in-control + drift detection + versioned/reversible continual
  learning); an ungated autopilot fails by construction. Convergence reported informationally.
- Docs: `docs/{closed_loop,autonomy}.md`; prereg `ws_{loop,continual,drift}` + SHA locks; deposit `phase_5.12/`.

### Notes
- The loop is **Level 3 — closed, but with humans/lab in control at every gate, NOT autonomous.** It runs in
  silico via the sim-lab (a real lab attaches at the same interface); continual learning recalibrates rather than
  retrains; drift covers calibration/residual shift, not all failures; the convergence demo is retrospective/
  simulated, reported with CIs.

## [5.11.0] - 2026-06-11 - v5.11 release: The Build Interface (digital→physical bridge)

**Closed-Loop arc, Cycle 5 of 7.** Make designs executable and results ingestible — loop-ready, lab-optional,
safety-gated, with the immune-risk profile attached as protocol metadata. Workstreams WS-{PROTO,INGEST,SIMLAB},
SHA-locked.

### Added
- **WS-PROTO** — `pen_stack/build/protocol.py`: `export_protocol(design, experiment, target, actor)` for
  Opentrons / PyLabRobot / cloud-lab. Runs `verify()` **first**: a safety-`refuse` or illegal design raises
  **`ProtocolExportError`** (no export path for a flagged design); a cleared design is emitted as a **DRAFT**
  ("human/lab review required") carrying the v5.6 immune profile + provenance in its metadata. Never auto-run.
- **WS-INGEST** — `pen_stack/build/ingest.py`: `ingest_result(result, ...)` validates a result (assay / readout /
  provenance) and turns it into a **quarantined measured edge Candidate**; the ONLY path into the curated
  world-model is the v4.5 gate (`gate_admit`) — automated checks **and** explicit human approval. No auto-edit
  (Principle 1). Immune measurements can begin validating the v5.6 proxies on a later pass.
- **WS-SIMLAB** — `pen_stack/build/simlab.py`: `run_simulated(protocol_ir, design, cell_state)` executes a
  protocol in silico (samples from the v5.9 twin + measurement noise), **labelled `SIMULATED`**, so the closed
  loop (v5.12) runs end-to-end **export → sim → ingest** without hardware; never enters the world-model as
  measured truth.
- **WS-BENCH** — bench **v0.3.7**: new `protocol_safety` hard-gate task (`pen_stack/validate/protocol_safety.py`)
  — a cleared design exports with immune metadata, a safety-refused/illegal design is blocked, and the simulated
  loop completes with quarantined SIMULATED results; an ungated exporter (which would emit the hazardous protocol)
  fails by construction.
- Docs: `docs/build_interface.md`; prereg `ws_{proto,ingest,simlab}` + SHA locks; deposit `phase_5.11/`.

### Notes
- PEN-STACK emits protocols and ingests results; it does **not** run experiments — protocols are drafts requiring
  human/lab review, results enter only through the gate, and the simulated lab is for development / loop-validation,
  never a substitute for real data. Export is hard-blocked for anything the safety gate flags.

## [5.10.0] - 2026-06-11 - v5.10 release: The Experiment Designer (active learning / EIG)

**Closed-Loop arc, Cycle 4 of 7.** The "Learn" brain of a self-driving lab: turn *"I'm uncertain"* into *"run
this experiment next."* Reads the calibrated v5.9 twin's uncertainty + the v5.6 immune labels, scores each
candidate experiment by expected information gain, assembles a diverse batch, and proves on held-out data — with
CIs — that this learns faster than random/greedy (reporting honestly when it does not). Workstreams
WS-{ACQ,DESIGN,VALIDATE}, SHA-locked.

### Added
- **WS-ACQ** — `pen_stack/active/acquire.py`: `expected_information_gain` (reducible uncertainty from the twin's
  predictive distribution; `≥ 0`, monotone in uncertainty), `predictive_entropy` (from the twin's interval width),
  and **`immune_voi`** — value of information for **validating an immune PROXY axis** (v5.6): an experiment that
  would measure a still-proxy axis is high-VOI (turns proxy → outcome-validated). `acquisition_score` is fully
  traceable to twin quantities + v5.6 labels; deterministic; no fabricated values.
- **WS-DESIGN** — `pen_stack/active/design.py`: `select_batch` greedily maximises acquisition **minus a
  redundancy penalty** (shared design facets) → a **diverse** batch (not k copies of the most-uncertain point);
  each experiment carries its expected info gain.
- **WS-VALIDATE** — `pen_stack/active/validate.py`: `retrospective_active_learning` simulates active vs random vs
  greedy campaigns on a held-out split, reports mean±CI learning curves and a **bootstrap CI on the curve-area
  gap**; `active_beats_random` only when the CI excludes zero — else the not-yet-useful negative is reported.
- **WS-BENCH** — bench **v0.3.6**: new `experiment_design` hard-gate task — the gate is the Learn engine's
  honesty + falsifiability (twin-sourced EIG monotone in uncertainty + immune-VOI for proxy validation + diverse
  batch + retrospective active-vs-random with reps+CI); a random selector fails by construction. Active-beats-
  random is reported informationally.
- Docs: `docs/experiment_design.md`; prereg `ws_{acq,aldesign,alvalidate}` + SHA locks; deposit `phase_5.10/`.

### Notes
- The experiment designer is only as good as the v5.9 twin + v5.6 labels it queries; its advantage is validated
  **retrospectively** with CIs and reported honestly when absent. It chooses informative experiments but **does
  not run them** — prospective benefit awaits a lab partner (v5.11+). No autonomy claim.

## [5.9.0] - 2026-06-11 - v5.9 release: The Digital Twin (calibrated outcome prediction)

**Closed-Loop arc, Cycle 3 of 7.** The missing layer: *what does the cell do after the write?* — predicted with
calibrated honesty. The twin computes what mechanism allows, adds an in-distribution virtual-cell estimate
(OOD-gated), screens immune outcome from the v5.6 profile, and is explicit about its boundary at phenotype.
Workstreams WS-{VCELL,MECH,OUTCOME,CAL}, SHA-locked.

### Added
- **WS-VCELL** — `pen_stack/oracles/vcell.py` + scope cards `state`/`scgpt`: `predict_response(cell_state,
  perturbation, model)` wraps **Arc STATE** / **scGPT** under the v4.0 `OracleResult` contract. A
  perturbation-response prediction is a **candidate**, OOD-gated (a context outside the documented envelope →
  `extrapolating`), cached/deferred (value `None` when absent — never fabricated). Encodes the field's own result
  (Arc Virtual Cell Challenge): perturbation models don't yet consistently beat naive baselines.
- **WS-MECH** — `pen_stack/twin/mechanistic.py`: `cassette_expression` = `promoter_strength × copy_number ×
  accessibility` (closed-form steady state); assumptions + scope flags attached; **physics where computable, NOT
  a phenotype**.
- **WS-OUTCOME** — `pen_stack/twin/outcome.py`: `predict_outcome(design, cell_state)` fuses mechanism +
  in-distribution virtual-cell response + the v5.6 immune profile into one prediction with an interval that
  **widens under OOD**, an immune-outcome dimension, and an explicit **phenotype / in-vivo-magnitude boundary**.
  In-vivo durability may be **conditioned on the grounded pre-existing-NAb axis** (no invented immune numbers);
  `output_kind="candidate"`.
- **WS-CAL** — `pen_stack/twin/calibrate.py`: `calibrate_outcome(...)` reports calibration **two-sided** — interval
  coverage + a bootstrap CI on the MAE gap vs a naive mean baseline; the twin "beats" naive **only when the CI
  excludes zero**, else the negative is reported verbatim; abstains at `N < 3`.
- **WS-BENCH** — bench **v0.3.5**: new `outcome_prediction` hard-gate task (`pen_stack/validate/outcome_prediction.py`)
  — the gate is the twin's **honesty properties** (two-sided calibration + OOD widening + immune dimension +
  phenotype out-of-scope), which an overconfident predictor fails by construction; twin-vs-naive skill is reported
  informationally on a labelled synthetic stream (no public perturbation-outcome calibration set exists).
- Docs: `docs/digital_twin.md`; prereg `ws_{vcell,mech,outcome,twincal}` + SHA locks; deposit `phase_5.9/`.

### Notes
- The twin is a **hypothesis engine, not an oracle of truth**: predictions are candidates with intervals;
  phenotype, in-vivo behaviour, immunogenicity *magnitude*, and durability beyond the computable stay
  scope-flagged. The interval is a heuristic band, **not** a trained conformal interval (no public outcome
  calibration set). Immune-outcome is sourced from v5.6, never invented.

## [5.8.0] - 2026-06-11 - v5.8 release: The Live Agent & Generative Designer

**Closed-Loop arc, Cycle 2 of 7.** PEN-STACK turns from a *checker* into a grounded *designer*: it generates
candidate end-to-end writing systems, keeps only those that pass safety + legality + calibration
(verifier-as-discriminator), and returns the **Pareto frontier** of real tradeoffs — in which immunogenicity-risk
is, for the first time, a **grounded** axis sourced from the v5.6 profile rather than a placeholder. Workstreams
WS-{ORCH,GEN,PARETO,BENCH}, SHA-locked.

### Added
- **WS-GEN** — `pen_stack/design/{space,generate}.py`: `generate_designs(goal|candidates)` PROPOSES candidates
  (`candidate_space` = the validated Phase-3 planner × the compatible delivery palette) and the v3.3 `verify()`
  — now **safety-gated (v5.7)** + legality + calibration + immune-profiled — DISPOSES. A candidate survives only
  if **legal AND safe** (`clear`/`flag`); hazardous (`refuse`/`escalate`) and illegal proposals are **discarded,
  never returned** (the `as_claim()` guard generalised to whole designs). Survivors carry calibrated confidence,
  the v5.6 immune profile, the safety decision, and `output_kind="candidate"` — never asserted to work.
- **WS-PARETO** — `pen_stack/design/pareto.py`: `pareto_front(designs)` over `(efficiency, durability, safety,
  deliverability, neg_immune_risk, neg_cost)`. **`neg_immune_risk` is grounded by the v5.6 profile** — the
  worst-case per-axis in-scope score with the per-axis uncertainty carried as a band; the profile is never
  collapsed into one number and the in-vivo magnitude stays scope-flagged (`in_vivo_magnitude_unknown`).
- **WS-ORCH** — `pen_stack/agent/orchestrator_live.py`: `orchestrate(goal)` — plan → generate → call an oracle
  (cache-first/replayable) for a critique signal → dispose via `verify()` → refine. Every number is tool-sourced;
  a seed-locked replay reproduces the trace (replay is the CI default); no fabrication.
- **WS-BENCH** — bench **v0.3.4**: new `generative_design` hard-gate task (`pen_stack/validate/generative_design.py`)
  — on a frozen mixed pool (benign + hazardous ricin payload + illegal oversize/mRNA-incompatible), the grounded
  designer returns only legal+safe+calibrated+immune-profiled survivors on a grounded-immune-axis Pareto frontier,
  while an ungrounded generator ships hazardous/illegal designs and fails by construction.
- Docs: `docs/generative_design.md`; prereg `ws_{gen,pareto,orch}` + SHA locks; deposit `phase_5.8/`.

### Notes
- A generated output is a **candidate, never a claim**; novelty is bounded by the oracles' validity and the
  rules' legality, and never asserted to work. The immune-risk Pareto axis is a worst-case **screen** — the
  per-axis v5.6 profile (with its validation labels) remains authoritative; in-vivo magnitude is a known-unknown.

## [5.7.0] - 2026-06-11 - v5.7 release: The Guardian (biosecurity / dual-use safety gate)

Opens the **Closed-Loop arc (Cycle 1 of 7)**. Before PEN-STACK moves toward "build", it is made **safe by
construction**: every design submitted to `verify()` first passes a biosecurity / dual-use screening gate that
refuses or escalates select-agent, pandemic-pathogen, and controlled-toxin signatures — with function-based and
chimera checks that catch AI-designed homologs homology alone would miss — while legitimate therapeutic designs
pass untouched. Orthogonal to (and complementary with) the v5.1–v5.6 immune-risk profile. Workstreams
WS-{SCREEN,POLICY,INTEGRATE,REDTEAM,BENCH}, SHA-locked.

### Added
- **WS-SCREEN** — `pen_stack/safety/{registry,screen}.py` + `configs/safety/hazard_registry.yaml`: a curated,
  **version-pinned** `HazardRegistry` (`registry_version`) and three+ screens returning typed, provenanced
  `ScreenHit`s — `function_flag` (toxin / pathogen-essential **functions**, the screen that catches AI-homologs
  at low identity), `taxon_flag` (regulated-pathogen taxa), `chimera_context` (hazardous assembly of benign
  parts + split-hazard), and `sequence_homology` (delegated to a wrappable external screener — IBBIS Common
  Mechanism / SecureDNA-style; in-repo baseline is an honest no-op). **Signatures are function/family/taxon-level
  only** (public Pfam accessions + public control-list references: 42 CFR 73 / 7 CFR 331 / 9 CFR 121 / Australia
  Group / HHS P3CO/DURC) — no hazard sequences, no synthesis/enhancement detail. **All 14+ Pfam accessions
  independently verified against EBI InterPro before reliance; one error (PF01375, mislabeled anthrax — it is
  heat-labile/cholera enterotoxin) caught and corrected; anthrax PA re-sourced from UniProt P13423.**
- **WS-POLICY** — `pen_stack/safety/{policy,gate,audit}.py` + `configs/safety/policy.yaml`: `SafetyVerdict`
  {clear, flag, refuse, escalate}; `safety_gate(design, actor=…)` = strip-framing → screen → decide → audit;
  ambiguous dual-use (gain-of-function) **escalates** to human review (HHS P3CO/DURC), not auto-refuse; an
  append-only **hash-chained, tamper-evident** `audit_log` (+ `verify_chain`) storing a design *digest*, not the
  design. Re-framing as "defensive research" cannot flip refuse→clear (the artifact decides, not the wording).
- **WS-INTEGRATE** — `Verdict.safety: SafetyVerdict`; `verify(design, actor=…)` runs the gate **first** and a
  `refuse` **short-circuits** (the design is returned un-evaluated, not scored/critiqued). No-fabrication holds:
  hits come only from the versioned registry.
- **WS-REDTEAM** — `pen_stack/safety/redteam.py`: adversarial harness (AI-homolog, split-hazard, reframing,
  chimera) + reframing-stability pairs; reports set size + caught count.
- **WS-BENCH** — bench **v0.3.3**: new `safety_screening` hard-gate task (`pen_stack/validate/safety_screening.py`)
  — benign therapeutics 0 false refusals, hazards refused/escalated at correct severity, evasions never `clear`;
  beats a no-safety baseline (1.0 vs 0.33) by construction. Frozen probes/registry/policy SHA-locked into the
  bench. Bench now **17/17 available, planner beats naive on 13/13**.
- Docs: `docs/responsible_use.md` + `docs/biosecurity.md`; prereg `ws_{screen,policy,redteam}` + SHA locks;
  deposit `phase_5.7/` (execution summary + independent data/ID verification record).

### Notes
- The safety gate is a **defensive safeguard, not a guarantee**, and **not a substitute for institutional
  biosafety / IBC review**; signatures are versioned and exploit detail is intentionally not published.
- Orthogonal to the immune-risk profile: the Guardian asks *"is this design hazardous/dual-use?"*; the immune
  profile asks *"will the patient react?"*. Both attach to every `Verdict`; neither subsumes the other.

## [5.6.0] - 2026-06-11 - v5.6 release: Immunology completion & calibration (anti-PEG · proxy honesty · unified profile)

Finishes the delivery-immunology arc (v5.1–v5.5): adds the missing **anti-PEG** axis, **calibrates** the
proxies honestly, and exposes a **unified per-design immune-risk profile** that never collapses into one number.
Workstreams WS-{PEG,CALIB,PROFILE} (+ optional WS-EXT), SHA-locked.

### Added
- **WS-PEG** — `pen_stack/planner/antipeg_oracle.py` + `configs/antipeg.yaml`: pre-existing/induced anti-PEG
  antibodies gate **re-dosing** of PEGylated LNP. Population prevalence range (25–72 %) →
  `preexisting_antipeg_score = 1 − midpoint/100`, range surfaced as `native_uncertainty`; **abstains** for
  non-PEGylated vehicles. Serosurvey DOIs Crossref-verified (Chen 2016 `10.1021/acs.analchem.6b03109`, Yang &
  Lai `10.1002/wnan.1339`, Armstrong `10.1002/cncr.22739`, Kozma `10.1016/j.addr.2020.07.024`). Scope card `antipeg`.
- **WS-CALIB** — `pen_stack/validate/immune_calibration.py`: `calibrate_axis()` (Spearman ρ + percentile
  bootstrap CI) labels an axis **outcome-validated only when the CI excludes zero**, else `weak_proxy`, and
  `mechanistic_proxy` when N < 6. With no sufficient public paired (proxy, observed) dataset, **every axis is
  honestly labelled a mechanistic/population proxy** — the label travels with the profile. (No fabricated
  outcome data; machinery proven on synthetic input.)
- **WS-PROFILE** — `pen_stack/planner/immune_profile.py` + **`Verdict.immune_profile`**: a per-design **vector**
  of all axes (genotoxicity, CD8 epitope, innate, pre-existing NAb, anti-PEG), each with its own value +
  uncertainty + scope + validation label. **`collapsed_score is None`** (never fused — asserted); known-unknowns
  listed; abstaining axes report `None`.
- **WS-EXT** — a documented qualitative **route/immune-privilege modifier** (eye/CNS lower realized
  immunogenicity vs systemic; Streilein 2003 `10.1038/nri1224`; no fabricated magnitude); **CD4/MHC-II helper
  epitopes**, **pre-existing capsid-specific T-cell immunity**, and **complement/CARPA** registered as
  known-unknowns. `prereg/ws_{peg,calib,profile}.yaml` + SHA locks.

### Changed
- Version 5.5.0 -> 5.6.0 (minor — additive); `cite.curated_dois()` ingests the anti-PEG + immune-privilege DOIs.

### Honesty invariant (unchanged)
- Every axis is a **relative-risk screen** (sequence/mechanistic or population proxy), labelled as such until
  outcome-validated; the profile is **never** collapsed into one number; patient-specific titer, post-dose-1
  induced immunity, and exact in-vivo magnitude stay **known-unknowns**.

## [5.5.0] - 2026-06-10 - v5.5 release: Anti-vector seroprevalence oracle (the last immune axis, from data)

Completes the computable delivery-immunology axes. **Pre-existing humoral immunity** (B-cell / neutralizing
antibody) to a viral capsid is the one immune axis that *cannot* be computed from sequence — it is a population
prevalence from natural exposure. v5.5 grounds it in published **serosurvey data**. Workstream WS-SEROPREV,
SHA-locked.

### Added
- **WS-SEROPREV table** — `configs/seroprevalence.yaml`: curated population NAb/IgG seroprevalence per serotype
  as **ranges** (region/age/assay variation) with DOIs — AAV (Calcedo 2009, Boutin 2010), adenovirus type 5
  (Mast 2010), HSV-1 (Looker 2015), VSV (negligible).
- **WS-SEROPREV oracle** — `pen_stack/planner/seroprevalence_oracle.py`: `seroprevalence_oracle(vehicle,
  serotype=None)` → `OracleResult`. `preexisting_score = 1 − midpoint(seroprevalence)/100`; the range width is
  surfaced as `native_uncertainty`. Non-viral → 1.0 by mechanism; unknown → **abstains**.
- **Wired into the pre-existing axis** — `safety_efficacy_profile()` folds the computed seroprevalence score
  into the `preexisting_immunity` sub-axis **only for in-vivo vehicles** (serum NAb neutralises the vector in
  vivo; ex-vivo transduction in a dish is not reached by host antibody → reported but muted). `seroprevalence_score`
  surfaces the raw value.
- **Result (from data):** adenovirus has the highest pre-existing seroprevalence (40–90%, score 0.35), AAV
  intermediate (30–60%, 0.55), VSV/lentivirus negligible (0–5%, 0.975) — the documented ordering quantified
  from serosurveys. `prereg/ws_seroprev.yaml`.

### Changed
- Version 5.4.0 -> 5.5.0 (minor — additive data-grounded oracle); `cite.curated_dois()` ingests the
  seroprevalence DOIs.

### Honesty invariant (unchanged)
- A **population** prevalence (a range; region/age/assay-dependent), **not** a given **patient's** NAb titer /
  sero-status (a clinical test, patient-specific → a known-unknown); the **humoral (B-cell)** axis only,
  distinct from the v5.3 T-cell epitope load. No patient-specific magnitude predicted.

## [5.4.0] - 2026-06-10 - v5.4 release: Computed innate-sensing scorer (completes the computable immune axes)

The third computed delivery-immunology signal, after v5.2 genotoxicity and v5.3 capsid epitope load. Innate
sensing of a delivered nucleic acid is computed directly from the **cargo sequence** — CpG O/E for DNA (TLR9),
U-richness + dsRNA for mRNA (TLR7/RIG-I) — covering every cargo form. Workstream WS-INNATE, SHA-locked.

### Added
- **WS-INNATE scorer** — `pen_stack/planner/innate_sensing.py`: `cpg_observed_expected()` (Gardiner-Garden &
  Frommer) + `innate_sensing(seq, cargo_form)` → `OracleResult`. **DNA** → CpG O/E (vertebrate genome ~0.2
  tolerated; non-depleted DNA → 1 TLR9-stimulatory), `innate_score = max(0, 1 − CpG_O/E)`. **mRNA** → uridine
  fraction + ViennaRNA dsRNA pairing (graceful when ViennaRNA absent), flagged **partial/`extrapolating`**.
  **RNP** → minimal/transient. Abstains on empty / unrecognised input (never fabricates). Pure sequence
  computation — no external data, runs in CI.
- **Surfaced in `verify()`** — when a design supplies `cargo_seq`, the computed innate load is attached as a
  `cargo_innate_sensing` scope flag (cargo form from the writer output form, else the vehicle's first
  compatible form) and added to `delivery_profile.cargo_innate`. No confidence added; the realized in-vivo
  innate response stays a known-unknown.
- Scope card `innate_sensing`; `prereg/ws_innate.yaml`. `cite.curated_dois()` ingests the innate provenance
  DOIs (CpG-TLR9 10.1073/pnas.161293498, CpG-depleted AAV 10.1172/JCI68205, RNA modification
  10.1016/j.immuni.2005.06.008, + Krieg 1995 / Hornung 2006).

### Changed
- Version 5.3.0 -> 5.4.0 (minor — additive computed scorer).

### Honesty invariant (unchanged)
- Sequence-intrinsic motif-**load** signal. The realized **in-vivo innate response** magnitude in a patient is
  **not** modelled (known-unknown); the mRNA score is **partial** because the dominant evasion lever —
  **nucleoside modification** (m1-pseudouridine) — is a manufacturing choice not derivable from sequence; DNA
  methylation state is likewise out of scope. No magnitude predicted.

## [5.3.0] - 2026-06-10 - v5.3 release: Computed capsid epitope-load oracle (covers all vectors)

v5.2 computed genotoxicity only meaningfully touches integrating vectors. v5.3 brings the **NetMHC-style
calculation** to the **adaptive (CD8 T-cell)** axis — the fraction of a viral vector's capsid/envelope that is
presentable across a frequent HLA-I panel (MHCflurry) — so the computed immune signal **covers all 8 vehicles**
(5 viral computed, 3 non-viral by mechanism). Workstream WS-EPITOPE, SHA-locked.

### Added
- **WS-EPITOPE build** — `scripts/p53_build_epitope_oracle.py` (runs in a dedicated `penstack:mhcflurry` image)
  slides 9-mers across each capsid/envelope antigen and predicts MHCflurry 2.0 affinity %rank per allele across
  12 frequent HLA-I alleles; `epitope_fraction_strong` = residues covered by a strong binder (%rank ≤ 0.5);
  `capsid_immune_score = 1 − epitope_fraction_strong`. Sequences UniProt-verified and committed
  (`configs/capsid_sequences.fasta`): AAV2 VP1 P03135, Ad5 hexon P04133, VSV-G P03522, HSV-1 gD P57083 + gB
  P06437. Emits the small committed summary `configs/capsid_epitope_oracle.yaml` (MHCflurry + raw sequences stay
  on the VM → CI-safe).
- **WS-EPITOPE oracle** — `pen_stack/planner/capsid_epitope_oracle.py`: `capsid_epitope_oracle(vehicle)` returns
  an `OracleResult` (`output_kind="baseline"`, scope card `capsid_epitope`). Non-viral vehicles → 1.0 by
  mechanism; unknown / sequence-less → **abstains**.
- **Wired into the adaptive axis** — `safety_efficacy_profile()` folds the computed capsid score into the
  adaptive (CD8) sub-axis **only for in-vivo vehicles**. The computed score is *intrinsic* antigen
  presentability; for **ex-vivo** lentivirus (whose VSV-G envelope is intrinsically epitope-dense but barely
  seen by the host ex vivo) it is **reported but not folded** (`adaptive_source = computed_ex_vivo_muted`), the
  documented tier kept. `capsid_presentability_score` surfaces the raw computed value.
- **Result:** AAV2 capsid is the *least* epitope-dense (0.72) and Ad5 hexon among the most (0.82); HDAd's in-vivo
  immune score drops accordingly — the documented adaptive ordering reproduced from sequence. `prereg/ws_epitope.yaml`.

### Changed
- Version 5.2.0 -> 5.3.0 (minor — additive computed oracle); `cite.curated_dois()` ingests the epitope
  provenance DOIs (MHCflurry 10.1016/j.cels.2020.06.010, HLA-I supertypes 10.1186/1471-2172-9-1).

### Honesty invariant (unchanged)
- Population-level, **sequence-intrinsic presentation** signal (does the capsid contain HLA binders) — **not**
  the realized in-vivo / **patient-HLA-specific** T-cell response (a known-unknown), and **CD8/MHC-I only** (not
  antibody / neutralizing-antibody). No magnitude predicted.

## [5.2.0] - 2026-06-10 - v5.2 release: Computed genotoxicity oracle (data, not a documented tier)

The v5.1 genotoxicity axis was a documented ordinal tier; for **integrating** vectors that signal is in fact
computable from data the stack already holds. v5.2 adds a **computed genotoxicity oracle** — the observed
enrichment of a vector class's integration sites near COSMIC oncogenes — answering through the v4.0
OracleResult contract. Workstream WS-GENOTOX, SHA-locked.

### Added
- **WS-GENOTOX build** — `scripts/p52_build_genotox_oracle.py` (runs on the VM where the data lives) computes,
  per integrating vector class, `P(integration site within 50 kb of a COSMIC Cancer-Gene-Census oncogene)` and
  its enrichment over genome background, from **VISDB** per-virus catalogues × the Phase-1 oncogene annotation
  (**COSMIC CGC v104**). Emits the small, auditable, committed summary `configs/genotoxicity_oracle.yaml` (raw
  catalogues stay on the VM; only the statistics ship → CI-safe).
- **WS-GENOTOX oracle** — `pen_stack/planner/genotoxicity_oracle.py`: `genotoxicity_oracle(vehicle)` returns an
  `OracleResult` (`output_kind="baseline"`) with `genotox_score = min(1, 1/enrichment)`, native uncertainty
  (CI on the observed fraction), the `delivery_genotoxicity` scope card, and `extrapolating` for small-n
  classes. Non-integrating vehicles → 1.0 by mechanism; no computed class → **abstains** (never fabricates).
- **Wired into the v5.1 balance** — `safety_efficacy_profile()` now **prefers the computed genotox_score** for
  integrating vectors and falls back to the documented tier otherwise (`genotox_source` records which).
- **Result (from data):** lentiviral (HIV) integration is **2.08×** enriched near oncogenes (n=88,743, robust)
  vs **5.65×** for gammaretroviral (MLV, the LMO2/SCID-X1 comparator, small-n flagged) — reproducing the
  lentivirus-safer-than-gammaretrovirus ordering **from VISDB×COSMIC**, and the computed lentivirus score
  (0.48) **validates** the v5.1 documented "moderate" tier (0.5). `prereg/ws_genotox.yaml`.

### Changed
- Version 5.1.0 -> 5.2.0 (minor — additive computed oracle); `cite.curated_dois()` ingests the genotox
  provenance DOIs (VISDB 10.1093/nar/gkz867, COSMIC CGC 10.1038/s41568-018-0060-1, HIV/MLV integration biology).

### Honesty invariant (unchanged)
- This is a **relative integration-preference** signal. The in-vivo clonal-expansion / leukemogenesis OUTCOME
  in a patient is **not** modelled and stays a known-unknown (`delivery_genotoxicity` scope card); the immune
  MAGNITUDE likewise stays `in_vivo_immunogenicity`. No magnitude is predicted.

## [5.1.0] - 2026-06-10 - v5.1 release: Delivery immunology (the safety↔efficacy balance)

The delivery palette gains a **documented, cited, qualitative immune + safety + efficacy profile** per vehicle,
so the substrate can make the safety↔efficacy tradeoff legible and user-weightable — without ever predicting an
immune magnitude (that stays a declared known-unknown). Workstream WS-IMMUNE, SHA-locked.

### Added
- **WS-IMMUNE config** — `configs/delivery_vehicles.yaml` (v1.1): an `immune_safety` block on all 8 vehicles
  (`preexisting_immunity`, `neutralizing_antibody`, `innate_immune`, `adaptive_immune`, `genotoxicity`,
  `efficacy`, `tradeoff`, `immune_dois`) — DOCUMENTED ordinal low/moderate/high priors, every `immune_doi`
  Crossref-verified and in the curated-DOI set (citations resolve by construction).
- **WS-IMMUNE planner** — `pen_stack/planner/delivery_immunology.py`: `safety_efficacy_profile()` reports two
  **separate** safety sub-axes — `immune_score` (immunogenicity; reversible, eligibility/re-dosing) and
  `genotox_score` (insertional/oncogenic; permanent) — never collapsed, with headline
  `safety_score = min(immune_score, genotox_score)` (precautionary worst-axis). `recommend_delivery(cargo_form,
  cargo_bp, safety_weight, in_vivo)` ranks the eligible palette along the safety↔efficacy frontier by a
  user-supplied weight. Reproduces the stated tradeoff: AAV is dinged on immunogenicity, lentivirus on
  genotoxicity. `prereg/ws_immune.yaml`.
- **WS-IMMUNE verify** — `Verdict.delivery_profile` + a `delivery_immune_profile` scope flag: `verify()` now
  surfaces the documented profile and tradeoff for a chosen vehicle, always attaching the standing
  `in_vivo_immunogenicity` known-unknown flag — never adding confidence, never predicting a magnitude.

### Changed
- Version 5.0.0 -> 5.1.0 (minor — additive delivery-immunology layer); `cite.curated_dois()` now also ingests
  the per-vehicle `immune_dois`.

### Honesty invariant (unchanged)
- The in-vivo immune MAGNITUDE (patient/construct-specific response) remains a declared known-unknown
  (`configs/known_unknowns.yaml: in_vivo_immunogenicity`) and is **never** predicted. v5.1 exposes only
  documented ordinal priors plus a transparent, user-weighted ranking — it makes the boundary legible, it does
  not close it.

## [5.0.0] - 2026-06-09 - v5.0 release: the Co-Scientist (capstone — smart because it is grounded)

The reasoning ceiling rises while the grounding floor stays fixed: a co-scientist that proposes multiple
distinct strategies, critiques and revises its own plans, cites its reasoning, and itemises what it cannot
assess — with **no-fabrication holding across the full reasoning stack** (the central gate). Workstreams
WS-{PLAN,MULTI,CRIT,SCOPE2,CITE,GEN}, each SHA-locked.

### Added
- **WS-PLAN + WS-MULTI** — `pen_stack/agent/co_scientist.py`: `propose_strategies()` returns 2–3 **materially
  distinct** strategies (≥2 design axes differ — measured by `distinctness()`, not reworded), each
  independently legal + confidence-tagged; `deliberate()` benchmarks the deliberative planner vs the
  deterministic baseline. `prereg/ws_plan.yaml`.
- **WS-CRIT + WS-SCOPE2** — `critique()` / `critique_and_revise()` (the critic only flags + swaps a design
  choice, never invents a number; revisions re-verified) + `critique_falsifiability()` (improves flawed plans
  illegal→legal, 0 spurious revisions on clean) + `scope_ledger()` (per-recommendation: what was/ wasn't
  assessed, the known-unknowns itemised). `prereg/ws_crit.yaml`.
- **WS-CITE + WS-GEN** — `pen_stack/agent/cite.py`: `cited_rationale()` (citations drawn from the curated
  world-model → resolve by construction) + `citations_grounded()` guard (rejects any DOI not in the curated
  set) + `generalise()` (adjacent tasks grounded-or-refused). `prereg/ws_cite.yaml`.
- **Bench v0.3.2** — `co_scientist_grounded` reference-solver task: grounded rate 1.0 vs ungrounded 0.0;
  no-fabrication across the full stack. `docs/co_scientist.md`.

### Changed
- Version 4.5.1 -> 5.0.0 (major — the substrate matured into a grounded co-scientist); bench 0.3.1 -> 0.3.2.

## [4.5.1] - 2026-06-09 - ID-correctness patch: cell-type ontology IDs

### Fixed
Two of the three new v4.5 Tier-A cell-type ontology IDs in `configs/cell_types.yaml` were wrong (verified via
EBI-OLS): `EFO:0002322` resolved to the **RPMI8226 myeloma line** (not a T cell) and `EFO:0004146` to an
**obsolete myopathy term** (not hepatocyte). Corrected to the canonical, non-obsolete Cell Ontology terms:
**primary_T_cell → `CL:0000084`** (T cell), **hepatocyte → `CL:0000182`** (hepatocyte). iPSC (`EFO:0004905`),
K562 (`EFO:0002067`), HepG2 (`EFO:0001187`) verified correct, as was the ISPpu10 back-test record (Europe PMC
**PPR1218813** — "ISPpu10 is a structure-gated bridge RNA recombinase…"). No result/test change (the IDs are
coverage-card metadata; `cell_types.py` reads coverage, not the ontology id).

## [4.5.0] - 2026-06-09 - v4.5 release: the Living World-Model (knowledge graph + gated living loop)

v4.5 promotes the flat tables into a queryable knowledge graph that keeps itself current. Workstreams
WS-{G,MON,CT,BA}, each SHA-locked. The agent proposes; a gate disposes — no process auto-edits curated truth.

### Added
- **WS-G - knowledge graph.** `pen_stack/graph/{schema,build,query}.py`: typed nodes
  (writer/locus/cargo/vehicle/cell_type/write_type/outcome) + typed edges
  (reaches/deliverable_by/performs/durable_in/carries/used_writer/observed_at), each carrying evidence kind
  (measured>curated>predicted) + confidence + scope + provenance. Built deterministically from the v4.0
  curated tables (94 nodes / 288 edges), pure-Python JSON store. Multi-hop queries return provenanced paths;
  `deliverable_by` reproduces the v3.3 verifier (0 parity mismatches). REST `POST /graph/query` + MCP
  `graph_query`. `docs/world_model.md`; `prereg/ws_graph.yaml`.
- **WS-MON - gated living loop.** `pen_stack/graph/ingest.py`: Candidate + Quarantine (propose never mutates
  a graph), `automated_checks` + `gate_admit(approved, admitted_by)` as the sole admission path with versioned
  records; back-test surfaces ISPpu10 (Europe PMC PPR1218813). No auto-edit path (asserted). `prereg/ws_mon.yaml`.
- **WS-CT - cell-type expansion.** `configs/cell_types.yaml` Tier-A (iPSC/ESC, primary T cells, hepatocytes)
  with coverage cards + Tier-B roadmap; `pen_stack/graph/cell_types.py` graceful degradation (partial coverage
  caps confidence) + cross-cell-type OOD labelling. `prereg/ws_ct.yaml`.
- **WS-BA - graph reasoning bench.** `graph_multihop_reasoning` (bench v0.3.1): graph reasoning accuracy 1.0
  vs ungrounded 0.0, every answer a provenanced path. `prereg/ws_ba_v45.yaml`.

### Changed
- Version 4.0.3 -> 4.5.0; bench 0.3 -> 0.3.1; README "What is new in v4.5"; M1/M2 + world-model note updates.

## [4.0.3] - 2026-06-09 - ID-correctness patch: UniProt + Pfam + ontology audit

### Fixed
A whole-repo audit of structured IDs (verified against InterPro, UniProt, EBI-OLS, mygene):
- **`pen_stack/mech/pfam_whitelist.yaml` (v1.2.1 -> v1.2.2):** the 26 Pfam accessions were all correct, but
  **13 of 22 `example_uniprot` proteins did not actually contain their claimed domain** (membership checked
  against each protein's UniProt Pfam cross-references) — including a marine-worm **Histone H3** (PF13586), a
  mouse **mannosyltransferase** (PF05621/TniB), **I-AniI** (a LAGLIDADG enzyme) mislabelled HNH (PF01844), a
  **glycine-betaine transporter** and a Tn3 transposase mis-filed as rve, and an **obsolete 404** accession
  (PF08721) — despite the header claiming a spot-check. All corrected to reviewed/curated proteins whose
  UniProt entry genuinely carries the domain (e.g. ISCro4 `D2TGM5`, Tn5 `Q46731`, Tn7-TnsA `P13988`, Bxb1
  integrase `Q9B086`, McrA `P24200`); the audit-status header was corrected to stop over-claiming.
- **`configs/atlas_families.yaml`** (drives family expansion in `expand.py`): IS621 `A0A0F6B5L8` (a
  betaine transporter) -> **`A0A2X3M8B0`** (IS621 transposase); phiC31 `Q9T2A6` (a plant NAD(P)H
  oxidoreductase) -> **`Q9T221`** (phiC31 integrase). The Pfam-query signatures and discovery DOIs were
  already correct.

### Verified clean
The 4 EFO cell-type IDs map correctly (EFO:0002067=K562, EFO:0001187=HepG2, EFO:0002784=GM12878,
EFO:0005483=ES-Bruce4); all GSH gene symbols are valid HGNC symbols; all 26 Pfam accessions resolve with the
correct domain name.

## [4.0.2] - 2026-06-09 - citation-correctness patch: full-repo DOI audit

### Fixed
A full sweep of all 56 DOIs in the repo (verified via Crossref + doi.org) found six incorrect or
non-existent citations — all now corrected to verified, topically-correct references:
- `configs/gsh_validated_heldout.yaml` H11 locus: `10.1371/journal.pone.0113481` (resolved to an unrelated
  cardiology paper) → **`10.1093/nar/gkt1290`** (Zhu et al. 2014, *DICE*, NAR 42:e34 — the paper that
  characterized human H11 on chr22q12.2 between DRG1 and EIF4ENIF1).
- `configs/delivery_vehicles.yaml` + `configs/rules/{delivery,payload}.yaml`: `10.1089/hum.2017.084`
  (non-existent), `10.1089/hum.2009.213` (non-existent), `10.1038/sj.gt.3302529` (unrelated erratum) →
  **`10.1128/JVI.79.15.9933-9944.2005`** (Grieger & Samulski, AAV packaging capacity),
  **`10.1128/JVI.72.2.926-933.1998`** (multiply-deleted adenovirus vectors), **`10.1038/nbt1101-1067`**
  (Wade-Martins, HSV-1 amplicon large-capacity).
- `pen_stack/validate/bench_writetype_tasks.py` provenance: `10.1038/s41586-023-06756-4` (diabetes program)
  and `10.1126/science.abm1123` (freshwater fish) → **`10.1016/j.cell.2022.03.045`** and
  **`10.1128/JVI.79.15.9933-9944.2005`**.

The remaining 50 DOIs resolve correctly; three legacy DOIs in `mech/pfam_whitelist.yaml` (Rice 1995 Cell,
Kholodii 1997 Res Microbiol, Prudhomme 2002 J Bacteriol) carry full author/year/journal references and are
real classic papers whose pre-modern DOIs do not resolve at doi.org — left unchanged (a registration artifact,
not an error).

## [4.0.1] - 2026-06-09 - data-correctness patch: writer-verification panel verified against Perry 2025

### Fixed
- **WS-WV frozen panel is now verbatim from the measured Perry 2025 ISCro4 DMS.** The offline-fallback panel
  in `atlas/writer_verify.py` previously used *illustrative* Z-scores (2.6/2.1/1.7) and invented control
  variants (G15D/P88R/L120E), and `_CORE_RESIDUES` used illustrative arginines. Replaced with the REAL values
  from `science.adz0276` Table S3: the top-3 enhancers **N322P (Z 0.754), H50K (0.742), R278M (0.709)**, real
  near-neutral variants (V21R, S312Q, G286T), the most-deleterious variants (R132E −5.40, R137E −5.12,
  R195D −4.98), and the documented catalytic residues **D11/E60/D102/D105/S241** ("Residue Groups" sheet). The
  real-DMS path (on the VM/Drive) was already correct; only the offline fallback constants were illustrative.
  Added `test_ws_wv.py::test_frozen_panel_matches_real_perry_dms_table_s3` to guard against drift.

## [4.0.0] - 2026-06-09 - v4.0 release: the Oracle Mesh (on top of the foundation models) + writer verification

A major bump: the substrate now *composes* the biomolecular foundation models under one contract and verifies
the writer enzyme itself. Workstreams WS-{O,WV,ATLAS}, each SHA-locked. No de-novo writer invention — score
and critique only (the pen-assemble lesson).

### Added
- **WS-O - the oracle mesh.** `pen_stack/oracles/` with `OracleResult{value, provenance(model+version),
  native_uncertainty, scope_card, in_scope, extrapolating, output_kind, available, cached}`. Adapters:
  `genome.py` (AlphaGenome OOD-gated; Evo2 likelihood=claim / generation=candidate; ChromBPNet·Borzoi
  baseline), `structure.py` (AlphaFold3/Boltz-2/Chai-1/Protenix + `consensus()` that widens the interval on
  cross-oracle disagreement), `protein_design.py` (RFdiffusion/ProteinMPNN/ESM3 - all candidates), `rna.py`
  (ViennaRNA - real, hard fold-legality), `energetics.py` (bridge off-target, MC3 gate ≥0.77).
  `configs/oracles/scope_cards.yaml` (11 models); deterministic version-pinned `oracle_cache/`. Guard:
  generative candidate `as_claim()` raises. `docs/oracles.md`; `prereg/ws_o.yaml`.
- **WS-WV - writer verification.** `pen_stack/atlas/writer_verify.py`: DMS- + structure-grounded variant
  scoring (measured=claimable, unmeasured=not), `blind_recovery` recovers N322P/H50K/R278M above
  measured-worse controls, and `critique_candidate` (fold/active-site/deliverable/reachable) wired into
  `verify()` as `Verdict.writer_critique` - always `no_claim=True`. `docs/writer_verification.md`;
  `prereg/ws_wv.yaml`.
- **WS-ATLAS - mesh upgrade + delivery oracle.** `wgenome/mesh_features.py` (OOD-gated feature hook + honest
  blind re-validation reporting parity vs v3.x when oracles are deferred) + a computable
  `delivery.aav_packaging_margin` soft rule (titre drops near the AAV capsid limit). `prereg/ws_atlas.yaml`.

### Changed
- Version 3.4.0 -> 4.0.0; `Verdict` gains `writer_critique`; M1 + writer-verification note + M2 updates.

## [3.4.0] - 2026-06-09 - v3.4 release: the Environment (train/eval surface + bench v0.3 + outcome-calibration)

v3.4 turns the thin Gym interface into a full environment an AI agent can be trained and graded in, ships
Genome-Writing Bench v0.3 (multi-write-type + adversarial robustness), and tests whether plan-confidence
actually predicts documented outcomes. Workstreams WS-{ENV,BENCH,CAL}, each SHA-locked. The environment is an
interface + evaluation harness (near-one-shot decision) - no RL-superiority claim.

### Added
- **WS-ENV - the genome-writing environment.** `pen_stack/env/genome_writing_env.py` upgraded to a full
  `gymnasium.Env`: a 5-stage MDP (write_type -> site -> writer -> cargo -> delivery) whose step validity comes
  from the v3.3 verifier and whose reward is the legality gate times the L4 calibrated plan confidence, with a
  reserved abstain action for a justified refusal. `pen_stack/env/policies.py` (random + greedy-planner).
  Passes `gymnasium.utils.env_checker.check_env`; greedy(planner) >= random and greedy-legal on the frozen
  seed set. `docs/environment.md`; `prereg/ws_env.yaml` + lock.
- **WS-BENCH - Genome-Writing Bench v0.3.** `multi_write_type_legality` routes + judges legality across all 6
  non-insertion write types (accuracy 1.0, ungrounded 0.0); `adversarial_robustness` probes T13-T16
  (out-of-scope-in-disguise, contradictory constraints, prompt-injection, distribution-shift) - the
  verifier-backed agent passes 4/4 vs an over-confident baseline 0/4, no-fabrication holds incl. under
  injection. Leaderboard v0.3 robustness contrast. `prereg/ws_bench.yaml` + lock.
- **WS-CAL - plan-confidence calibrated against documented outcomes.** `pen_stack/validate/outcome_calibration.py`:
  plan-level reliability diagram + ECE + bootstrap-CI selective prediction on the DOI writer panel. Honest
  result: useful for ranking (high-confidence 0.30 vs low-confidence 0.0 documented-choice recovery, gap
  CI95 [0.17, 0.43], monotone) but poorly calibrated in absolute terms (ECE 0.71). Feeds M-UQ.
  `prereg/ws_cal.yaml` + lock.

### Changed
- Version 3.3.0 -> 3.4.0; bench 0.2.1 -> 0.3; README "What is new in v3.4"; M2/M-UQ manuscript updates.

## [3.3.0] - 2026-06-09 - v3.3 release: the Verifier (a type checker for genome writes)

v3.3 lifts the laws of genome writing into a versioned, machine-readable rule base and exposes a single
`verify(design) -> Verdict` call (legal/illegal + named rule + calibrated confidence + scope) over Python,
REST, and MCP. Workstreams WS-{R,D,ROUTE,V,BA}, each SHA-locked.

### Added
- **WS-R - rule base + solver.** `pen_stack/rules/{schema,evaluators,loader,solver}.py` + `configs/rules/*.yaml`
  (9 rules across reachability/fold/payload/multiplex/delivery), each id/kind/mechanism/param/provenance(DOI)/
  test. Evaluators delegate to the existing validated functions; a parity test proves no decision changed.
  Legality and confidence are kept as distinct axes.
- **WS-D - delivery palette.** `configs/delivery_vehicles.yaml` + `planner/delivery_vehicles.py`: 8 vehicles
  (AAV single/dual, lentivirus, HDAd, HSV amplicon, LNP-mRNA, eVLP, electroporation) with capacity/integration/
  cargo-form/DOIs; delivery rules (hard rejects + soft penalties + an immunogenicity-magnitude scope flag).
- **WS-ROUTE - write-type router.** `planner/router.py` + `configs/write_types.yaml`: dispatches insertion/
  excision/inversion/replacement/regulatory_rewrite/landing_pad_install/multiplex; unsupported types defer.
- **WS-V - verification service.** `pen_stack/verify/{service,schema}.py`: `verify(design) -> Verdict`; `POST
  /verify` + MCP `verify_write`; `docs/verify.md`. No fabrication (every number tool-sourced).
- **WS-BA - bench v0.2.1 + agent.** T12 rule-grounded legality-with-explanation (verifier reason accuracy 1.0
  vs ungrounded 0.0); the agent submits its plan to the verifier. Bench 12/12 available, planner beats baseline
  8/8.
- **Docs:** `docs/verify.md`, `docs/rules.md`, `docs/delivery.md`.

### Changed
- Version 3.2.0 -> 3.3.0 (pyproject, `__init__`, CITATION.cff). README "what is new in v3.3"; bench badge v0.2.1.

## [3.2.0] - 2026-06-08 - v3.2 release: a calibrated, self-aware co-scientist

The v3.2 cycle makes the genome-writing funnel **trustworthy**: every value carries a calibrated confidence,
an extrapolation flag, and — where the biology is beyond any tool here — an explicit out-of-scope deferral.
Workstreams UQ/EP/MC/BA, each pre-registered (`prereg/ws_{uq,ep,mc,ba}.yaml`, SHA-locked) and reporting its
honest negatives. The Genome-Writing Bench bumps to **v0.2**.

### Added
- **WS-UQ - calibrated uncertainty + OOD.** Conformal prediction intervals (durability expression) and APS /
  Mondrian prediction sets (safety, silenced) wrapping the existing heads with no retraining
  (`pen_stack.wgenome.uncertainty`); an OOD detector that widens intervals out-of-distribution
  (`pen_stack.wgenome.ood`); selective prediction + plan-level confidence
  (`pen_stack.validate.selective_prediction`). Held-out coverage 0.895 vs 0.90 nominal; risk-coverage accuracy
  0.739->0.930 under abstention. OOD across human cell types is weak (0.65-0.73) - reported as a heuristic.
- **WS-EP - epistemic scoping.** A three-tier status (grounded-confident / grounded-extrapolating /
  not-computable) on every agent output (`pen_stack.agent.epistemic`); a known-unknowns registry + scope
  matcher (`configs/known_unknowns.yaml`, `pen_stack.agent.scope`, `docs/scope.md`) that defers out-of-scope
  questions (deferral 1.0, false-defer 0.0); abstention in the agent. No-fabrication gate intact.
- **WS-MC - mechanistic filters.** A hard target-site/PAM/att-site reachability reject
  (`pen_stack.planner.target_site`, `configs/target_sites.yaml`; controls 9/9); vehicle-specific
  delivery-sequence penalties (`pen_stack.planner.delivery_constraints`); and an off-target **energetics**
  model (`pen_stack.bridge.offtarget_energetics`) that beats the 0.77 baseline at held-out AUROC 0.88 on the
  comparable (core-disrupted) construction and ships as the default ranker. A reviewer-driven re-run
  (`by_negative_construction`) shows that gap is mostly the core-penalisation artifact; with the core held
  matched the non-core substitution-identity gain is real but modest (Δ≈0.04, 0.687 vs 0.646). Both AUROCs
  carry a favourable-negative-set caveat (decoys derived from real off-targets; no non-recombining background).
- **WS-BA - bench v0.2 + uncertainty-aware agent.** Four trust tasks (T8 calibration, T9 selective prediction,
  T10 OOD honesty, T11 out-of-scope refusal) contrasting the uncertainty-aware agent with an over-confident
  baseline (4/4); PEN-Agent emits confidence + epistemic status + abstains; UI surfaces them. Bench re-SHA-locked.
- **WS-OPT1 (optional) - Gymnasium interface.** A thin `gymnasium.Env` over the planner (`pen_stack.env`,
  `[env]` extra) for agent-developer interoperability - interface only, no RL superiority claimed.
- **Docs:** `docs/uncertainty.md`, `docs/scope.md`, `docs/mechanistic_constraints.md`; M-UQ methods note +
  M1/M2 manuscript updates. WS-OPT2 (Opentrons) deferred to `docs/BACKLOG.md`.

### Changed
- Version 3.1.0 -> 3.2.0 (pyproject, `__init__`, CITATION.cff). README "what is new in v3.2"; badges + bench
  v0.2. The bridge off-target default ranker is now the energetics model when its penalty table is present.

## [3.1.0] - 2026-06-04 - v3.1 release: publishable contributions + an adopted benchmark

The v3.1 cycle completes (workstreams A-H). It hardens the honesty of the planning benchmark, surrounds the
models with strong baselines, adds a predicted-structure safety axis, and ships the first benchmark and
grounded agent for the genome-writing side. Every workstream is pre-registered (`prereg/ws_*.yaml`,
SHA-locked) and reports its honest negatives.

### Added
- **WS-B - strong baselines + safety primary-metric switch.** Endogenous-expression baseline (TRIP-trained
  Spearman 0.51 vs AlphaGenome ES-Bruce4 proxy 0.43), multi-mark ablation (all-marks >= best single), and a
  published GSH rule-set: safe-harbour discrimination (learned 0.92, 95% CI [0.82, 0.98] vs distance-rule
  0.38, delta CI excludes zero) is now the primary safety metric; the circular `genotoxic_cis` AUROC is a
  labeled diagnostic. (`pen_stack.wgenome.gsh_baseline`, `pen_stack.validate.durability_baselines`.)
- **WS-C - AlphaGenome integration.** Hosted-API provider with an offline cache; predicted-vs-measured track
  validation (HepG2 ATAC Pearson 0.85) with an honest score-level low-confidence flag; a 3D structural-risk
  axis from contact-map deltas (`pen_stack.wgenome.{providers,chromatin_seq,structure3d}`,
  `pen_stack.validate.seq_vs_measured`).
- **WS-D - Cargo Polish.** Cargo-sequence silencing-risk scan (`pen_stack.planner.cargo_polish`).
- **WS-E - Genome-Writing Bench v0.1 + PEN-Agent.** The first writing-side benchmark (`benchmarks/`,
  `bench/run.py`) with deterministic scorers, a leaderboard, and a real LLM-agent baseline; a grounded
  write-planning state machine with a no-fabrication hard gate (`pen_stack.agent.pen_agent`).
- **WS-F - local recalibration / private-data adaptation.** Gated recalibration / fine-tuning on private
  data, in-container; the adapted model activates only if it beats the released model AND a no-skill
  baseline; the released model is provably unchanged (`pen_stack.adapt`).
- **WS-G - multiplex + guide QC.** A pairwise translocation-risk screen (`pen_stack.planner.multiplex`,
  surfaced in PEN-Agent) and a bridge-RNA guide ranker (`pen_stack.bridge.guide_qc`).
- **WS-H - release + dissemination.** README/badges updated for v3.1, `docs/quickstart.md`,
  `docs/positioning.md`, the leaderboard submission guide, the dissemination log, and version 3.1.0.

### Changed (honesty)
- The planning benchmark's `recovery_at_k` ranking is now deterministic (stable sort + tie-breakers).
- The LLM stack defaults to the local Ollama model on the compute tier with an automatic hosted-Nemotron
  fallback, a cooldown cache, and bounded timeouts (no more multi-minute stalls when a provider is absent).

## [3.1.0a0] - 2026-06-04 - v3.1 WS-A: de-circularize the planning benchmark (gate)

The v3.1 cycle (publishable contributions + an adopted benchmark) opens with its gate: de-circularizing the
Phase-3 planning benchmark before anything builds on it.

### Changed (honesty)
- **The Phase-3 "discriminating-stratum recovery@10 = 1.00 vs 0.00 (McNemar p, CI)" is now labeled
  definitional, not predictive,** everywhere (README, manuscript abstract, `prereg/paper3.yaml`,
  `validate/paper3_benchmark.py` docstring). An on-target identity term dominates the score, so the planner
  ranks the goal's own gene first by construction. Documented in `docs/benchmark_circularity.md` (WS-A1).
- The intent result is reframed as a **specification-compliance correctness table** (`validate/intent_specification.py`,
  7/7), with no recovery/p-value/CI language (WS-A2).

### Added (the honest, non-circular replacements)
- **Blind safe-harbour site discovery (the new headline)**: `validate/blind_gsh_discovery.py` +
  `configs/gsh_validated_heldout.yaml` (5 DOI-validated held-out GSH, gene-anchored to hg38) +
  frozen/SHA-locked `data/gsh_matched_controls.parquet`. Run genome-wide (no on-target term), the planner's
  writability separates validated GSH from matched-context controls at **AUROC 0.92** (safety-only 0.50)
  (WS-A3).
- **Diversified writer-family recovery**: `validate/writer_recovery.py` + `data/writer_panel.csv` (8 writes,
  4 families, DOIs). recovery@1 = **1.0** vs prevalence 0.25 (smallest-capacity DSB-free writer that fits
  the cargo) (WS-A4).
- **Within-locus ranking** (descriptive): `validate/within_locus_ranking.py` - AAVS1 documented bin at the
  93rd within-locus percentile (top quartile); CLYBL at the 34th (honest negative) (WS-A5).
- **Consolidated report** `scripts/p3_benchmark_report.py` -> `out/ws_a_report.md`; `prereg/ws_a.yaml` +
  SHA lock. Gate G-A is met: blind AUROC reported, no circular claims remain (WS-A6).

## [Unreleased] - 2026-06-03 - honest reframing, repository polish, coverage, hybrid LLM

### Added
- **Hybrid LLM backend** (`pen_stack/rag/llm.py`, `configs/llm.yaml`): a strong hosted model for
  reasoning/agent/Q&A (NVIDIA Nemotron, OpenAI-compatible, free) with **automatic fallback** to the local
  Ollama model, then to the deterministic no-LLM path. One `provider` switch. The agent and RAG were
  refactored onto a single provider-agnostic `chat()` (NVIDIA tool-call IDs and Ollama native message
  threading both handled). The LLM stays non-load-bearing - every number/citation still comes from
  validated tools - so the model choice does not affect scientific reproducibility; it only improves
  orchestration (Nemotron planned a goal in 2 tool calls vs the local 7B's 8-call loop). Core scientific
  compute stays local/VM and uses no LLM. API keys are read from an env var or a **gitignored** file and
  are never committed.

### Changed
- **Paper 4 reframed to its honest scope.** `pen-bridge` is positioned as the first measured-data-validated
  tool that **nominates and ranks candidate off-target *locations*** for bridge recombinases - a
  **screening tool, not a quantitative safety calculator**. The AUROC 0.77 vs 0.62 result is stated with
  its caveat (favourable negative set; mostly tests core integrity), and the magnitude limitation
  (sequence-risk does not rank recombination amount, rho ~0.30) is named as the single most important
  limitation. Application-Note tier, first-of-its-kind for an unoccupied gap; the Writable Genome remains
  the flagship. Manuscript + `prereg/paper4.yaml` + summaries updated.
- **Variant-effect reframed:** the DMS recovers KNOWN enhancers (a catalogue feature), it is not a novel
  variant-design method; EVOLVEpro is the engine to wrap when generating new variants.
- **Repository made clean ASCII:** removed all decorative emojis and em/en dashes and other non-ASCII
  punctuation across code, docs, configs, and manuscripts (box-drawing tree characters kept).

### Added
- 72-system ortholog characterisation (`bridge/ortholog_screen.py`) - explicitly DESCRIPTIVE (Table S1 has
  no activity label): sequence-similarity organisation vs the validated standout ISCro4 (IS621 ranks most
  similar, a sanity check). Exploratory secondary result, N ~72.
- Coverage: CI runs `pytest --cov`, uploads to Codecov, and publishes a self-hosted coverage badge
  (`tools/make_coverage_badge.py` -> `.github/badges/coverage.svg`). Unit-test coverage of the core logic
  is **69%** (integration-only modules that need GPU/VM/network/LLM are excluded via `[tool.coverage.run]`).
- Professional, emoji-free README with connected-repo badges (genome-atlas / mech-class / pen-score /
  pen-assemble / pen-compare), an architecture diagram, and the problem/gaps explanation.

## [3.0.0a5] - 2026-06-02 - Phase 1.5 (Bridge-recombinase off-target engine -> Paper 4, BEACHHEAD)

The first public instrument: a bridge-recombinase off-target screening tool.

### Added
- **Off-target engine** (`pen_stack/bridge/offtarget.py` + `configs/bridge_offtarget_profile.yaml`):
  genome-wide hg38 pseudosite scan (CT-core seed, per-chromosome, memory-bounded) + a position-weight
  risk model grounded in the published mechanism. **Beats naive Hamming: AUROC 1.00 vs 0.59** at
  separating core-preserving (real-risk) from core-disrupting (abolished) sites. Exposes
  `predict_offtargets(family, site)` - completes the Phase-3 Planner cargo hook.
- **Fold / cross-loop QC** (`bridge/fold_qc.py`): ViennaRNA fold (verified MFE on a 190-nt design) +
  TBL/DBL cross-loop complementarity.
- **Activity framework** (`bridge/activity.py`): exploratory DMS + 72-system trainer (deferred; data paywalled).
- **`pen-bridge`** (`bridge/pipeline.py`, `bridge/cli.py`, `/bridge/design` API): **wraps** the Arc
  BridgeRNADesigner (verified) and adds the off-target + QC layer.
- `validate/paper4_validation.py` + `scripts/p4_genome_scan.py`; `prereg/paper4.yaml` + SHA lock.

### Notes
- **Phase 1.5 COMPLETE** - pre-registered criteria met (or honestly gated): the off-target engine,
  ViennaRNA fold, and designer wrap are verified on the VM (real hg38 scan: chr22 in ~21 s). The *blind
  recall of Perry 2025's measured off-targets* and the DMS/activity model are gated on the paywalled
  Perry 2025 supplementary (drop in via `ingest.load_offtarget_profile`). Completes the deferred Phase-2
  Section 2.4 and Phase-3 Section 3.2 hooks. 68 tests green; ruff clean. **All program phases (0,1,1.5,2,3) now done.**

## [3.0.0a4] - 2026-06-02 - Phase 3 (The Write Planner + agentic platform -> Paper 3, CAPSTONE)

Inverse design + the paper-defining recovery@k benchmark + the agentic platform.

### Added
- **Inverse-design optimiser** (`pen_stack/planner/optimize.py`, `configs/intent_weights.yaml`): an
  `edit_intent`-conditioned objective whose `target_gene_sign` flips whether hitting the target gene is
  penalised or rewarded - the same TRAC site ranks #1 (knock-in) vs #101 (safe-harbour).
- **Cargo/delivery** (`planner/cargo.py`, `planner/delivery.py`): donor spec + size check + delivery rule
  table; bridge/seek off-target via an optional Phase-1.5 hook (pending until 1.5).
- **End-to-end Planner** (`planner/pipeline.py`, `report.py`, `/plan` API, `pen-stack plan` CLI): ranked,
  fully traceable plans with per-field provenance.
- **Two-stratum recovery@k benchmark** (`validate/paper3_benchmark.py`, `data/benchmark_panel.csv`,
  `prereg/paper3.yaml`): **discriminating stratum planner 1.00 vs baseline 0.00, McNemar p=0.0156, gap CI
  [1.0,1.0] excludes zero; control tie 0.67=0.67**. Panel cited to Europe-PMC-verified sources.
- **Forward hypotheses** (`validate/forward_hypotheses.py`): date-stamped novel F8/SERPINA1/CISH/HBA1
  proposals + grounded cited ranking.
- **Agentic platform**: `agent/tools.py` + `agent/orchestrator.py` (Ollama tool-calling, auditable trace,
  no-fabrication, refusals), `agent/mcp_server.py` (fastmcp), `docker-compose.yml` + `docker/ui.Dockerfile`
  + Streamlit **Agent** page + `docs/DEPLOY.md`/`docs/MCP.md`, `validate/agent_eval.py`.
- Shipped `data/curated/gene_coords.parquet` (GENCODE-derived) so tools work in any container.

### Notes
- **Phase 3 COMPLETE** - pre-registered criteria met (`prereg/paper3.yaml` + `SHA256_LOCK_phase3.json`).
  Agent verified on the VM in LLM mode (no-fabrication + plan-equivalence + refusals all pass). 63 tests
  green; ruff clean. Wet-lab (3.7) skipped - non-gating. Bridge off-target hook completes with Phase 1.5.

## [3.0.0a3] - 2026-06-02 - Phase 2 (Writer Atlas + Unified Stack -> Paper 2)

The broad, cross-family Writer Atlas, the writer<->locus cross-link, and the installable platform.

### Added
- **Writer Atlas** (`pen_stack/atlas/expand.py`, `atlas.parquet`): **33,370 systems across 8 families**
  (31,885 IS110/IS1111 orthologs + curated cores/reps), every row confidence-tagged + >=1 source DOI,
  targeting metadata inherited from the WT-KB. `configs/atlas_families.yaml` drives the UniProt queries.
- **Mechanism at scale** (`pen_stack/mech/`): ported audited 18-family Pfam whitelist v1.2.1; composite
  co-occurrence rules; **core agreement 1.00** vs audited labels; conflicting calls -> review queue.
- **Therapeutic readiness** (`pen_stack/score/therapeutic.py`): deliverability/cargo/human-cell axes,
  components retained (ISCro4 326aa->AAV).
- **Cross-link** (`pen_stack/atlas/crosslink.py`): bidirectional writer<->locus queries; AAVS1 held-out
  check passes (0.90 writability + bridge-reachable). Per-family caches for k562/hepg2/hspc.
- **Variant proposal** (`pen_stack/atlas/variant_propose.py`): point-mutation framework + retrospective
  harness, no chimeras; DMS model pluggable (Phase 1.5).
- **PEN-MONITOR** (`pen_stack/monitor/`): Europe PMC living-database engine; back-test surfaces ISPpu10;
  never auto-edits the atlas; every candidate cited.
- **Grounded RAG** (`pen_stack/rag/`, `pen_stack/agent/guardrails.py`): numbers from tool calls, claims
  cited, clinical directives refused; optional Ollama/Qwen phrasing layer (presentation only).
- **Stack**: unified CLI subcommands, FastAPI server (`pen_stack/server/api.py`), Streamlit platform UI
  (Writer Atlas + Ask pages), mkdocs site + 4 use-case tutorials. 46 tests green; ruff clean.

### Notes
- **Phase 2 COMPLETE** - pre-registered criteria met (`prereg/paper2.yaml` + `SHA256_LOCK_phase2.json`);
  atlas Zenodo DOI pending author upload. Verified on the VM (Docker): API, UI (:8501), RAG with Qwen.

## [3.0.0a0] - 2026-06-01 - Phase 0 (in progress)

Fresh v3.0 monorepo. Supersedes the v1.0 platform repository (archived); consolidates the five prior
repositories (`genome-atlas`, `mech-class`, `pen-score`, `pen-assemble`, `pen-compare`) as provenance.

### Added
- Monorepo scaffold: 13 modules (`atlas`, `mech`, `score`, `wgenome`, `planner`, `bridge`, `monitor`,
  `rag`, `agent`, `ui`, `data`, `validate`, `server`), `pyproject.toml`, Docker image spec, `penctl`
  laptop<->VM orchestrator, CI, `configs/`, `prereg/`.
- `docs/INFRA.md` - three-tier (laptop / VM / Drive) Docker-only, SFTP-only workflow.
- `configs/llm.yaml` - single LLM switch (Ollama + Qwen2.5-7B-Instruct, Apache-2.0).
- `configs/datasets.yaml` - pinned dataset accessions + verified IDs (see VERIFICATION_REPORT_v3.0).

- **WT-KB** (`pen_stack/atlas/`): 8 fully-sourced writer families with reachability tiers; schema enforces the >=1-DOI sourcing rule.
- **Re-grounded axes** (`pen_stack/score/recalibrate.py`, `configs/score_axes.yaml`): `S_Cargo` from measured bp, `S_Prog` from targeting modality, `length_aa` backfilled - no per-enzyme overrides.
- **Canonical universe** (`pen_stack/atlas/universe.py::assemble`): one path joining the 1,058-entity universe + WT-KB + crosswalk; cross-module consistency test.
- **Descriptive scorecard** (`pen_stack/atlas/scorecard.py`): reframed from the circular certification; blind concordance recovers ISCro4 as the bridge standout without naming it. 21 tests green.

### Notes
- Independent verification of all datasets/IDs/DOIs/tools completed: no critical errors in the v3.0 plan
  (full report in `Final_Part_v3.0/VERIFICATION_REPORT_v3.0.md`).
- **Phase 0 COMPLETE** - all pre-registered success criteria met (`prereg/phase0.yaml` + SHA lock).
