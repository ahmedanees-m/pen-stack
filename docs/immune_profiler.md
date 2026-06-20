# The immune profiler (v6.9 PEN-IMMUNE)

The immune profiler profiles a design's immunogenicity/toxicity across **separate, never-collapsed axes**. Through v6.8 the
adaptive axis was **CD8/MHC-I only** (capsid epitope load via MHCflurry). v6.9 adds the **dominant** driver,
**MHC-II/CD4 to ADA**, and scores the **writer enzyme as a distinct antigen**.

## The MHC-II/CD4 axis (`planner/immune_mhc2.py`)

> **v6.9.1 real predictor.** The MHC-II epitope load is computed with the **licensed NetMHCIIpan-4.0** (EL
> %Rank≤2 over a frequent HLA-II panel; MHC-I via **NetMHCpan-4.1**), run inside `penmhc:tools` Docker on the VM
> with the licensed tools **mounted** (never committed). Only the **derived fractions** are cached
> (`configs/mhc_epitope_oracle.yaml`), exactly like the v5.3 MHCflurry cache. Computed with the v6.9.2 residue-coverage
> metric (residues covered by ≥1 strong binder, union over the panel; matches the v5.3 MHCflurry convention): the
> gold-standard tool discriminates self from foreign (human-self albumin **0.319** vs foreign writers **0.56-0.65**;
> the v6.9.0 heuristic proxy gave ~0.08-0.10 for all). Still a population-level proxy (frequent-HLA panel, not a
> patient-HLA magnitude).
>
> **v6.9.2 no production proxy.** For a sequence **not** in the real cache the axis now **abstains** (out of
> scope) rather than emitting a proxy number; the documented promiscuous-binder density below is retained
> only as `mhc2_proxy_estimate` for **offline triage** (explicitly labelled, never the production axis). The **capsid
> MHC-I axis** is likewise re-grounded on **NetMHCpan-4.1** as the primary, with MHCflurry kept as a reported cross-check.

A grounded, dependency-free **promiscuous MHC-II binder density** (`mhc2_proxy_estimate`, offline triage only): MHC-II presents a 9-mer core in an open groove
whose **P1 pocket is deep and hydrophobic**, the single dominant anchor (M/F/Y/W/L/I/V; Stern & Wiley, *Nature*
1994), with secondary pockets at P4/P6/P9. A *promiscuous* epitope (binds many HLA-DR) has a strong P1 anchor plus
favorable secondaries (Southwood 1998). We count promiscuous-binder cores to obtain an epitope-density proxy, computed over
**capsid AND writer** sequences. It is a **population-level, sequence-intrinsic proxy**: not a trained
allele-specific predictor, not a patient-HLA magnitude (out of scope).

## The ADA-risk axis + self-tolerance (`planner/ada_risk.py`)

Epitope load is necessary but not sufficient: **self** proteins carry MHC-II epitopes yet are tolerated. So:

```
ADA-risk = MHC-II epitope density × foreignness
```

where `foreignness` is the **authoritative protein origin** (self vs bacterial/viral/phage), the definitive
central-tolerance signal. **v6.9.2:** the MHC-II density is the real NetMHCIIpan-4.0 value (by antigen name), and an
**unknown origin abstains** (no k-mer guess, no heuristic). The **real full-human-proteome 9-mer self-match**
(computed on the VM over the full UniProt reference proteome, 20 431 proteins / 10.4 M 9-mers) is reported as a
**cross-check**, not as a foreignness imputation. This **recovers immunogenic-vs-tolerated**:

| Protein (real UniProt) | origin | MHC-II density (NetMHCIIpan-4.0) | ADA-risk | human-proteome self-match |
|---|---|---|---|---|
| SpCas9 (Q99ZW2) | foreign | 0.636 | **0.636** | 0.0 (non-self) |
| Bxb1 integrase (Q9B086) | foreign | 0.647 | **0.647** | 0.0 (non-self) |
| ISCro4 bridge recombinase (D2TGM5) | foreign | 0.564 | **0.564** | 0.0 (non-self) |
| Human albumin (P02768) | self | 0.319 | **0.0** (tolerated, × origin) | **1.0** (self) |

ADA-risk = density × foreignness, so the self control is zeroed by its `self` origin while the foreign writers carry
their full MHC-II load. The independent human-proteome self-match agrees: albumin is fully self (1.0), the bacterial
writers are non-self (0.0).

## The writer as a distinct antigen

`immune_profile` now carries a `writer_as_antigen` card and a `writer_dominant_risk` flag. The insight the
capsid-only profile missed: **for non-viral delivery (LNP/mRNA, eVLP) of a bacterial writer there is no capsid
antigen, so the WRITER is the dominant immunogen.** The flag fires accordingly; the axes are reported as a vector
with `collapsed_score: None` (never fused).

## Limitations
- Population-level proxies, never a patient-specific ADA titer / realized CD4 magnitude (out of scope).
- The MHC-II method is presentation potential, not a trained allele-specific predictor.
- The self-tolerance k-mer filter is seeded by the bundled human reference; the **full human proteome** is
  substitutable on the VM (the authoritative foreignness signal is the protein origin).
- The ADA axis's `calibrate_axis` pass **stays a proxy**: no public observed-incidence set at N≥6 power (the standing
  wet-lab/clinical-data bottleneck), reported, never manufactured.

See `benchmarks/immuno/` (Immuno-Bench) and `prereg/ws_immune2.yaml`.
