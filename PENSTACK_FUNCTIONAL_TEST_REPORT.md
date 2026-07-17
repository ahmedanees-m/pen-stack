# PEN-STACK v8.0.5 — Rigorous Functional Test Report

**What this is:** a hands-on functional verification of the PEN-STACK *application* — every design stage from intent
through enzyme, locus, durability, writability, delivery, integration efficiency, off-target, verification,
biosecurity, immunogenicity, expression, oracles, and the closed loop — driven with **my own varied example inputs**
(including adversarial, out-of-scope, and invalid ones) and judged as a genome-writing domain expert on three axes:
does it **run**, are the results **scientifically plausible**, and does it stay **honest** (refuse / abstain /
return a known-unknown instead of fabricating).

**How it was run:** the installed package (v8.0.5) was exercised directly through the SDK/CLI across **~80 distinct
scenarios** organised into 6 stage-cluster batteries + 5 end-to-end integration scenarios, each battery followed by an
**independent adversarial re-run** that tried to break the honesty invariants. Environment: the bare clone with the
committed one-chromosome demo atlas (k562/chr19); heavier data (full genome atlas, other cell types) and external
model backends are not present, so their honest data-gating/abstention is scored as a PASS, not a failure.

---

## Verdict: **Functionally sound. The honesty contract holds under adversarial testing.**

Every stage runs and returns scientifically plausible results across varied inputs. Of ~27 explicit honesty
invariants probed, **25 HELD** and **2 BROKE** — both traced to the same class of issue (a value applied/attached
where it should have been withheld), both **medium**, neither a fabrication of a *scientific* result presented as
validated. No high-severity defects. The core no-fabrication invariant, the biosecurity gate, the immune
non-collapse, the candidate/claim guard, and the data-gating all survived every attack I threw at them.

| Severity | Count | Items |
|---|---|---|
| High | 0 | — |
| **Medium** | **2** | (1) `AAVS1`→"aav" substring injects a false `delivery_limit=AAV_single`; (2) Cas12a candidate-scoring path applies SpCas9 calibration instead of abstaining |
| Low | ~7 | input-validation / robustness / interface-consistency edge cases (below) |

---

## Per-stage results

| Stage | Feature | Verdict | Evidence (my inputs) |
|---|---|---|---|
| **A** Intent | Typed WriteSpec extraction, ontology resolution, feasibility SAT | **MOSTLY_PASS** | "Insert 2 kb GFP at AAVS1 in K562 w/ serine integrase" → HGNC `PPP1R12C`, GRCh38 `chr19:55040914-55167637`, SO CDS/promoter/polyA ids, `no_fabrication=true`. Underspecified "edit a gene" → 3 clarifying questions, fields null. Nonsense gene → stays null. Feasibility: 2 kb feasible; 20 kb/AAV infeasible with named blocker + repair. |
| **B** Writable site | safety × durability × writability, blocklist | **PASS** | AAVS1/k562 real rows; verified `writability == 0.5·safety + 0.5·p_durable` numerically. hepg2/hspc → `FileNotFoundError` (honest data-gate). Off-chr19 genes → 0 rows (honest). Blocklist config = exactly the 8 documented loci; overlay zeroes safety 0.9→0.0 and recomputes writability. |
| **C** Writer/enzyme | selection, efficiency (interval), guide/att, mechanism, capacity | **PASS** | Ranked families (bridge_IS110→serine→PE→CAST) across 5 intents × 3 cargo sizes; large cargo → capacity warning. Efficiency returns a % with a conformal interval, **candidate-labelled** (pre-registered null honestly retained). Guide design **abstains** without a target sequence. |
| **D** Delivery vector | vehicle choice, capsid fitness, tropism | **PASS** | DNA/mRNA/RNP × {1 kb, 4.7 kb, 9 kb}: 9 kb correctly needs dual/split-AAV or lentivirus (capacity math right). AAV9→CNS, AAV5→liver, AAV2→retina grounded to approved-therapy DOIs; **novel capsid tropism abstains**; capsid-fitness model absent → **abstains**, no fabricated score. |
| **C** Integration efficiency | learned writer-efficiency predictor | **PASS** | Predictions carry a split-conformal interval and the candidate label; KB ranking stays primary (the pre-registered leave-one-family-out gate that failed is honored). |
| **E** Off-target | all 5 writer classes, truthful status | **MOSTLY_PASS** | Nuclease finder enumerated genome-wide sites w/ CRISOT, empirical active fraction, risk band, `output_kind=candidate`, `nomination_is_not_clearance`; **more mismatches → lower risk (monotone)**. Serine-integrase/bridge/CAST/PASTE all carry truthful `mechanism_based_unvalidated`. **Cas12a finder abstains (honest); candidate-scoring path does NOT (medium bug, below).** |
| **F** Verify / legality | rule base, repair-oriented proof | **PASS** | 2 kb/AAV legal; 8 kb/AAV illegal + repair hint; 8 kb/lenti legal. RNP-in-AAV and mRNA-in-AAV → `delivery.cargo_form_compatible: violate`. `verify_proof` returns 3 axes with `collapsed=None`, `no_fabrication=true`. |
| **F** Biosecurity | design-stage screen, runs first | **PASS** | Benign (GFP, Factor IX, CAR-T TRAC, BCL11A) → clear. Controlled hazards (ricin, botulinum, variola) → **refuse** with Select-Agent/Australia-Group/taxon provenance. Empty submission → clear **but `declared_signal=false`** (not a clearance). A hazard word placed only in a non-declared free-text field is correctly **ignored** (reads declared fields only). Standards concordance **8/8**. |
| **G** Immunogenicity | 5 axes, never collapsed | **PASS** | `collapsed_score=None` on every combo. Scientifically correct: genotoxicity AAV **1.0** (episomal) vs lentivirus **0.514** (integrating); pre-existing NAb AAV **0.6**, Ad5 **0.35**, LV **0.975**; writer foreignness=1.0 with a 0.0 human-proteome self-match. Out-of-scope axes abstain; patient titre = known-unknown. |
| **H** Expression / outcome | relative expression, position-effect head | **PASS** | 31-promoter palette; `predict_outcome` **reacts to the promoter** (live lever); interval widens under OOD; over-capacity cargo fires the feasibility flag; `outcome_validated` is resolution-aware (coarse→false, honest). |
| **I** Oracle mesh | reliability verbatim, cache-or-abstain | **PASS** | 13 oracles: ViennaRNA live in-process; all foundation-model backends honestly `live=false`; reliability `set` only where a published benchmark exists, `null` otherwise. `predict_affinity` out-of-scope pairs (protein–protein, protein–DNA) → `in_scope=false, extrapolating=true`. |
| **J** Beyond one design | generate, experiment designer, closed loop, graph | **PASS** | World-model graph resolves AAVS1 (curated), TRAC/HBB/LMO2 (non-GSH, tier-1 candidates), aliases (PPP1R12C→AAVS1, ROSA26→hRosa26), unknown→**0 answers**. `generate_designs` → guarded 6-design Pareto front, **0 hazardous/illegal**. `select_batch` acquisition **varies** (2.02/1.22…, not the old constant). Cloud-lab benign → mock receipt; hazard → refused (S3). |
| **K** PEN-CHAT | 4-lane router, grounding | **PASS** | A write request routes to `design` and **never leaks** to a non-grounded lane; meta/general classified correctly; a dual-use request routes to the safety-handled general lane, not to a grounded design lane. |

---

## The two medium findings (both independently confirmed)

### M1 — `AAVS1` locus name triggers a false AAV delivery constraint (Stage A)
The intent extractor's vehicle detector checks `if "aav" in text`, which matches the **"aav" inside "AAVS1"**. Result: a
request to insert a 6 kb transgene at the AAVS1 safe harbour gets an **unstated** `constraints.delivery_limit =
"AAV_single"`, labelled `provenance="explicit"`.

```
parse_request("Insert a 6 kb transgene into the AAVS1 locus ...") → constraints.delivery_limit = "AAV_single"
parse_request("Insert a 6 kb transgene into the CCR5  locus ...") → constraints.delivery_limit = null   (control)
```

**Why it matters:** AAVS1 is *the* most common safe-harbour target, and a 6 kb cargo exceeds single-AAV capacity
(~4.7 kb). A feasible design (e.g. via lentivirus) can therefore be wrongly flagged over-capacity/infeasible purely
because of the locus's *name*, and the injected constraint is mislabelled as user-stated (`explicit`). **Fix:** match
vehicle tokens on word boundaries / a serotype vocabulary, not substrings.

### M2 — Cas12a candidate-scoring path applies SpCas9 calibration instead of abstaining (Stage E)
`cas12a` is a member of the internal `_NUCLEASE` routing set, and the caller-supplied-`candidate_sites` branch has no
Cas12a guard. So:

```
nominate_offtargets("cas12a", guide=…)                       → abstain=True  (finder path — honest ✓)
nominate_offtargets("cas12a", guide=…, candidate_sites=[…])  → abstain=False, family="nuclease",
                                                                risk_band="high" from SpCas9 mismatch calibration
```

The genome-wide *finder* correctly abstains for Cas12a (the CRISOT scorer + mismatch-risk calibration are
SpCas9-specific, per v7.3.1), but the *candidate-scoring* path silently applies that SpCas9 calibration to Cas12a and
relabels the family. The numbers are still tagged `output_kind=candidate` / `nomination_is_not_clearance` (so it is not
asserted as *validated*), which bounds the harm — but a SpCas9-specific empirical risk band should not be emitted for a
different enzyme without the same abstention. **Fix:** apply the finder's Cas12a abstain gate to the candidate-scoring
path too.

## Low-severity findings (robustness / input-validation / interface consistency)
- **Stage A:** mixed-verb prose ("multiplex knockout of TRAC and B2M") mis-classifies by keyword priority and drops the
  second target; a symbol-shaped nonsense token (≤7 chars) is passed through as a low-confidence *unvalidated* id
  instead of staying null (length-dependent vs a longer nonsense token); "HeLa or Jurkat" is silently committed to one.
- **Stage C:** `recommend_writers` reads `request["write_type"]` while the CLI/docs use `intent`, so the documented key
  is silently ignored (a `intent="excision"` request returns an insertion). Learned-efficiency point estimate is not
  clamped to a physical [0,100] on out-of-distribution input.
- **Stage D/H:** `recommend_delivery_plus` accepts a negative `cargo_bp` and an unknown `cargo_form` without a
  validation flag; `predict_outcome` scores an unknown/typo promoter to a neutral 0.5 default silently; a nonsense
  `writer_family` is accepted without setting `extrapolating`; `AAVrh74` tropism returns `doi=null` while naming the
  approved therapy (grounding-completeness gap). All are *conservative* (no inflated claim), just under-flagged.
- **Stage E:** family alias `lbcas12a` isn't routed into the nuclease set; an unrecognized serine-integrase selector
  (`PhiBT1`) silently falls back to Bxb1 rather than abstaining.

**None of these fabricate a scientific result** — they are missing input-validation guards and one naming collision.

---

## Honesty-invariant scorecard (adversarially probed)

**HELD (25):** candidate `.as_claim()` raises · `OracleResult`+`Provenance` frozen/immutable · known-unknowns exposed
as machine-readable values · capability manifest no-fabrication guarantee · ontology id-format validator real ·
writability formula transparent/reproducible · cell-type & atlas data-gating **raises** rather than fabricates ·
off-atlas genes return honest empty · efficiency candidate-labelled with uncertainty · pre-registered negative
reported · fabricated writer variants get no activity score · guide/att design abstains without a sequence · efficiency
not extrapolated to unseen families · unrecognized write_type echoed (not relabelled) · blocklist point-queries carry
provenance · novel capsid abstains · capsid-fitness absent → abstain · tropism grounded-or-known-unknown · outcome
intervals labelled non-conformal · OOD flagged + interval widened · over-capacity flagged not-buildable · data-gated
heads return null · nomination ≠ clearance on every off-target path · integrase/bridge/CAST/PASTE carry truthful status
· adversarial/invalid inputs abstain or error cleanly (no crash, no fabrication).

**BROKE (2):** the extractor attached an unstated constraint mislabelled `explicit` (M1) · Cas12a candidate-scoring
mis-applied SpCas9 calibration instead of abstaining (M2).

---

## End-to-end integration scenarios

| Scenario | Verdict | Coherent? | Notes |
|---|---|---|---|
| **S1 — CAR-T TRAC knock-in** (A→C→D→E→F→G→H) | MOSTLY_PASS | Yes | Composes end-to-end; the TRAC site step (off-chr19) data-gates honestly rather than crashing. |
| **S2 — Large-cargo dual-AAV at AAVS1** | **PASS** | Yes | 9 kb single-AAV → illegal + repair hint → apply repair (dual/lenti) → **re-verify passes**. The composition/repair contract works. |
| **S3 — Hazard refusal (ricin / botulinum)** | **PASS** | Yes | Refused at the verify stage **and** at closed-loop cloud-lab export; **no protocol emitted**, no fabricated legality/confidence. Cannot be bypassed via the normal action space. |
| **S4 — Sickle-cell BCL11A (benign)** | **PASS** | Yes | Clears biosecurity, concordant, immune + outcome computed — the gate discriminates benign from S3's hazards. |
| **S5 — Grounded co-scientist session** | MOSTLY_PASS | Yes | Deterministic (no-LLM) dossier composes multiple stages; every surfaced quantity traces to a tool, candidates labelled, `no_fabrication=true`. |

---

## Bottom line

PEN-STACK's stages all function and interoperate, and — the property the paper stakes itself on — the platform
**refuses, abstains, and data-gates instead of fabricating**, and it held that line under ~80 varied and adversarial
inputs. The scientific outputs are plausible and correctly scoped (capacity math, tropism grounding, genotoxicity
ordering, mismatch monotonicity, immune non-collapse). The two medium findings are a substring name-collision (M1) and
a two-code-path inconsistency in Cas12a off-target scoring (M2); both are precise, both are fixable in a few lines, and
neither undermines the substrate's central non-fabrication guarantee. The remaining items are ordinary input-validation
hardening. This is a functionally robust, honest platform.

*Every result above was produced by executing the installed package; the two medium findings each ship with a one-line
reproduction.*
