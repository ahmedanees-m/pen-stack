# Delivery immunology — the safety↔efficacy balance (v5.1 → v5.5)

PEN-STACK scores and constrains the **whole** delivery palette (8 vehicles), not just dual-AAV. v5.1–v5.5 added
a delivery **safety↔efficacy** layer: a per-vehicle immune / safety / efficacy profile, a user-weightable
ranking, and — crucially — **four of the five immune/safety axes are now grounded in real data or sequence**
rather than hand-typed `low/moderate/high` tiers.

> **The honesty invariant (unchanged across the program).** The in-vivo immune *magnitude* — how strongly a
> given patient or construct will actually react — is a declared **known-unknown**
> (`configs/known_unknowns.yaml: in_vivo_immunogenicity`) and is **never predicted**. Every oracle below
> abstains rather than fabricate when it lacks data, and each carries a scope card stating exactly what it is
> *not* valid for. What is surfaced is a relative, auditable, cited signal — not a per-patient prediction.

## The 8-vehicle palette

`configs/delivery_vehicles.yaml` — AAV (single / dual), lentivirus, helper-dependent adenovirus, HSV amplicon,
LNP-mRNA, eVLP, electroporation. Each carries cargo capacity, integration, cargo form, an `immune_safety` block
(documented ordinal priors + cited DOIs), and the computed-oracle hooks below.

## The safety↔efficacy profile

`pen_stack/planner/delivery_immunology.py::safety_efficacy_profile(vehicle)` returns, per vehicle:

- **two separate safety sub-axes** — never collapsed, because they are different *kinds* of risk:
  - `immune_score` — immunogenicity (largely reversible; bears on eligibility / re-dosing), the mean of four
    immune axes (pre-existing, NAb, innate, adaptive);
  - `genotox_score` — insertional / oncogenic risk (permanent);
- a headline `safety_score = min(immune_score, genotox_score)` (precautionary worst-axis);
- `efficacy_score`, the documented `tradeoff` sentence, and the standing magnitude scope flag.

`recommend_delivery(cargo_form, cargo_bp, safety_weight, in_vivo)` ranks the eligible palette along the
frontier: `balance = safety_weight·safety + (1−safety_weight)·efficacy`. Move `safety_weight` from 0→1 to slide
from efficacy-first to safety-first. This reproduces the motivating tradeoff: **AAV** is dinged on
immunogenicity (non-integrating, but NAb-limited), **lentivirus** on genotoxicity (a highly efficacious
integrator whose insertional risk is the dominant concern).

`verify(design)` surfaces the profile as `delivery_profile` plus a `delivery_immune_profile` scope flag, and —
when a `cargo_seq` is supplied — a `cargo_innate_sensing` flag (see below).

## v5.6 — completion & calibration: anti-PEG, proxy honesty, and the unified profile

v5.6 finishes the picture and tells the truth about it (`docs` + `pen_stack/planner/{antipeg_oracle,immune_profile}.py`,
`pen_stack/validate/immune_calibration.py`):

- **Anti-PEG axis (WS-PEG)** — `antipeg_oracle.py` + `configs/antipeg.yaml`. Pre-existing/induced anti-PEG
  antibodies gate **re-dosing** of PEGylated LNP. Same honest serosurvey pattern as v5.5: a population
  prevalence **range** (25–72 %, Chen 2016 / Yang & Lai 2015 / Armstrong 2007 / Kozma 2020) →
  `preexisting_antipeg_score = 1 − midpoint/100 = 0.515`, range surfaced as uncertainty. **Abstains** for
  non-PEGylated vehicles. Patient titer and post-dose-1 *induced* anti-PEG stay known-unknowns.
- **Proxy calibration (WS-CALIB)** — `immune_calibration.py`. `calibrate_axis()` computes a Spearman ρ +
  bootstrap CI and labels an axis **outcome-validated only when the CI excludes zero** (else `weak_proxy`;
  `mechanistic_proxy` when N < 6). Because no sufficient public *paired* (proxy, observed-immunogenicity)
  dataset exists, **every axis is currently labelled a mechanistic/population proxy** — that honest label is
  the deliverable, and it travels with the profile. (The machinery is proven on synthetic data; it will
  promote an axis only from real data.)
- **Unified immune-risk profile (WS-PROFILE)** — `immune_profile.py`, exposed as **`Verdict.immune_profile`**.
  A per-design **vector** of all axes, each with its own value + uncertainty + scope + validation label;
  **`collapsed_score is None`** (never fused into one overconfident number — asserted by test);
  `known_unknowns` listed; abstaining axes report `None`, not a guess.
- **WS-EXT** — a documented qualitative **route/immune-privilege modifier** (eye/CNS materially lower realized
  immunogenicity vs systemic; Streilein 2003 `10.1038/nri1224`; *no* fabricated magnitude), and three
  mechanistically-distinct axes registered as **known-unknowns**: CD4/MHC-II helper epitopes,
  pre-existing capsid-specific T-cell immunity, and complement/CARPA.

## The axes — four computed/grounded, anti-PEG added, one documented

| Axis | Risk kind | v5.1 | Now | Grounding |
|---|---|---|---|---|
| **Genotoxicity** | permanent / oncogenic | tier | **computed** (v5.2) | integration-site catalogues × oncogene loci |
| **Adaptive (CD8 T-cell)** | reversible | tier | **computed** (v5.3) | MHC-I epitope load over the capsid sequence |
| **Innate** | reversible | tier | **computed** (v5.4) | CpG / dsRNA motif load of the cargo sequence |
| **Pre-existing / NAb (B-cell)** | reversible (eligibility) | tier | **data-grounded** (v5.5) | published serosurveys |
| **Anti-PEG (LNP re-dosing)** | reversible (re-dosing) | — | **data-grounded** (v5.6) | anti-PEG serosurveys |
| **Efficacy** | — | tier | documented | construct/context-specific by nature |

Each computed signal answers through the v4.0 `OracleResult` contract (value + provenance + native uncertainty
+ scope card + `output_kind="baseline"`), and the small committed artifacts (where any) keep the heavy
data/models on the VM so the package and CI stay light.

### Genotoxicity — `genotoxicity_oracle.py` (v5.2, WS-GENOTOX)

For an **integrating** vector, the observed enrichment of its integration sites near COSMIC Cancer-Gene-Census
oncogenes: `P(site within 50 kb of an oncogene)` over the vector class's VISDB catalogue, vs genome background
(2.21 %). `genotox_score = min(1, 1/enrichment)`.

- **Lentiviral (HIV) 2.08×** enrichment (n = 88,743, robust) vs **gammaretroviral (MLV) 5.65×** (the LMO2 /
  SCID-X1 comparator; n = 32, flagged small-n) — reproducing the *lentivirus-safer-than-gammaretrovirus*
  ordering **from data**. The computed lentivirus score (0.48) **validates** the v5.1 documented "moderate"
  tier (0.5).
- Non-integrating vehicles → 1.0 by mechanism. *Not valid for:* the in-vivo clonal / leukemogenesis **outcome**
  (a known-unknown). Build: `scripts/p52_build_genotox_oracle.py` → `configs/genotoxicity_oracle.yaml`.
  Provenance: VISDB `10.1093/nar/gkz867`, COSMIC CGC `10.1038/s41568-018-0060-1`.

### Adaptive / CD8 — `capsid_epitope_oracle.py` (v5.3, WS-EPITOPE)

For a **viral** vector, the fraction of its capsid/envelope antigen presentable to CD8 T cells across a
frequent HLA-I panel (MHCflurry 2.0, %rank ≤ 0.5 over 9-mers × 12 alleles): `capsid_immune_score = 1 −
epitope_fraction_strong`.

- AAV2 VP1 is the **least** epitope-dense capsid (0.72), Ad5 hexon among the most (0.82) — the documented
  adaptive ordering reproduced **from sequence**. All 8 vehicles covered (5 viral computed, 3 non-viral 1.0 by
  mechanism).
- The score is *intrinsic* presentability, so it is folded into the adaptive axis **only for in-vivo**
  vehicles; for **ex-vivo lentivirus** (VSV-G is intrinsically epitope-dense but barely seen ex vivo) it is
  reported but muted. *Not valid for:* the patient-HLA-specific response (a known-unknown); antibody immunity
  (this is CD8/MHC-I only). Sequences UniProt-verified (`configs/capsid_sequences.fasta`: AAV2 VP1 P03135, Ad5
  hexon P04133, VSV-G P03522, HSV-1 gD P57083 + gB P06437). Provenance: MHCflurry `10.1016/j.cels.2020.06.010`,
  HLA supertypes `10.1186/1471-2172-9-1`.

### Innate — `innate_sensing.py` (v5.4, WS-INNATE)

For the **cargo sequence** (computed live in `verify()` when a `cargo_seq` is supplied):

- **DNA** → CpG observed/expected (TLR9/cGAS): vertebrate genome ~0.2 is tolerated, non-depleted DNA → 1 is
  stimulatory; `innate_score = max(0, 1 − CpG_O/E)`.
- **mRNA** → U-richness + ViennaRNA dsRNA pairing (TLR7/8 + RIG-I/MDA5/PKR); a **partial** signal (flagged
  `extrapolating`) — the dominant evasion lever, nucleoside modification (m1-pseudouridine), is *not*
  sequence-derivable.
- **RNP** → minimal/transient. *Not valid for:* the realized in-vivo innate response, RNA nucleoside
  modification, DNA methylation state. Provenance: CpG-TLR9 `10.1073/pnas.161293498`, CpG-depleted AAV
  `10.1172/JCI68205`, RNA modification `10.1016/j.immuni.2005.06.008`.

### Pre-existing / neutralizing antibody — `seroprevalence_oracle.py` (v5.5, WS-SEROPREV)

The one axis that **cannot** be computed from sequence — anti-capsid NAb seroprevalence is a population
prevalence from natural exposure. Grounded in published serosurveys (`configs/seroprevalence.yaml`, ranges with
DOIs): `preexisting_score = 1 − midpoint(seroprevalence)/100`, range half-width surfaced as native uncertainty.

| Serotype (vehicle) | NAb seroprevalence | pre-existing score |
|---|---|---|
| Ad5 → HDAd | 40–90 % | 0.35 |
| HSV-1 → HSV | 50–70 % | 0.40 |
| AAV (aggregate) → AAV | 30–60 % | 0.55 |
| VSV → lentivirus | 0–5 % | 0.975 (muted, ex-vivo) |

Folded for in-vivo vehicles (serum NAb neutralises the vector in vivo), muted for ex-vivo; non-viral → 1.0 by
mechanism. *Not valid for:* a given **patient's** NAb titer / sero-status (a clinical test, patient-specific →
a known-unknown). Provenance: Calcedo `10.1086/595830`, Boutin `10.1089/hum.2009.182`, Mast
`10.1016/j.vaccine.2009.10.145`, Looker `10.1371/journal.pone.0140765`.

## Outcome

Across v5.1→v5.5 the delivery immune/safety profile moved from documented `low/moderate/high` tiers to **real
calculations from data and sequence** on four of the five axes, spanning all 8 vehicles — each grounded, each
abstaining rather than fabricating, with the in-vivo magnitude always a declared known-unknown. The result is
the safety↔efficacy balance the program set out to provide: *computed wherever the science allows, documented
where it does not, and explicitly out-of-scope where no one can yet predict.*

See also: [Oracle mesh](oracles.md) · [Delivery palette & router](delivery.md) · [Verification](verify.md) ·
[Scope & known-unknowns](scope.md). Pre-registrations: `prereg/ws_{immune,genotox,epitope,innate,seroprev}.yaml`.
