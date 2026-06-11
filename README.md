<div align="center">

# PEN-STACK

### The verification & grounding substrate for genome-writing AI — matured into a co-scientist

*The foundation models *generate*; PEN-STACK *checks*. It tells you **where** in the genome you can safely and
durably write, **which enzyme** can write it there, and **how** to design the write end-to-end — then verifies
every design against rule-grounded mechanism, reports calibrated confidence, cites its reasoning, and says
"out of scope" rather than guess. Every number comes from a validated tool; nothing is fabricated.*

[![PyPI](https://img.shields.io/pypi/v/pen-stack.svg)](https://pypi.org/project/pen-stack/)
[![CI](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![Publish](https://github.com/ahmedanees-m/pen-stack/actions/workflows/publish.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/publish.yml)
[![coverage](https://raw.githubusercontent.com/ahmedanees-m/pen-stack/main/.github/badges/coverage.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ahmedanees-m/pen-stack/branch/main/graph/badge.svg)](https://codecov.io/gh/ahmedanees-m/pen-stack)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-5.5.0-blue.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-240%20passing-success.svg)](tests/)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-purple.svg)](https://github.com/astral-sh/ruff)
[![Runtime: Docker](https://img.shields.io/badge/runtime-docker-2496ED.svg)](docker/)
[![Validation: pre-registered](https://img.shields.io/badge/validation-pre--registered-critical.svg)](prereg/)
[![Genome-Writing Bench v0.3](https://img.shields.io/badge/benchmark-Genome--Writing%20Bench%20v0.3.2-6f42c1.svg)](benchmarks/genome_writing_bench/)

**Built on five prior, separately published repositories:**

[![genome-atlas](https://img.shields.io/badge/built_on-genome--atlas-1f6feb.svg)](https://github.com/ahmedanees-m/genome-atlas)
[![mech-class](https://img.shields.io/badge/built_on-mech--class-1f6feb.svg)](https://github.com/ahmedanees-m/mech-class)
[![pen-score](https://img.shields.io/badge/built_on-pen--score-1f6feb.svg)](https://github.com/ahmedanees-m/pen-score)
[![pen-assemble](https://img.shields.io/badge/built_on-pen--assemble-1f6feb.svg)](https://github.com/ahmedanees-m/pen-assemble)
[![pen-compare](https://img.shields.io/badge/built_on-pen--compare-1f6feb.svg)](https://github.com/ahmedanees-m/pen-compare)

</div>

---

## What is PEN-STACK?

PEN-STACK is a single, installable, pre-registered computational stack that builds the reference and design
layer the genome-**writing** era lacks. It consolidates five earlier research projects into one citable
package, then adds the two reference maps and the design engine the field was missing.

Genome **editing** changes a base or short stretch in place. Genome **writing** installs *new* information -
inserting genes, flipping or excising kilobases, placing programmable landing pads. Writing is the harder,
less-tooled, and more clinically transformative modality, and it is gated by questions that today have no
canonical answer.

## The problem, and the gaps PEN-STACK closes

Two questions gate every genome-writing project, and before PEN-STACK no resource answered them together:

| Gap | The problem today | What PEN-STACK provides |
|---|---|---|
| **Where can you write?** | Each lab re-derives an ad-hoc "safe harbour" shortlist from inconsistent criteria; published lists range from ~2,000 sites to 25, none predict expression durability from a learned model, none are writer-aware, most cover one cell type. | **The Writable Genome** - a learned, cell-type-aware, writer-aware atlas scoring every locus for *safety* (genotoxicity risk) x *durability* (will the cassette stay expressed) x *reachability* (which enzyme can engage it). |
| **What can write there, and how well?** | Enzyme capabilities are scattered across papers; no catalogue places all genome-writing families on common, measured axes with their targeting requirements. | **The Writer Atlas** - 33,370 enzyme systems across 8 families on common measured axes, joined to the Writable Genome by a bidirectional cross-link. |
| **How do I design the actual write?** | Destination, enzyme, cargo and delivery are interdependent and goal-dependent; no tool optimises them jointly. | **The Write Planner** - inverse design that, given a goal and an `edit_intent`, returns ranked, traceable site x writer x cargo x delivery plans. |
| **Where might my bridge-recombinase design go off-target?** | Bridge recombinases are the most programmable writers, but had no genome-wide off-target screening tool (a "CRISPOR" equivalent); their developers list this as future work. | **The bridge off-target engine** (`pen-bridge`) - measured-data-validated screening that *nominates and ranks candidate off-target locations* (a screen, not a per-site risk calculator). |

Everything is built on bulk-downloadable public data, runs on a single GPU, and is validated **blind** against
a pre-registered, honest baseline before release.

## What is new in v5.5 — Anti-vector seroprevalence oracle (the last immune axis, from data)

This completes the computable delivery-immunology axes. **Pre-existing humoral immunity** (B-cell / NAb) to a
viral capsid is the one axis that *cannot* be computed from sequence — it is a population prevalence from
natural exposure — so v5.5 grounds it in published **serosurvey data** (AAV: Calcedo 2009 / Boutin 2010;
adenovirus: Mast 2010; HSV-1: Looker 2015). `preexisting_score = 1 − midpoint(seroprevalence)/100`, with the
literature range surfaced as native uncertainty.

| serotype (vehicle) | NAb seroprevalence | pre-existing score |
|---|---|---|
| Ad5 → HDAd | 40–90% | 0.35 |
| AAV (aggregate) → AAV | 30–60% | 0.55 |
| HSV-1 → HSV | 50–70% | 0.40 |
| VSV → lentivirus | 0–5% | 0.975 |

Folded into the pre-existing axis for **in-vivo** vehicles (muted for ex-vivo, where serum NAb can't reach
ex-vivo cells); non-viral → 1.0 by mechanism. It is a **population** prevalence — **not** a given patient's NAb
titer (a known-unknown). See `pen_stack/planner/seroprevalence_oracle.py`, `configs/seroprevalence.yaml`,
`prereg/ws_seroprev.yaml`, and the `seroprevalence` scope card.

**With v5.5, four of the five delivery-immunology axes are grounded in data or sequence** — genotoxicity
(VISDB×COSMIC), adaptive/CD8 (MHCflurry), innate (CpG/dsRNA), pre-existing/NAb (serosurveys) — each abstaining
rather than fabricating, with the in-vivo *magnitude* always a declared known-unknown.

## What is new in v5.4 — Computed innate-sensing scorer (completes the computable immune axes)

The third computed delivery-immunology signal (after v5.2 genotoxicity and v5.3 capsid epitope load). Innate
sensing of a delivered nucleic acid is computed directly from the **cargo sequence**, covering every cargo
form. It is a sequence-intrinsic motif-*load* signal; the realized in-vivo innate response stays a
known-unknown, and the mRNA score is honestly *partial* (the dominant lever — nucleoside modification — isn't
derivable from sequence).

| Cargo form | Pathway | Computed from sequence | Score |
|---|---|---|---|
| **DNA** (AAV / HDAd / HSV / plasmid) | TLR9 / cGAS | CpG observed/expected ratio | `max(0, 1 − CpG_O/E)` — vertebrate genome ~0.2 tolerated, non-depleted DNA → 1 stimulatory |
| **mRNA** (LNP-mRNA / electroporation) | TLR7/8 + RIG-I/MDA5/PKR | U-fraction + ViennaRNA dsRNA pairing | partial / `extrapolating` (nucleoside modification out of scope) |
| **RNP** (eVLP / electroporation) | minimal (transient gRNA) | — | ~0.9 by mechanism |

`verify()` surfaces it as a `cargo_innate_sensing` flag whenever a `cargo_seq` is supplied. See
`pen_stack/planner/innate_sensing.py`, `prereg/ws_innate.yaml`, and the `innate_sensing` scope card.

## What is new in v5.3 — Computed capsid epitope-load oracle (covers all vectors)

v5.2 computed genotoxicity only touches integrating vectors. v5.3 brings the **NetMHC-style calculation** to the
**adaptive (CD8 T-cell)** axis: the fraction of a viral vector's capsid/envelope presentable across a frequent
HLA-I panel (MHCflurry), so the computed immune signal now **covers all 8 vehicles** — 5 viral computed, 3
non-viral by mechanism. It is a population-level, *sequence-intrinsic* presentation signal; the realized
patient-HLA-specific T-cell response stays a known-unknown (and it is CD8/MHC-I only, not antibody).

| Workstream | What it adds | Result |
|---|---|---|
| **EPITOPE build** | `scripts/p53_build_epitope_oracle.py` → committed `configs/capsid_epitope_oracle.yaml` | per viral capsid: `epitope_fraction_strong` over 9-mers × 12 HLA-I alleles (MHCflurry %rank ≤ 0.5), from UniProt-verified sequences (AAV2 VP1, Ad5 hexon, VSV-G, HSV gD/gB); MHCflurry stays on the VM, only the summary ships |
| **EPITOPE oracle** | `planner/capsid_epitope_oracle.py` (`OracleResult`) | `capsid_immune_score = 1 − epitope_fraction_strong`; non-viral → 1.0 by mechanism; abstains when no sequence |
| **wired into the adaptive axis** | folded **only for in-vivo** vehicles | AAV2 least epitope-dense (0.72), Ad5 hexon among the most (0.82) — documented adaptive ordering reproduced from sequence; **ex-vivo** lentivirus's intrinsic VSV-G load is *reported but muted* (host barely sees it ex vivo) |

See `prereg/ws_epitope.yaml` and the `capsid_epitope` scope card.

## What is new in v5.2 — Computed genotoxicity oracle (data, not a documented tier)

v5.1 scored genotoxicity as a documented `low/moderate/high` tier. v5.2 makes it **computed from data** for
integrating vectors: the observed enrichment of a vector class's integration sites near COSMIC oncogenes
(VISDB integration catalogues × the Phase-1 COSMIC-CGC oncogene annotation), surfaced through the v4.0
`OracleResult` contract. The in-vivo clonal / leukemogenesis **outcome** stays a known-unknown — this is a
relative integration-*preference* signal, not a per-patient oncogenesis probability.

| Workstream | What it adds | Result |
|---|---|---|
| **GENOTOX build** | `scripts/p52_build_genotox_oracle.py` → committed `configs/genotoxicity_oracle.yaml` | per integrating class: `P(site within 50 kb of a COSMIC oncogene)`, enrichment vs background, CI, n — from VISDB × COSMIC CGC v104 (raw data stays on the VM; only the auditable summary ships) |
| **GENOTOX oracle** | `planner/genotoxicity_oracle.py` (`OracleResult`, `output_kind="baseline"`) | `genotox_score = min(1, 1/enrichment)`; non-integrating → 1.0 by mechanism; **abstains** when it has no computed class (never fabricates); small-n classes flagged `extrapolating` |
| **wired into v5.1 balance** | `safety_efficacy_profile()` prefers computed genotox, falls back to the documented tier | **lentiviral 2.08×** vs **gammaretroviral 5.65×** oncogene-proximity enrichment — reproduces the lentivirus-safer-than-gammaretrovirus ordering **from data**; computed LV score (0.48) **validates** the v5.1 documented tier (0.5) |

See `prereg/ws_genotox.yaml` and the `delivery_genotoxicity` scope card.

## What is new in v5.1 — Delivery immunology (the safety↔efficacy balance)

v5.1 makes the delivery palette's **safety↔efficacy tradeoff legible and user-weightable**. Every vehicle now
carries a documented, cited, qualitative immune + safety + efficacy profile — so you can ask for a *balance*
(AAV is safe by integration but neutralizing-antibody/pre-existing-immunity limited; lentivirus is a highly
efficacious integrator but its genotoxicity is the dominant concern). Crucially, the in-vivo immune
**magnitude** stays a declared known-unknown — v5.1 surfaces documented priors, it does **not** predict a
patient-specific immune response.

> **The full delivery-immunology story (v5.1 → v5.5), with every axis, method, and outcome, is in
> [`docs/delivery_immunology.md`](docs/delivery_immunology.md).** By v5.5, four of the five immune/safety axes
> are computed from data or sequence (genotoxicity, adaptive/CD8, innate, pre-existing/NAb) rather than
> hand-typed tiers.

| Workstream | What it adds | Result |
|---|---|---|
| **IMMUNE config** | `immune_safety` block on all 8 vehicles in `configs/delivery_vehicles.yaml` | documented ordinal (low/moderate/high) priors for pre-existing immunity, neutralizing antibody, innate/adaptive immune, **genotoxicity**, efficacy — every `immune_doi` Crossref-verified and in the curated-DOI set |
| **IMMUNE planner** | `planner/delivery_immunology.py` — `safety_efficacy_profile()` / `recommend_delivery()` | two **separate** safety sub-axes (`immune_score` reversible vs `genotox_score` permanent), never collapsed; headline `safety_score = min(...)` (worst-axis); ranks the palette along the safety↔efficacy frontier by a **user weight** |
| **IMMUNE verify** | `Verdict.delivery_profile` + `delivery_immune_profile` scope flag | `verify()` surfaces the documented tradeoff for a chosen vehicle, always attaching the `in_vivo_immunogenicity` known-unknown flag — never adding confidence, never predicting a magnitude |

See `prereg/ws_immune.yaml`.

## What is new in v5.0 — the Co-Scientist (smart because it is grounded)

v5.0 matures the reasoning layer on top of everything beneath it. Given a goal and an intent, PEN-STACK
returns a small set of **materially distinct, ranked, fully-traceable strategies** — each verified,
calibrated, cited, and scope-ledgered — while the **no-fabrication guarantee holds by construction**: the
reasoning layer proposes and critiques, but every number still comes from a validated tool or oracle.
Intelligence rises while groundedness never falls.

| Workstream | What it adds | Result |
|---|---|---|
| **PLAN + MULTI** | `agent/co_scientist.py` — `propose_strategies()` / `deliberate()` | 2–3 **materially-distinct** strategies (≥2 design axes differ — *measured*, not reworded), each independently **legal** + **confidence-tagged**; deliberative planner benchmarked vs the deterministic baseline |
| **CRIT + SCOPE2** | self-critique/revise loop + scope ledger | the critic only flags + swaps (never invents a number); revisions are **re-verified** and **falsifiable** (improve flawed plans illegal→legal, never touch clean ones); every recommendation carries a **complete scope ledger** itemising the known-unknowns |
| **CITE + GEN** | `agent/cite.py` — cited rationale + scoped generalisation | citations are **drawn from the curated world-model** (resolve by construction); a guard **rejects any hallucinated DOI**; adjacent tasks are **grounded-or-refused** |
| **central gate** | `co_scientist_grounded` bench (v0.3.2) | grounded rate **1.0** vs ungrounded **0.0**; **no-fabrication holds across the full reasoning stack** (asserted) |

See `docs/co_scientist.md` and `prereg/ws_{plan,crit,cite}.yaml`.

## What is new in v4.5 — the Living World-Model (a knowledge graph that keeps itself current)

v4.5 promotes the flat atlas/WT-KB/crosslink tables into a queryable **knowledge graph**: writers, loci,
cargo, delivery vehicles, cell types, write types and measured outcomes are typed nodes joined by typed edges,
**each carrying its provenance, its uncertainty, and the scope within which it holds**. An agent answers a
multi-hop design question in one grounded traversal, and the graph stays current through a **gated loop** —
new literature evidence is *proposed* as candidate edges and admitted only through a validation/human gate,
**never auto-merged**.

| Workstream | What it adds | Result |
|---|---|---|
| **G — knowledge graph** | `pen_stack/graph/{schema,build,query}` — typed nodes + provenance/uncertainty/scope-tagged edges, built from the v4.0 curated tables; REST `POST /graph/query` + MCP `graph_query` | multi-hop design queries return **fully provenanced paths** (the answer *is* the path); `deliverable_by` edges reproduce the v3.3 verifier with **0 parity mismatches** |
| **MON — gated living loop** | `pen_stack/graph/ingest.py` — PEN-MONITOR emits **candidate** edges; quarantined; admitted only via `gate_admit(approved)` with a versioned record | **no process auto-edits the curated truth** (Principle 1, asserted); back-test admits the recent ISPpu10 bridge system only through the gate |
| **CT — cell-type expansion** | Tier-A cell types (iPSC/ESC, primary T cells, hepatocytes) as nodes with **coverage cards** + Tier-B roadmap | partial coverage **degrades gracefully** (confidence capped, raw reported); cross-cell-type queries **OOD-labelled** (v3.2 finding); Tier-B documented, never silently extrapolated |
| **BA — graph reasoning bench** | `graph_multihop_reasoning` (bench v0.3.1) | graph reasoning accuracy **1.0** vs ungrounded **0.0**; every answer grounded by a provenanced path; no-fabrication holds |

See `docs/world_model.md` and `prereg/ws_{graph,mon,ct,ba_v45}.yaml`.

## What is new in v4.0 — the Oracle Mesh (sitting on top of the foundation models)

v4.0 makes PEN-STACK the **composition + verification layer over the biomolecular foundation models**. It
wraps AlphaGenome, Evo2, AlphaFold3, Boltz-2, Chai-1, Protenix, ESM3, RFdiffusion and ProteinMPNN under one
contract that carries each model's provenance, native uncertainty, and a **scope card** stating what it is
valid for — then routes their outputs through the rule-grounded verifier and the calibrated trust layer. A
generated sequence or structure is always a **candidate to be checked, never a claim**. For the writer enzyme
itself, v4.0 builds **verification, not invention**: proposed/variant writers are scored against measured DMS
data and predicted structure, recovering known enhanced variants blind and refusing to assert activity for
anything unsupported.

| Workstream | What it adds | Result |
|---|---|---|
| **O — the oracle mesh** | `pen_stack/oracles/` — `OracleResult{value, provenance(model+version), native_uncertainty, scope_card, output_kind}`; adapters for genome / structure / protein-design / RNA / energetics; deterministic version-pinned cache | one contract; **generative output = candidate** (`as_claim()` raises — the pen-assemble lesson in code); AlphaGenome **OOD-gated**; cross-oracle **disagreement widens the interval**; ViennaRNA + energetics real |
| **WV — writer verification** | `atlas/writer_verify.py` — DMS- + structure-grounded variant scoring; candidate **critique** wired into `verify()` | recovers the known enhancers (**N322P / H50K / R278M**) above measured-worse controls; unmeasured variants flagged, **not claimable**; a generated writer is critiqued (fold/active-site/deliverable/reachable), **never returned as a working pen** |
| **ATLAS — mesh + delivery oracle** | `wgenome/mesh_features.py` (OOD-gated feature hook + honest blind re-validation) + a computable **AAV packaging-margin** delivery rule | atlas re-validation reports **parity** vs v3.x when oracles are deferred (delta 0.0, never hidden); titre-margin flag fires near the AAV capsid limit; immunogenicity magnitude stays a scope flag |

See `docs/oracles.md`, `docs/writer_verification.md`, and `prereg/ws_{o,wv,atlas}.yaml`.

## What is new in v3.4 — the Environment (a place to train and grade genome-writing AI)

v3.4 makes PEN-STACK the surface an AI agent can be **trained and graded** in, the counterpart to v3.3's
verifier (the surface for *checking*): a Gymnasium **environment** whose every action is checked by the
rule-grounded verifier and whose reward is the legal, calibrated plan score; **Genome-Writing Bench v0.3** with
multi-write-type and adversarial robustness probes; and a demonstration of whether plan-confidence actually
predicts documented outcomes. The environment is an **interface + evaluation harness** (near-one-shot
decision) — no claim that a learned policy beats the deterministic planner.

| Workstream | What it adds | Result |
|---|---|---|
| **ENV — the environment** | full `gymnasium.Env`: 5-stage MDP (write_type → site → writer → cargo → delivery), **verifier-driven step validity**, reward = legality gate × L4 calibrated plan score, a reserved **abstain** action for justified refusal; `env/policies.py` (random + greedy-planner) | passes `check_env`; greedy(planner) ≥ random **and** greedy-legal on the frozen seed set (sanity, not a learning claim) |
| **BENCH — Bench v0.3** | `multi_write_type_legality` (route + judge legality across all 6 non-insertion write types) + `adversarial_robustness` (**T13–T16**: out-of-scope-in-disguise, contradictory constraints, prompt-injection, distribution-shift) | multi-write-type accuracy **1.0** vs ungrounded **0.0**; verifier-backed agent passes **4/4** adversarial probes vs an over-confident baseline **0/4**; **no-fabrication holds even under prompt injection** |
| **CAL — outcome-calibration** | `validate/outcome_calibration.py`: plan-level reliability diagram + ECE + bootstrap-CI selective prediction on the DOI writer panel | **honest result** — useful for *ranking* (high-confidence 0.30 vs low-confidence 0.0 documented-choice recovery, gap CI95 [0.17, 0.43], monotone) but **poorly calibrated in absolute terms** (ECE 0.71): high confidence narrows the feasible field, it does not uniquely identify the documented choice |

See `docs/environment.md`, the v0.3 `benchmarks/genome_writing_bench/LEADERBOARD.md`, and `prereg/ws_{env,bench,cal}.yaml`.

## What is new in v3.3 — the Verifier (a type checker for genome writes)

v3.3 lifts the *laws of genome writing* out of code into a **versioned, machine-readable rule base** and
exposes a single **`verify(design) → Verdict`** call: submit a proposed write and get back *legal / illegal +
the named violated rule + a calibrated confidence + a scope flag* — over Python, REST (`POST /verify`), and an
MCP tool (`verify_write`) any AI agent can submit to. PEN-STACK becomes the layer that *checks* what the
foundation models *generate*.

| Workstream | What it adds | Result |
|---|---|---|
| **R — rule base + solver** | the laws lifted into `configs/rules/*.yaml` (9 rules: reachability, fold, payload, multiplex, delivery), each id/kind/mechanism/param/**citation**/test; a solver returning legality + named reasons | a **parity test** proves the rules reproduce the prior in-code decisions (relocation, not behaviour change); positives legal, negatives rejected by the **correct named rule** |
| **D — delivery palette** | the AAV-only assumption replaced by an **8-vehicle palette** (AAV single/dual, lentivirus, HDAd ~35 kb, HSV amplicon >100 kb, LNP-mRNA, eVLP, electroporation) with capacity/integration/cargo-form/DOIs | hard rejects (cargo>capacity, RNP-into-DNA-only-vehicle, non-integrating-goal+integrating-vehicle); immunogenicity *magnitude* declared out-of-scope, never predicted |
| **ROUTE — write-type router** | the fixed insertion chain becomes one sub-graph of a router over insertion / excision / inversion / replacement / regulatory-rewrite / landing-pad / multiplex | each type routes to its rule sub-graph; unsupported/ambiguous types **defer**, never guess |
| **V — verification service** | `verify(design) → Verdict` over Python/REST/MCP; legality (rules) + confidence (v3.2 L4) + scope, kept as **distinct axes** | every Verdict carries legality + (confidence ∨ abstention) + scope; **no fabrication** (every number tool-sourced) |
| **BA — bench + agent** | Bench **v0.2.1** adds **T12 rule-grounded legality-with-explanation**; the agent submits its own plan to the verifier | verifier verdict+reason accuracy **1.0**; an ungrounded judge cannot cite a rule (0.0) — the verifier uniquely supplies grounded reasons; no-fabrication intact |

See `docs/verify.md`, `docs/rules.md`, `docs/delivery.md`.

## What is new in v3.2 — a calibrated, self-aware co-scientist

v3.2 makes the genome-writing funnel **trustworthy**: every value the funnel returns now carries a calibrated
confidence, an extrapolation flag, and — where the biology is beyond any tool here — an explicit "out of
scope." The LLM may plan, but ideas pass through computable filters, and the system says *how much to trust
each number* and *where the edge of its knowledge is*. Every workstream is pre-registered
(`prereg/ws_{uq,ep,mc,ba}.yaml`, SHA-locked) and reports its honest negatives.

| Workstream | What it adds | Honest headline result |
|---|---|---|
| **UQ — calibrated uncertainty + OOD** | conformal prediction intervals / sets over the existing heads (no retraining), an out-of-distribution detector, and selective prediction | calibrated UQ is **useful on the expression axis**: the durability **expression interval covers 0.895** vs 0.90 nominal on held-out chromosomes (within tolerance) and **risk-coverage accuracy rises 0.739→0.930** under abstention. On the **silenced axis it is informative-in-name-only** at this N — the set covers 0.996 with mean size 1.93 of 2 (≈ the full label set), because the head is weak (we say so plainly). OOD fires strongly on a real **chromatin-state** shift (euchromatin→heterochromatin AUROC **0.98**) but is **weak across biological context** — K562→HSPC 0.72, K562→HepG2 0.65, even cross-species mESC→human **0.56** — because chromatin-mark distributions barely move across cell types/species; reported as a heuristic feature-space-novelty signal, not a guarantee |
| **EP — epistemic scope** | a three-tier status (grounded-confident / grounded-extrapolating / not-computable) on every output, plus a known-unknowns registry + scope matcher | out-of-scope probes deferred **1.0**, in-scope false-defer **0.0** (zero fabrication); the no-fabrication hard gate still holds. The unknown funnel (structure→phenotype, in-vivo immunogenicity, long-term durability, epistasis, polygenic, germline) is made *legible*, not closed |
| **MC — mechanistic filters** | a hard target-site/PAM/att-site reachability reject, vehicle-specific delivery-sequence penalties, and an off-target **energetics** model | positive+negative target-site controls 9/9 (a physically impossible writer–site pairing is rejected); off-target **energetics beats the 0.77 baseline at AUROC 0.88** on the comparable (core-disrupted) construction and ships as the default ranker — but a reviewer-driven re-run shows that gap is *mostly the core-penalisation artifact*: with the core held matched, the non-core substitution-identity gain is real but **modest (Δ≈0.04: 0.687 vs 0.646)**; both AUROCs carry a favourable-negative-set caveat |
| **BA — bench v0.2 + uncertainty-aware agent** | four trust tasks (T8 calibration, T9 selective prediction, T10 OOD honesty, T11 out-of-scope) + the agent emits confidence + epistemic status + abstains | the uncertainty-aware agent beats an over-confident baseline **4/4** on the trust tasks; the leaderboard now separates *trustworthy* agents, not just grounded ones |

Optional: a thin **Gymnasium environment interface** (`pen_stack/env/`, `[env]` extra) for agent-developer
interoperability — interface only, no RL superiority claimed. See `docs/uncertainty.md`, `docs/scope.md`,
`docs/mechanistic_constraints.md`.

## What is new in v3.1

v3.1 hardens the honesty of the planning benchmark, surrounds the models with strong baselines, adds a
predicted-structure safety axis, and ships the first benchmark and grounded agent for the genome-*writing*
side of the field. Every workstream is pre-registered (`prereg/ws_*.yaml`, SHA-locked) and reports its
honest negatives, not just its wins.

| Workstream | What it adds | Honest headline result |
|---|---|---|
| **A - De-circularized benchmark** (gate) | retires the circular targeted-intent recovery@k; the headline is now blind safe-harbour discovery, on a gold set scaled from 5 to 16 loci | blind GSH discovery on 16 curated loci: **AUROC 0.68 (95% CI 0.53-0.82)**; validated-only (N=8) **0.70 (CI 0.48-0.91, underpowered)** vs safety-only 0.51 - a weak, honestly-bounded signal (the 0.92-on-5 was fragile). The full Pellenz-2019 35-site set is also included as a separate exploratory tier and scores near chance (0.54) - the model does not over-rank weak computational candidates |
| **B - Strong baselines + safety metric switch** | endogenous-expression baseline, multi-mark ablation, published GSH rule-set; safe-harbour discrimination is the primary safety metric | headline is the learned model's **absolute** discrimination: writability AUROC **0.68 (95% CI 0.53-0.82, N=16)**. The published distance rule is reported as a *qualitative failure case*, not a delta to beat - it scores at/below chance (curated 0.51; validated-8 **0.48**) because validated harbours are **intragenic** (AAVS1/PPP1R12C, CCR5), so a "far-from-genes" prior mis-ranks them; the learned-minus-rule delta is kept only as a non-significant diagnostic. The circular `genotoxic_cis` AUROC is demoted to a labeled diagnostic |
| **C - AlphaGenome integration** | predicted sequence tracks + a predicted **3D structural-risk** axis (Hi-C contact-map deltas) via the hosted AlphaGenome API | per-track transfers well (HepG2 ATAC 0.91), but the *composite* score degrades from predicted tracks, so the measured atlas stays the backbone (flagged) |
| **D - Cargo Polish** | scores the *insert* for silencing/instability triggers (CpG islands, GC, cryptic splice, MFE, silencers) | directional: high-CpG bacterial cassette 0.75 vs CpG-depleted 0.0, every flag carries a fix |
| **E - Genome-Writing Bench v0.1 + PEN-Agent** | the first benchmark for the writing side, plus a grounded agent that cannot fabricate | planner beats the naive baseline 3/3; the grounded agent reaches the planner's numbers only by grounding (0 fabricated). **T7 ungrounded contrast**: the same models with no tools fabricate 100% of tool-only values under a naive prompt (qwen2.5:7b, Nemotron) - so the bench separates grounded from ungrounded agents, not just "did it call the tool" |
| **F - Local recalibration / private-data adaptation** | recalibrate or fine-tune the released models on your own assays, in-container, behind a validation gate | the adapted model activates only if it beats the released model AND a no-skill baseline; the released model is provably unchanged |
| **G - Multiplex + guide QC** | a pairwise translocation-risk screen for multi-edit plans, and a bridge-RNA guide ranker | DSB-free recombinase plans carry ~zero translocation risk by construction; the guide-QC ranker is validated by a **synthetic positive-control unit test** (hand-constructed guides each tripping one failure mode rank below a clean control) - this tests the ranking logic, not real guide outcomes |

The **Genome-Writing Bench** (workstream E) is v3.1's adoption vehicle: a one-command, SHA-locked, leaderboard
benchmark with deterministic scorers and no circular labels. See
[`benchmarks/genome_writing_bench/`](benchmarks/genome_writing_bench/) and `docs/positioning.md`.

## Architecture

```
                           +-------------------------------------------+
                           |            WRITE PLANNER (engine)         |
                           |   inverse design: destination x writer    |
                           |   x cargo/guide x delivery -> ranked plan  |
                           +----------------^-------------^-------------+
                                            |             |
                  +-------------------------+--+      +---+------------------------+
                  |    WRITABLE GENOME (B)     |      |      WRITER ATLAS (A)      |
                  |    flagship reference      |<---->|   companion reference      |
                  |                            | reach|                            |
                  |  - Safety layer (learned)  | ability  - Family targeting KB    |
                  |  - Durability layer (learned)|      |  - Measured scoring axes   |
                  |  - Reachability layer  -----+------+  - Mechanism classifier    |
                  |  -> writability profile    |      |  - DMS variant model        |
                  +-------------------------^--+      +---+------------------------+
                                            |             |
         +----------------------------------+-------------+-------------------------+
         |                       DATA FOUNDATION (bulk-downloadable)                |
         |  hg38 . ENCODE/Roadmap chromatin . Hi-C/LADs . TRIP position effects .   |
         |  RID/VISDB/MLV integration sites . clinical genotoxic CIS . COSMIC .     |
         |  DepMap . gnomAD . GTEx . UniProt . Pfam/InterPro . bridge-recombinase   |
         |  off-target + DMS (Perry 2025)                                           |
         +-------------------------------------------------------------------------+

   Delivery layer (v5.1-5.5, feeds the planner): a safety<->efficacy balance over the 8-vehicle palette,
   with four of five immune/safety axes computed from data/sequence (genotoxicity = VISDB x COSMIC;
   adaptive/CD8 = MHCflurry over the capsid; innate = CpG/dsRNA of the cargo; pre-existing/NAb = serosurveys).

   Platform services (on top of the validated core): PEN-MONITOR (Europe PMC living database),
   grounded RAG/Q&A, a tool-using agent + MCP server, and a Streamlit web app.
```

## How it works

PEN-STACK is organised as **two reference layers + one engine + a services layer**.

| Component | Module | Role | Status |
|---|---|---|---|
| **Writable Genome** (flagship) | `pen_stack.wgenome` | learned per-locus safety x durability x reachability | Paper 1 |
| **Writer Atlas** (companion) | `pen_stack.atlas`, `.mech`, `.score` | cross-family enzyme catalogue + Writer-Targeting KB | Paper 2 |
| **Cross-link** | `pen_stack.atlas.crosslink` | bidirectional writer to locus queries | Paper 2 |
| **Write Planner** (engine) | `pen_stack.planner` | inverse design, `edit_intent`-conditioned | Paper 3 |
| **Delivery immunology** (v5.1-5.5) | `pen_stack.planner.delivery_immunology` + `{genotoxicity,capsid_epitope,seroprevalence}_oracle`, `innate_sensing` | safety↔efficacy balance over the 8-vehicle palette; 4 of 5 immune axes **computed from data/sequence**, magnitude stays a known-unknown ([docs](docs/delivery_immunology.md)) | M2 |
| **Agentic platform** | `pen_stack.agent` | goal to cited, auditable plan; MCP server; one-command deploy | Paper 3 |
| **Bridge off-target engine** | `pen_stack.bridge` | "CRISPOR for bridge recombinases" + guide QC (v3.1) | Paper 4 |
| **Genome-Writing Bench** (v3.1) | `benchmarks/`, `bench/run.py` | first writing-side benchmark; deterministic scorers, leaderboard | M2 |
| **PEN-Agent** (v3.1) | `pen_stack.agent.pen_agent` | grounded write-planning state machine; zero fabrication | M2 |
| **3D structural risk** (v3.1) | `pen_stack.wgenome.structure3d` | AlphaGenome contact-map deltas as a safety axis | M1 |
| **Cargo Polish** (v3.1) | `pen_stack.planner.cargo_polish` | cargo-sequence silencing-risk scan | M1 |
| **Local adaptation** (v3.1) | `pen_stack.adapt` | gated recalibration / fine-tuning on private data | M1 |
| **Multiplex risk** (v3.1) | `pen_stack.planner.multiplex` | pairwise translocation-risk screen for multi-edit plans | M3 |
| **Platform services** | `monitor`, `rag`, `ui`, `server` | living database, grounded RAG, web app, REST API | - |

### Headline results (all blind / pre-registered)

- **Paper 1 (Writable Genome):** a genome-wide atlas of 3,031,030 loci x 3 cell types (K562, HepG2, CD34+
  HSPC) recovers validated safe harbours as highly writable and clinical genotoxic loci as non-writable,
  blind. Durability transfers mouse to human (Spearman rho = 0.42).
- **Paper 2 (Writer Atlas):** 33,370 enzyme systems across 8 families on common measured axes; mechanism
  classifier agrees with the audited labels on the curated core (1.00); cross-link validated on AAVS1.
- **Paper 3 / v3.1 (Write Planner + de-circularized benchmark):** the honest headline is **blind
  safe-harbour site discovery** - run genome-wide (so no on-target identity term fires), the planner's
  writability is tested for whether it ranks held-out safe harbours above matched-context controls. On a
  gold set **scaled from 5 to 16 independent loci** (8 functionally validated + 8 computationally-defined
  universal-GSH, classic harbours + Lin et al. 2024) this is a **weak signal, honestly bounded**: all-loci
  **AUROC 0.68 (95% CI 0.53-0.82)**, validated-only **0.70 (95% CI 0.48-0.91, underpowered at N=8)** vs a
  safety-only baseline 0.51. The earlier 0.92-on-5 was an over-estimate from tiny N; the AUROC is always
  cited with its CI and N. Writer-family recovery@1 = **0.86** vs prevalence 0.29 across 4 families (14 documented writes, including
  honest misses where labs chose a non-minimal-capacity writer - see Limitations). The earlier "recovery@10 = 1.00, McNemar p" for *targeted* intents was definitional,
  not predictive (an on-target identity term dominates), so it is reported only as a specification-compliance
  table - see `docs/benchmark_circularity.md`. A tool-using agent never fabricates a number.
- **Paper 4 (Bridge off-target engine):** to our knowledge the first measured-data-validated tool that
  **nominates and ranks candidate off-target *locations*** for bridge recombinases. On the measured Perry
  2025 data (6,856 real off-targets) the per-position profile confirms the central core (positions 7-9) is
  the specificity determinant, and the model ranks real off-targets above core-disrupted decoys at AUROC
  0.77 vs 0.62 for Hamming. Stated plainly: it is a **screening tool, not a quantitative safety
  calculator**, it does not quantify how much recombination occurs at each site (sequence-risk vs measured
  magnitude, rho approximately 0.30). A first-of-its-kind beachhead for a genuinely unoccupied gap, not a
  Nature-tier breakthrough; the Writable Genome (Paper 1) remains the flagship novelty.

## The Genome-Writing Bench (v0.2.1, M2)

The first benchmark for the **writing** side of genome engineering - *where* to write, *what* writer to use,
*how* to design the cargo, and *what off-target / structural risk* a write carries - complementing the many
editing-side (Cas9 / base / prime) benchmarks. Six tasks, each with a deterministic scorer and a documented
ground-truth source; **no task is scored against a circular label** (it inherits the de-circularization gate).

```bash
python bench/run.py --agent          # one command -> out/bench_results.json + a leaderboard
docker compose run --rm bench python bench/run.py --agent   # same, on the clean image
```

| Solver | Beats naive on | No-fabrication | Note |
|---|---|---|---|
| deterministic planner | 3/3 grounded tasks | n/a | the validated planning tools (reference) |
| naive baseline | - | n/a | safety-only / prevalence / Hamming |
| **grounded LLM agent** (PEN-Agent) | = planner (grounded) | **PASS** | a real LLM drives the tools; reaches the planner only by grounding every value, 0 fabricated |

**Ungrounded-LLM contrast (T7) - the benchmark separates agents, not just "did it call the tool":** the
*same* models with **no tools** fabricate tool-only values. Under a naive prompt, qwen2.5:7b and Nemotron
both fabricate **100%** of planning fields (and invent in-human clinical numbers no tool could produce -
qwen 100%, Nemotron 67% on ungroundable goals). Even *coached* to refuse, qwen still slips (4%) while
Nemotron refuses fully - but the **grounded agent is 0.0 under every prompt and model, by construction**.
Grounding, not prompting, is what removes fabrication. (Transcripts cached under `data/llm_bench_cache/` for
offline replay; `bench/run.py --ungrounded-live` repopulates them on the VM.)

Per-task (planner vs naive): site selection **0.70** vs 0.51 (validated GSH, N=8; all-16-loci 0.68, CI
0.53-0.82), writer recovery **0.86** vs 0.29 (N=14 writes), off-target **0.77** vs 0.62, intent 7/7,
no-fabrication **PASS** (a hard gate). The gold sets were scaled in v3.1.1 and every metric is reported with
its N and CI - see Limitations. **PEN-Agent** (`pen_stack.agent`) is a
grounded write-planning state machine - goal to site to writer to cargo (with Cargo Polish) to off-target
to 3D structural risk to report - that copies every number from a validated tool with provenance and refuses
or degrades rather than invent. See [`benchmarks/genome_writing_bench/`](benchmarks/genome_writing_bench/),
`docs/agent.md`, and the leaderboard submission guide.

## How PEN-STACK connects to the prior repositories

PEN-STACK v3.0 consolidates and re-grounds five earlier projects. Their genuinely reusable assets are
imported here; the originals are archived read-only for provenance and DOI stability. This is what makes
PEN-STACK "the thing you cite instead of rebuilding the pipeline."

```
  genome-atlas  --+  18-family InterPro-audited Pfam whitelist (v1.2.1)  -->  WT-KB + mechanism classifier
  mech-class  ----+  multi-source mechanism classifier                   -->  family / mechanism calls
  pen-score  -----+- 9 scoring axes (dsb/cargo/deliv/immuno/prog/...)     -->  re-grounded therapeutic axes
  pen-assemble  --+  IS110 ortholog / design set                         -->  part of the 1,058-entity universe
  pen-compare  ---+  unified_editor_universe.parquet (1,058) + scorecard  -->  canonical universe + scorecard
```

| Prior repo | Pinned version | What v3.0 reuses | What changed |
|---|---|---|---|
| [genome-atlas](https://github.com/ahmedanees-m/genome-atlas) | v0.7.2 | the audited 18-family Pfam backbone - spine of the WT-KB and the at-scale mechanism classifier | GraphSAGE link-prediction framing retired |
| [mech-class](https://github.com/ahmedanees-m/mech-class) | v0.5.4 | the mechanism classifier (Pfam + RHEA + CRISPRcasdb + UniProt) | reused as the family/mechanism caller |
| [pen-score](https://github.com/ahmedanees-m/pen-score) | v0.1.3 | the scoring axes (deliv / immuno / cargo, ...) | prog/cargo re-grounded; hand-set overrides removed |
| [pen-assemble](https://github.com/ahmedanees-m/pen-assemble) | v0.5.2 | the ortholog sequence set | de-novo chimera generation retired -> DMS-grounded point-variant proposal |
| [pen-compare](https://github.com/ahmedanees-m/pen-compare) | v0.1.0 | the 1,058-entity universe + scorecard scaffold + tests | circular 5-gate "certification" -> descriptive scorecard with blind concordance |

**One canonical assembly path** (`pen_stack/atlas/universe.py::assemble`) feeds the classifier, the scorer,
and the scorecard identical metadata, so the cross-module inconsistency in the prior pipelines cannot recur.

## Repository structure

```
pen-stack/
├── pen_stack/                        the installable package
│   ├── wgenome/                      Writable Genome (Paper 1)
│   │   ├── features.py               unified feature matrix (accessibility + histones + safety + integration)
│   │   ├── safety.py                 calibrated genotoxicity-risk model (chrom-block CV + baseline)
│   │   ├── durability.py             conditional chromatin->expression model (TRIP-trained, transferable)
│   │   ├── writability.py            decomposable safety x durability x reachability integration
│   │   ├── uncertainty.py            v3.2 conformal intervals/sets over the heads (no retraining)
│   │   ├── ood.py                    v3.2 out-of-distribution / extrapolation detector
│   │   ├── structure3d.py            3D structural-risk axis (AlphaGenome contact-map deltas, 11 hijack loci)
│   │   └── export_tracks.py          BigWig / BED atlas export
│   ├── atlas/                        Writer Atlas + WT-KB + cross-link (Papers 1-2)
│   │   ├── schema.py                 pydantic WriterEntry (enforces >=1 DOI per row)
│   │   ├── build_wtkb.py             Writer-Targeting Knowledge Base builder (8 families, tiered)
│   │   ├── expand.py                 ortholog ingestion -> atlas.parquet (33,370 systems)
│   │   ├── crosslink.py              writers_for_locus / loci_for_writer / loci_for_gene
│   │   ├── variant_propose.py        DMS-grounded point-mutation proposal (no chimeras)
│   │   ├── universe.py               THE canonical universe assembly (1,058 entities)
│   │   └── scorecard.py              descriptive scorecard + blind concordance
│   ├── mech/                         mechanism classification at scale (audited 18-family whitelist v1.2.1)
│   ├── score/                        re-grounded axes + therapeutic-readiness scoring
│   ├── planner/                      Write Planner (Paper 3): optimize / cargo / cargo_polish / multiplex / pipeline
│   │                                   + v3.2 target_site (hard PAM/att/core reject) / delivery_constraints
│   │                                   + v3.3 router (write-type dispatch) / delivery_vehicles (8-vehicle palette)
│   │                                   + v5.1-5.5 delivery_immunology (safety<->efficacy balance) and the four
│   │                                     computed immune-axis oracles: genotoxicity_oracle (VISDB x COSMIC) /
│   │                                     capsid_epitope_oracle (MHCflurry) / innate_sensing (CpG-O/E + dsRNA) /
│   │                                     seroprevalence_oracle (anti-vector NAb serosurveys)
│   ├── bridge/                       bridge off-target engine (Paper 4): offtarget / fold_qc / guide_qc / pipeline / cli
│   │                                   + v3.2 offtarget_energetics (position x substitution; held-out 0.88, ships)
│   ├── agent/                        agentic platform: tools / orchestrator / pen_agent / mcp_server / guardrails; v5.0 co_scientist + cite (multi-strategy, self-critique, cited rationale, scope ledger)
│   │                                   + v3.2 epistemic (3-tier status) / scope (known-unknowns matcher)
│   ├── graph/                        v4.5 living world-model knowledge graph (schema/build/query/ingest/cell_types); typed provenanced edges; gated living loop (propose-only)
│   ├── oracles/                      v4.0 L1 oracle mesh: OracleResult contract + adapters (genome/structure/protein_design/rna/energetics) over the foundation models; version-pinned cache; v5.2-5.5 delivery-immunology scope cards (delivery_genotoxicity/capsid_epitope/innate_sensing/seroprevalence)
│   ├── rules/                        v3.3 machine-readable rules engine (schema/evaluators/loader/solver) over configs/rules/*.yaml
│   ├── verify/                       v3.3 verification service: verify(design) -> Verdict (legal+reasons+confidence+scope; v4.0 writer_critique)
│   ├── adapt/                        local recalibration / private-data adaptation behind a gate (v3.1, WS-F)
│   ├── env/                          v3.4 full Gymnasium environment over router+verifier (genome_writing_env + policies; [env] extra)
│   ├── monitor/                      PEN-MONITOR living database (Europe PMC)
│   ├── rag/                          grounded, cited Q&A (hybrid LLM: Ollama primary, Nemotron fallback)
│   ├── validate/                     benchmarks: blind_gsh_discovery / durability_baselines / writer_recovery /
│   │                                   within_locus_ranking / agent_eval / ungrounded_baseline (T7) / adapt_demo /
│   │                                   v3.2 selective_prediction / uncertainty_eval / bench_trust_tasks (T8-T11) /
│   │                                   out_of_scope_refusal / target_site_controls / offtarget_energetics_eval /
│   │                                   v3.3 bench_rule_tasks (T12) / v3.4 bench_writetype_tasks + bench_adversarial_tasks (T13-16) + outcome_calibration
│   ├── data/                         ingestion (genome, chromatin, integration, TRIP, safety annotations)
│   ├── server/api.py                 FastAPI REST (atlas, crosslink, writable, plan, bridge, ask)
│   ├── ui/app.py                     Streamlit web app (16 pages; v3.2 PEN-Agent shows confidence + epistemic status)
│   └── cli.py                        unified CLI
├── benchmarks/genome_writing_bench/  Genome-Writing Bench v0.3 (T1-T16 + co_scientist; tasks / harness / solvers / LEADERBOARD / SHAs)
├── bench/run.py                      one-command bench entrypoint (--agent, --verify)
├── scripts/                          reproducible pipeline drivers (p1_*, p2_*, p4_*, p52/p53 delivery-immunology oracle builds, ws_*_report)
├── configs/                          pinned datasets + thresholds + curation (YAML); v3.2 known_unknowns /
│                                       target_sites / delivery_constraints; v5.1-5.5 delivery_vehicles immune_safety /
│                                       genotoxicity_oracle / capsid_epitope_oracle + capsid_sequences.fasta /
│                                       seroprevalence + oracles/scope_cards
├── prereg/                           SHA-locked success criteria (paper1..4 + ws_a..ws_h + v3.2-v5.5 ws_{uq,ep,mc,ba,
│                                       r,v,route,env,bench,cal,o,wv,atlas,graph,mon,ct,plan,crit,cite,immune,
│                                       genotox,epitope,innate,seroprev} + SHA256 locks)
├── data/curated/                     small committed tables (universe, gene coords, measured bridge profile,
│                                       v3.2 bridge_offtarget_energetics.json)
├── data/llm_bench_cache/             28 cached ungrounded-LLM transcripts (T7, offline/CI replay)
├── data/alphagenome_cache/           cached AlphaGenome predictions (tracks + contact maps; offline reproducibility)
├── tests/unit/                       unit + regression + blind-validation suite
├── docs/                             mkdocs site (cards, tutorials, INFRA, DEPLOY, MCP);
│                                       v3.2: uncertainty.md / scope.md / mechanistic_constraints.md / BACKLOG.md
├── docker/                           CUDA image + UI image + pinned requirements
├── tools/penctl.py                   laptop<->VM orchestrator (paramiko SSH/SFTP, Docker-only)
├── docker-compose.yml                one-command self-hostable platform
└── pyproject.toml  CITATION.cff  CHANGELOG.md  LICENSE
```

> **Data policy.** Large artifacts (3 M-row atlases, BigWig tracks, models) and any third-party copyrighted
> data are *not* committed - they are released via Zenodo (DOI) or fetched from the original source, and are
> reproducible by re-running the scripts. Only small curated tables and derived products live in git.

## Installation and quick start

**From PyPI** (the library, CLI, agent, and pure-logic tools):

```bash
pip install pen-stack            # core
pip install "pen-stack[models,bio,bridge,server,services]"   # full stack
```

The wheel ships the importable package and the command-line tools. The **full data pipeline** (the 3 M-row
atlases, BigWig tracks, and curated configs) is distributed via the cloned repo + Zenodo, per the data
policy below; point an installed copy at a checkout with `export PEN_STACK_HOME=/path/to/pen-stack` to use
the config-driven features. Most users who want the whole pipeline clone the repo:

```bash
git clone https://github.com/ahmedanees-m/pen-stack.git && cd pen-stack
pip install -e ".[dev]"                                   # core + tests
pip install -e ".[models,bio,bridge,server,services]"     # full stack
pytest -q                                                 # 115 tests
pen-stack info                                            # stack status
python bench/run.py --agent                               # run the Genome-Writing Bench (under 5 min)
```

A five-minute quickstart that runs a bench task end-to-end is in [`docs/quickstart.md`](docs/quickstart.md).

Query the stack:

```bash
pen-stack atlas --coverage                                # Writer Atlas coverage (33,370 systems x 8 families)
pen-stack writable --gene CCR5 --ct k562                  # rank writable loci near a gene
pen-stack crosslink --chrom chr19 --bin 55090             # which writers reach AAVS1
pen-stack plan --gene TRAC --intent knock_in_with_disruption --cargo-bp 2000   # inverse-design plans
pen-bridge design --target ACGTGTCTACGTGA --donor TTGCATCTAGGCAC               # bridge design + off-target + QC
pen-stack monitor --back-test                             # PEN-MONITOR living-database scan
```

Self-host the whole platform (API + web app + agent + MCP + LLM), one command:

```bash
docker compose up -d
docker compose exec ollama ollama pull qwen2.5:7b-instruct   # first run only (local fallback model)
# Web app :8501  .  API :8000 (/plan, /bridge/design, /ask)  .  MCP :8765   (see docs/DEPLOY.md)
```

**LLM backend (hybrid, non-load-bearing).** Services (agent, RAG, PEN-MONITOR) use one switch in
`configs/llm.yaml`. On the compute tier (the GPU VM) the default is the **local Ollama model**
(`qwen2.5:7b-instruct`, free, private, tool-calling verified) with **automatic fallback** to the hosted
**NVIDIA Nemotron** (free, no local resources), then to a deterministic no-LLM path. A cooldown cache and
bounded timeouts mean an absent or slow provider degrades in seconds rather than stalling. The LLM is
non-load-bearing - every number and citation comes from a validated tool - so the choice never affects
scientific reproducibility, only orchestration quality. Set `NVIDIA_API_KEY` (or a gitignored
`configs/nvidia_api_key.txt`) for the hosted fallback; a low-RAM laptop with no GPU uses it automatically.
The core scientific compute uses no LLM at all.

## The web platform

`pen_stack/ui/app.py` is a single Streamlit app over the whole stack (11 pages):

- **Writable Genome** - Overview, Forward query (gene to writability/safety/durability), Site finder
  (inverse), Atlas browser, Validation dashboard, Cross-cell-type transfer.
- **Writer Atlas** - family coverage and measured-axis comparison.
- **Write Planner** - goal + `edit_intent` to ranked, traceable plans.
- **Bridge design** - design a bridge RNA, fold/cross-loop QC, genome-wide off-target scan.
- **Ask** - grounded, cited Q&A (numbers from validated tools).
- **Agent** - a goal to a cited, auditable end-to-end plan.

## Data sources (all public)

hg38 (UCSC); ENCODE / Roadmap chromatin (ATAC/DNase + histone marks; K562, HepG2, CD34+ progenitor, mouse
ES-Bruce4); GENCODE v46; COSMIC Cancer Gene Census v104; DepMap Public 26Q1; LaFave 2014 (NHGRI GeIST) MLV
integrations; VISDB; TRIP / Akhtar 2013 (GEO GSE49806/49807); UniProt orthologs; Pfam/InterPro; Europe PMC;
Addgene; Perry 2025 bridge-recombinase off-target + DMS data (Science adz0276; copyrighted - kept local,
only derived products released). Every accession and DOI is pinned in `configs/datasets.yaml` and
independently verified.

## Validation philosophy

- **Pre-register before training.** Success criteria, baselines and held-out sets are SHA-locked in
  `prereg/` (paper1..4) before any model sees test data.
- **Always report an honest baseline** (oncogene-distance for safety; H3K9me3/LAD for durability;
  intent-blind ranking for the Planner; Hamming for the bridge engine).
- **Blind external concordance** - recover validated safe harbours, clinical genotoxic loci, documented
  writes, and measured off-targets the model never trained on.
- **Report failure honestly** - cross-cell-type degradation, small benchmark N, and the limits of
  sequence-only off-target magnitude prediction are quantified results, not footnotes.
- **Every estimate carries its N and CI; statistical power is a stated limitation.** The validated gold
  sets are small: blind GSH discovery rests on 8 functionally-validated harbours (16 curated loci; +35 Pellenz-2019
  exploratory candidates reported separately, near chance), writer recovery on 14 documented writes, within-locus on 5 loci, the
  3D structural sanity on 11 hijacking loci, and the LLM-agent bench on a few goals. Headline AUROCs are
  bootstrap-CI'd and the CIs are wide - e.g. blind GSH discovery is **0.68 (95% CI 0.53-0.82)**, not a
  precise 0.92. Scaling these gold sets (the literature has dozens of candidate harbours and many documented
  large-cargo integrase/CAST/PASTE writes) is the top priority for turning this from a proof of concept into
  an adopted resource; v3.1.1 began that scaling (5 -> 16 GSH loci).
- **Grounded services** - every quantitative answer comes from a validated tool call (never a language
  model); the living database never auto-edits the atlas; clinical directives are refused.

## Papers and phases

| # | Title | Phase | Status |
|---|---|---|---|
| 1 (flagship) | The Writable Genome: a predictive, writer-aware atlas of safe & durable insertion sites | 1 | complete |
| 2 (platform) | PEN-STACK: unified open infrastructure for non-destructive genome writing | 2 | complete |
| 3 (capstone) | The Write Planner: end-to-end inverse design of genomic writes | 3 | complete |
| 4 (beachhead) | Genome-wide off-target prediction for RNA-guided bridge recombinases | 1.5 | complete |
| M1 (v3.1) | Writable Genome hardened: strong baselines, AlphaGenome sequence + 3D structural-risk axis | v3.1 B,C,D,F | complete |
| M2 (v3.1) | The Genome-Writing Bench + PEN-Agent: the writing-side benchmark and a grounded agent | v3.1 E | complete |
| M3 (v3.1) | Multiplex translocation-risk + bridge-RNA guide QC | v3.1 G | complete |

The v3.1 cycle (workstreams A-H) is recorded in `CHANGELOG.md`, `docs/positioning.md`, and the SHA-locked
`prereg/ws_*.yaml`; preprint drafts are in `manuscripts/`.

Per-phase build records, execution summaries, and Zenodo deposit packages are kept alongside the program
plan. Data releases are deposited on Zenodo (one per paper).

## Citation

```bibtex
@software{penstack2026,
  author  = {Mahaboob Ali, Anees Ahmed},
  title   = {PEN-STACK: open infrastructure for genome writing (The Writable Genome)},
  year    = {2026},
  version = {3.3.0},
  url     = {https://github.com/ahmedanees-m/pen-stack}
}
```

**Author:** Anees Ahmed Mahaboob Ali, VIT University, Vellore. MIT licensed.

*Decision-support, not a clinical directive - every score is traceable to public data and a pre-registered
model.*
