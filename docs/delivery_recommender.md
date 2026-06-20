# The deliverability engine (v6.11 PEN-DELIVER)

This component upgrades delivery from an 8-vehicle **rule palette** to a cross-modality recommender with a **learned,
benchmarked AAV capsid-fitness model**, a **grounded serotype→tissue tropism prior** from approved therapies, and an
**immune-coupled dose tradeoff**, without ever fabricating tropism.

## Learned capsid-fitness (`planner/delivery_predict.capsid_fitness`)

A model trained on the **FLIP-AAV** benchmark (Dallago et al. 2021; built on **Bryant et al. 2021** packaging
fitness, `10.1038/s41587-020-00793-4`; **Ogden et al. 2019** is the foundational landscape, `10.1126/science.aaw2900`).
A windowed one-hot gradient-boosting model over the mutagenized VP1 561-588 region. It beats a
mutation-burden baseline on held-out FLIP-AAV on **both** splits (`benchmarks/delivery/`):

| Split | learned Spearman | baseline | gap 95% CI |
|---|---|---|---|
| `sampled` (random 80/20, in-distribution) | **0.920** | 0.522 | [0.387, 0.411] |
| `mut_des` (mutant→designed, hard generalization) | **0.814** | 0.752 | [0.061, 0.064] |

The licensed FLIP-AAV data (217 MB/split) stays on the VM; the **derived metrics + reproducible build script**
(`scripts/build_capsid_fitness.py`) are committed. The trained model (`models/capsid_fitness.pkl`, ~3 MB) is
**gitignored**, regenerated from the build script and **mounted into the deployed app** (the `position_effect.pkl`
pattern), so CI stays lean and the axis **abstains gracefully** when the model is absent. **Scope:** predicted
fitness is a **candidate** for the *measured* packaging axis; it is **not** an in-vivo human-tropism claim (out of
scope).

## Serotype → tissue tropism priors (`configs/aav_serotype_tropism.yaml`)

Real serotype↔tissue mappings evidenced by **approved AAV gene therapies** (independently verified): AAV9→CNS
(Zolgensma), **AAVrh74→skeletal muscle** (Elevidys), AAV5→liver (Hemgenix/Roctavian), **AAVRh74var→liver** (Beqvez,
a *different* capsid from AAVrh74), AAV2→retina/putamen via **local injection** (Luxturna/Upstaza). A grounded prior
for an approved serotype; an **abstain** for a novel/engineered capsid, never a fabricated tissue.
Ex-vivo cell therapies (Casgevy = non-viral CRISPR; Lyfgenia = lentiviral) carry **no** serotype prior.

## Immune-coupled tradeoff (`planner/delivery_immune.delivery_immune_tradeoff`)

Fuses deliverability with the per-axis immune profile and surfaces the **dose↔immunogenicity tradeoff**
per vehicle as a vector; `collapsed_score` is always `None`. The realized in-vivo magnitude / patient titer are
out of scope; this is decision-support, not a clinical dosing directive.

## Generative candidates (`design/capsid_generate.generate_capsid_candidates`)

Verifier-as-discriminator (v5.8): propose VP1-region variants, score with the learned capsid-fitness, keep survivors
above the WT fitness. Every survivor is a **candidate**: packaging fitness only; assembly, in-vivo tropism, and
immunogenicity are not claimed. Abstains when the model is absent (no fabricated capsids).

## Surfaces
REST `POST /delivery` + `POST /capsid_fitness` + `GET /delivery/tropism`, MCP `delivery_recommend`, manifest
`recommend_delivery` + `capsid_fitness`, the `capsid_fitness` scope card, and a `delivery` task in the
Genome-Writing Challenge (serotype→tissue, label = approved-therapy registry).

## Limitations
Predicted capsid-fitness is strongest for the **measured** packaging axis and extrapolative for in-vivo human tissue
(out of scope). VLP/LNP coverage is thinner than AAV (alpha-retro-VLP is exploratory; its strongest in-vivo evidence
is a conference abstract). Manufacturing/CMC is out of scope.
