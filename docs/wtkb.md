# Writer-Targeting Knowledge Base (WT-KB)

_Generated from `configs/wtkb_curated.yaml` — 8 writer families. Every row is schema-validated and carries >=1 DOI (sourcing rule)._

| Family | Representative | Mechanism | Modality | Target site | Tier | Confidence | DOIs |
|---|---|---|---|---|---|---|---|
| bridge_IS110 | ISCro4 | DSB_FREE_TRANSEST_RECOMBINASE | RNA-guided | bipartite ~14 nt target with central CT dinucleotide core; target and donor loops reprogrammable independently | Tier1_scannable | measured | 10.1126/science.adz0276; 10.1126/science.adz1884; 10.1038/s41586-024-07552-4 |
| seek_IS1111 | IS1111-family seekRNA recombinase | DSB_FREE_TRANSEST_RECOMBINASE | RNA-guided | bipartite RNA-specified target/donor (seekRNA); IS1111 subfamily of the IS110 superfamily; bridge-RNA mechanism general across the family | Tier1_scannable | inferred | 10.1038/s41586-024-07552-4 |
| CAST_VK | ShCAST (Scytonema hofmanni, Cas12k) | DSB_FREE_TRANSEST_RECOMBINASE | RNA-guided | Cas12k sgRNA protospacer + PAM; insertion ~60-66 bp DOWNSTREAM of the protospacer (fixed distance) | Tier2_context_candidate | measured | 10.1126/science.aax9181; 10.1038/s41586-022-05059-4 |
| serine_integrase | Bxb1 | DSB_FREE_TRANSEST_RECOMBINASE | fixed-att | attB x attP recombination; native genomic pseudo-att sites match the integrase specificity profile; installed attB/P sites are deterministic | Tier2_context_candidate | measured | 10.1128/microbiolspec.MDNA3-0046-2014 |
| PE_integrase | PASTE (Cas9-nickase + RT + serine integrase) | DSB_FREE_TRANSEST_RECOMBINASE | PE-installable | pegRNA installs an attB landing site at the nicked locus, then the serine integrase inserts the attP-cargo; insertions demonstrated up to ~36 kb | Tier1_scannable | measured | 10.1038/s41587-022-01527-4 |
| Cas9 | SpCas9 | DSB_NUCLEASE | RNA-guided | 20 nt protospacer + NGG PAM; blunt DSB ~3 bp upstream of PAM (for completeness; a cutter, not a DSB-free writer) | Tier1_scannable | measured | 10.1126/science.1225829; 10.1016/j.cell.2014.02.001 |
| Cas12a | AsCas12a | DSB_NUCLEASE | RNA-guided | 23 nt protospacer + 5' TTTV PAM; staggered DSB distal to PAM (for completeness) | Tier1_scannable | measured | 10.1016/j.cell.2015.09.038 |
| TnpB_Fanzor | ISDra2 TnpB / Fanzor | DSB_NUCLEASE | RNA-guided | omega/reRNA-guided; short TAM (transposon-associated motif); compact ancestral Cas12 relative | Tier3_not_predictable | inferred | 10.1126/science.abj6856 |

## Reachability constraints (per family)

- **bridge_IS110** (Tier1_scannable): scan hg38 for bipartite core match around the CT dinucleotide; both loops reprogrammable; sites with <=2 mismatches are off-target risk (Perry 2025)
- **seek_IS1111** (Tier1_scannable): scan hg38 for the seekRNA-specified bipartite target; mechanism computationally identified across diverse IS110/IS1111 members (Durrant 2024)
- **CAST_VK** (Tier2_context_candidate): protospacer + PAM + fixed +60-66 bp insertion distance + recruitment context; candidate site — requires experimental validation
- **serine_integrase** (Tier2_context_candidate): scan for native pseudo-att against the Bxb1 specificity profile (candidate); an INSTALLED att collapses to Tier 1 (deterministic) via PE/landing pad
- **PE_integrase** (Tier1_scannable): Tier-1 via PE-installability check (can a pegRNA be efficiently designed at the locus?), bounded by prime-editing context; after install the att step is deterministic
- **Cas9** (Tier1_scannable): scan for 20 nt protospacer + NGG PAM; insertion requires a DSB + HDR template (not DSB-free); included for completeness/comparison
- **Cas12a** (Tier1_scannable): scan for 5' TTTV PAM + 23 nt protospacer; DSB-dependent insertion; completeness/comparison entry
- **TnpB_Fanzor** (Tier3_not_predictable): TAM + omegaRNA target; insertion preferences not yet genome-scale predictable — flagged not-yet-predictable
