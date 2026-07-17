# GigaScience Reviewer Report — PEN-STACK v8.0.5

**Manuscript:** *PEN-STACK: a non-fabricating tool layer for language-model agents in genome writing*
**Software:** `pen-stack` 8.0.5 — https://github.com/ahmedanees-m/pen-stack
**Review type:** Reproducibility / usability / utility (GigaScience criteria), with a hands-on cloud run of the software.
**Reviewer environment:** fresh clone in an isolated Linux cloud container, Python 3.11.15, Docker 29.3.1, 4 cores / 15 GB RAM. No GPU, no API keys, no Zenodo artifacts (bare-clone conditions — exactly the "competent non-specialist reproduces this from scratch" case).

---

## Recommendation: **Accept with minor revision.**

The one blocking item for a final DOI-bearing record — the Zenodo deposit (concept DOI) — is explicitly out of scope for this round per the author's note and is the only item preventing a clean "accept." Everything I could execute, executed and matched the manuscript. I recomputed **both** headline results from committed source on a bare clone and they reproduced to the digit. The no-fabrication invariant, the biosecurity gate, and the honesty ledger are not just described — they are enforced in code and I was able to trip them on demand.

This is, by GigaScience's own stated yardstick (reproducibility, usability, utility over subjective "impact"), an unusually strong submission.

---

## 1. What I ran, and what happened

| # | Test | Result |
|---|------|--------|
| 1 | Clean-venv install from source `pip install -e .[dev]` | **PASS** (exit 0); import + CLI entrypoints work |
| 2 | `pip install pen-stack==8.0.5` from PyPI (published wheel) | **PASS**; ships + reads its package data outside the repo (v8.0.4 fix holds) |
| 3 | `make repro` (the reproducibility gate) | **PASS** (exit 0); both headlines re-derived from source, match to the digit |
| 4 | Full test suite `pytest -q` | **PASS** (exit 0); 664 collected, all pass, **80% line coverage** (matches the claim); skips are heavy-optional-dep only |
| 5 | All 10 stages + PEN-CHAT via SDK / CLI / REST / MCP | **PASS**; behaviour matches manuscript incl. the honest refusals |
| 6 | Docker image build/run | **Blocked by sandbox network policy** (Docker Hub base-image CDN 403), *not* a PEN-STACK defect — see §6 |

### Dependency-drift stress test (unplanned bonus)
The install pins are lower-bounds, so a bare clone today resolves to the **newest** scientific stack: NumPy 2.4.6, pandas 3.0.3, scikit-learn 1.9.0, pydantic 2.13, LightGBM 4.6. Everything — including the model that recomputes ρ=0.571 — still builds, imports, trains, and reproduces. That is a much harder reproducibility bar than a frozen lockfile and it passed. This is worth noting to the editor: the result is robust to library drift, not just to a pinned environment.

---

## 2. Reproducibility (the GigaScience core criterion) — **exemplary**

`make repro` on a bare clone, no download, no key, reproduced:

- **Human K562 expression-robustness head, re-derived from the committed source table** (`scripts/p2_build_human_head.py`): shipped-twin full **ρ = 0.5711**, independent/de-circularised variant **0.5580**, learned chromatin baseline **0.493**. Asserted within 0.02 of the sealed metrics → **PASS**. This is the manuscript's headline (ρ ≈ 0.571) and it is *recomputed*, not echoed.
- **Prior-art distinctness vs ePRIDICT**, re-derived from source (`scripts/pa_epridict_distinctness.py`): Spearman **ρ = 0.21177**, Pearson 0.20151, OLS **R² = 0.04061** on n=7,295 shared K562 loci — **exact** match to committed values; decision **DISTINCT** (96% of durability variance unexplained by efficiency).
- **Grounding benchmark** (LLM live, replayed from committed transcripts): naive plan-fabrication **98.8% / 90.8% / 96.7%** (Claude Haiku 4.5 / Nemotron 120B / Qwen 1.5B), coached **0.0% / 0.8% / 1.7%**, grounded agent **0.0** — the monotone-with-scale coaching failure the paper's central argument rests on, reproduced verbatim.
- **Agentic no-fabrication audit**: three model families each drove the tools on 4/4 goals with the audit **PASS**; the deterministic no-LLM gate **8/8 PASS**.
- **Benchmark integrity**: frozen `SHA256SUMS` verified 7/7 files unmodified.

The reproduction target is wired into CI and exits non-zero on drift, so this cannot silently decay. **This is the strongest form of the GigaScience reproducibility criterion: the paper's numbers regenerate from the repository, and the repository fails loudly if they stop matching.**

Secondary metrics that need un-committed bulk data (genome-wide atlas, hg17) are printed with an explicit *sealed-metric* annotation and are not passed off as re-derivations — an honest and correct distinction.

The test suite corroborates: **664 tests collected, all passing, 80% line coverage** — the exact figure the manuscript states — with the REST/MCP/SBOL3/GenBank feature tests bundled into the default `[dev]` install so no claimed surface is silently skipped. The only skips are the heavy externally-licensed/GPU/network integration tests, which are documented as such.

---

## 3. The central claim — no fabrication — is real and enforced, not asserted

I verified the invariant is a property of the type system, not the prose:

- A generative candidate (`OracleResult(output_kind="candidate")`) **raises `ValueError` on `.as_claim()`** — I tripped it directly.
- The result type is **frozen**: assigning `output_kind = "claim"` on a returned object raises `ValidationError`. Provenance is frozen too.
- Generative capsid design **abstains** ("capsid-fitness model not present → cannot score generated capsids; no fabrication") rather than inventing candidates.
- Out-of-scope quantities return as explicit **known-unknowns** (`/scope` lists 10; the immune profile abstains on uncached axes with `in_scope: false`, `value: null`).

Given no tools, the models fabricate 91–99% of the quantities a plan needs; driving the same tools they fabricate none. I reproduced both halves. The argument holds.

---

## 4. Per-stage functional check (all 10 stages + the invariant)

Every stage was exercised on the SDK, and cross-checked on the REST API and MCP server. All behaved as documented, **including the honest failures**:

- **A — Typed intent:** "Insert a 2kb GFP cassette at AAVS1 in K562" → typed `WriteRequest` with live-verified ontology IDs (HGNC `PPP1R12C`, SO:0000316 CDS, GRCh38 `chr19:55040914-55167637`), per-field provenance, `no_fabrication: true`.
- **B — Writable site:** AAVS1 writability 0.99 with the decomposed `0.5·safety + 0.5·p_durable` formula surfaced; unmeasured cell types 503 rather than extrapolate.
- **C — Writer:** ranked families (bridge_IS110 → serine_integrase → PE_integrase → CAST_VK) with the KB-ranking-primary / learned-efficiency-candidate split intact; guide design **abstains** cleanly when no target sequence is supplied.
- **D — Delivery:** ranked vehicles with per-vehicle immune tiers + provenance; AAV9 tropism **grounded to Zolgensma** (DOI 10.1056/NEJMoa1706198); novel-capsid in-vivo tropism abstains (known-unknown).
- **E — Off-target:** nuclease finder enumerated **2,609 genome-wide sites** (1 on-target + 2,608 off) with CRISOT scores, empirical active fractions, mismatch-calibrated risk bands, each `output_kind: candidate` and `nomination_is_not_clearance`; Cas12a path correctly abstains; per-mechanism assay recommender returns GUIDE/CHANGE/CIRCLE/SITE-seq.
- **F — Verify / biosecurity:** over-capacity design → `legal: false` with a machine-readable repair hint; **ricin → refuse** (Select Agent provenance), **GFP → clear**, **empty submission → clear but `declared_signal: false`** (the crucial "nothing was screened ≠ cleared" distinction, working); standards concordance **8/8**.
- **G — Immunogenicity:** five axes, `collapsed_score: None` (never averaged), out-of-scope axes abstain, `no_fabrication: true`.
- **H — Expression twin:** relative-expression estimate with an honest heuristic band + resolution-aware `outcome_validated` semantics; 31-promoter palette live.
- **I — Oracle mesh:** published reliability surfaced verbatim, unverified numbers left `null`, backends that are absent report "not available" rather than crash.
- **J — Beyond one design:** world-model graph resolves AAVS1 (curated safe harbour) and TRAC (flagged non-GSH, tier-1 candidate writers); cloud-lab submission is safety-gated.

**MCP server:** boots under FastMCP and registers **exactly 22 tools** (manuscript claim confirmed). **REST API:** boots, `/health` reports 8.0.5, ~42 endpoints live.

---

## 5. Honesty ledger — spot-checked and holds

I independently verified the sharpest ledger entries:

- **Claim 7 (clinical genotoxicity false-negatives → deterministic blocklist):** the deployed blocklist config contains **exactly the eight documented loci** (LMO2, CCND2, MECOM, PRDM16, HMGA2, SETBP1, BMI1, MN1); the overlay zeroes safety (0.9 → 0.0) and recomputes writability (0.85 → 0.40) for a flagged bin while leaving safe bins untouched. The code comments state plainly it is a *completeness fix, not a novel-locus predictor* — the honest framing the paper claims.
- **Claim 1 (ρ=0.571) PASS** and **Claim 5 (AUROC 0.37 null)** are both present in the served/committed metrics and recomputed/echoed appropriately.

The pattern the paper argues — "a system that cannot construct an unsupported number also cannot conceal an unflattering one" — is observable in the artifact.

---

## 6. The one thing I could not run: the Docker image

`docker build` failed **only** at pulling the base image `python:3.12-slim`: the Docker Hub layer-blob CDN returned HTTP 403 through this environment's mandatory egress proxy (a network-policy restriction of my sandbox, logged as a gateway CONNECT denial). This is **not** a defect in PEN-STACK.

Mitigating evidence that the image is sound: the `Dockerfile` is well-formed (pinned public base, the single correct system dep `libgomp1`, `pip install -e .[dev]`, a build-time smoke test, `CMD make repro`). **Every command the image runs, I ran natively on the same code and dependency set, and each passed** — the install, the `import pen_stack` + demo-atlas smoke test, and `make repro`. I am confident the image builds and runs wherever Docker Hub is reachable; I simply could not fetch the base layer here. *Recommendation to the editor: no action needed from the author; if desired, a reviewer on an unrestricted network can confirm the one pull.*

---

## 7. FAIR assessment

| FAIR facet | Finding |
|---|---|
| **Findable** | GitHub homepage, PyPI (`pen-stack`), `CITATION.cff`, RRID/bio.tools placeholders flagged for insertion. Zenodo concept DOI **pending** (the known remaining item). |
| **Accessible** | `pip install pen-stack` works today; MIT license; no credential or paywall on the request path; bare clone runs offline. |
| **Interoperable** | Typed results; SBOL3 + GenBank round-trips; MCP (open protocol) + REST + SDK; ontology IDs (HGNC, SO, MONDO, Cellosaurus, ChEBI, GRCh38) live-verified. |
| **Reusable** | MIT code; CC0 data resources; per-row DOIs + verbatim source quotes in the writer-efficiency KB; `DATA_SOURCES.md` + `DATA_LICENSES.md` with a CI test that fails if licensed data ever ships; 161 SHA-locked pre-registration/lock files; 20 committed benchmarks with frozen splits. |

Data provenance is handled to a standard well above the typical submission: licensed sources (COSMIC, OncoKB, Perry 2025) are referenced by accession only and a unit test enforces that they never appear as shipped derived data.

---

## 8. Assessment against the five review dimensions

- **Novelty —** The contribution is correctly and modestly framed: *not* novelty in agentic orchestration (explicitly disclaimed), but (i) the first calibrated, non-fabricating tool *substrate* for genome **writing** (as opposed to editing), and (ii) the measured demonstration that anti-fabrication prompting is a scale-dependent correlation, not a guarantee. Both are genuinely new and useful. **Strong.**
- **Originality —** The type-enforced no-fabrication invariant (candidates that raise on assertion; frozen provenance; known-unknowns as values) as *importable code* rather than a described method is an original and portable idea. The writer-efficiency KB and the human K562 exact-site position-effect head are new, independently reusable resources. **Strong.**
- **Validity —** Externally validated where it can be (ρ=0.571 on a pre-registered held-out split, circularity-guarded), null where it must be (6 of 10 pre-registrations returned nulls, all shipped as machine-readable flags), and refusing where no ground truth exists. I reproduced the headline validations from source. Claims are scoped, not overstated. **Strong.**
- **Usability —** `pip install` → working CLI in one step; a demo atlas makes the quickstart run on a bare clone; four coherent surfaces (SDK/CLI/REST/MCP) + a React web app; clear docs. Minor friction only (see below). **Strong.**
- **Significance / utility —** For GigaScience's "utility over impact" test this scores well: an agent builder gets a drop-in grounded tool layer over an open protocol; a bench scientist gets a cited, refusing shortlist. The reusable fabrication corpus and the "honesty ledger as a reporting norm" proposal have utility beyond this domain. **Strong.**

---

## 9. Minor revisions requested

1. **Zenodo deposit + concept DOI** (already flagged by the author) — required for the archived version of record and the Data Availability statement. This is the only item gating a clean accept.
2. **Author-action placeholders** in the manuscript should be resolved before typesetting: ORCID, RRID (SciCrunch), bio.tools ID, Funding statement, AI-assisted-technology disclosure, Acknowledgements.
3. **MCP tool count consistency (cosmetic):** the MCP server registers 22 tools (verified) while the public `capability_manifest` / `/capabilities` lists 20 curated capabilities. Both are internally consistent, but a one-line note reconciling "22 MCP tools" vs "20 advertised capabilities" would pre-empt a confused reader.
4. **Docker base image:** consider pinning the base by digest (`python:3.12-slim@sha256:…`) for a fully hermetic image, and note in the README that behind a restrictive proxy the base pull is the only external dependency of `docker build`.
5. **`git` tags:** the reviewed clone had the six clean topic commits but no `v8.0.5` tag locally visible; ensure the release tag is pushed so `CITATION.cff` / reference [46] resolve to an immutable commit.

None of these affect the scientific content or the reproducibility result.

---

## 10. Bottom line

PEN-STACK does what the manuscript says it does. I installed it three ways, reproduced both headline numbers from source on a bare clone under a *newer* dependency stack than the authors used, drove all ten stages plus the biosecurity gate and the no-fabrication invariant, and confirmed the honest failures are shipped as machine-readable flags rather than buried in prose. The engineering claim — that grounding, not prompting, removes fabrication, and that this belongs in the type system — is substantiated by the artifact, not merely argued. Pending the Zenodo deposit and the routine author-action fields, this meets and exceeds GigaScience's reproducibility, usability, and utility bar.

*Reviewer note: this review was produced by executing the software; the commands and outputs above are reproducible with `make repro`, `pytest -q`, and the per-stage SDK calls on a clean clone.*
