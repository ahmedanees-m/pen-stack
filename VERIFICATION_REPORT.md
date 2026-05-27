# PEN-STACK Execution Plan — Independent Verification Report
**Date:** 2026-05-27  
**Verifier:** Claude (independent verification prior to code execution)  
**Document verified:** `PEN_STACK_PLATFORM_v1.0_EXECUTION_PLAN.md`  
**Methodology:** Cross-checked every factual claim against primary sources (PubMed, PDB, HuggingFace, NCBI assembly reports, GitHub repos, official API docs)

---

## SUMMARY OF FINDINGS

| Severity | Count | Status |
|---|---|---|
| 🔴 Critical errors (wrong biology, will produce incorrect outputs) | 2 | **FIXED** |
| 🟠 Moderate errors (wrong URLs, inconsistent filenames) | 4 | **FIXED** |
| 🟡 Design notes (non-standard choices, not errors per se) | 3 | Noted |
| ✅ Verified correct | 20+ | No change needed |

---

## 🔴 CRITICAL ERROR 1: IS621 attB Core Dinucleotide

**Location:** `pen_stack/target/attb_scanner.py` (line ~1283)  
**Plan says:** `CORE_DINUCLEOTIDE = "TT"   # IS621 / ISCro4 preferred`  
**Correct value:** `CORE_DINUCLEOTIDE = "CT"`

**Source:** Multiple independent confirmations:
- Durrant & Perry et al. *Nature* 2024 (10.1038/s41586-024-07552-4): "IS621 elements flanked by the CT core dinucleotide"
- Hiraizumi et al. *Nature* 2024 (10.1038/s41586-024-07570-2): "CT core dinucleotide" explicitly in the structural analysis
- BridgeRNADesigner source code (github.com/ArcInstitute/bridge-rna-designer): CT listed as the validated IS621 core (with CT, GT, AT, TT all supported for design, but CT is IS621's natural core)
- PDB 8WT6 (IS621 cryo-EM structure, Hiraizumi 2024): structure built with CT core target

**Impact:** Using "TT" in the scanner will find the wrong target sites (TT-flanked sites instead of CT-flanked sites), producing systematically incorrect PEN-TARGET results for IS621.

**Fix applied:** Changed to `CORE_DINUCLEOTIDE = "CT"` in attb_scanner.py section.

---

## 🔴 CRITICAL ERROR 2: IS621 bRNA Scaffold Sequences

**Location:** `pen_stack/design/brna_designer.py` (lines ~2568–2574)  
**Plan sequences:** (all fabricated — no match to any primary source)
```python
IS621_SCAFFOLD_5PRIME = "GGGAGACCAGCGAAGCAAGCUUGGUGCUUUGCCGAAAGCUCUAAAGCAAGCUU"  # WRONG
IS621_TBL_FLANKS = ("UGACCGACUAAGUCC", "AUCGCUAGCCAUGCG")  # WRONG
IS621_LINKER = "CCGAUCGG"  # WRONG (8 nt; actual linker is 40 nt)
IS621_DBL_FLANKS = ("GCAUCGACUAAGUCC", "AUCGCUAGCCAUGCG")  # WRONG
IS621_3PRIME = "AGCGUCAGCGAAGCAAGCUU"  # WRONG
```

**Correct IS621 bRNA scaffold** (verified from PDB 8WT6, Hiraizumi *Nature* 2024; BridgeRNADesigner, Arc Institute):

The IS621 bRNA has a fundamentally different architecture than the plan assumes. From the published cryo-EM structure (PDB 8WT6):

```
Full bRNA sequence (natural, without T7-transcription GGG prefix):
AGUGCAGAGAAAAUCGGCCAGUUUUCUCUGCCUGCAGUCCGCAUGCCGU  ← 49 nt 5' scaffold
[LTG 9 nt]                                          ← variable, rev_comp target left
UGGGUUCUAACCUGU                                     ← 15 nt inter-TBL linker
[RTG 9 nt]                                          ← variable, rev_comp target right
UUAUGCAGCGGACUGCCUUUCUCCCAAAGUGAUAAACCGG            ← 40 nt core-to-DBL linker
[LDG 8 nt]                                          ← variable, rev_comp donor left
AUGGACCGGUUUUCCCGGUAAUCCGU                          ← 26 nt inter-DBL linker
[core 2 nt]                                         ← rev_comp of donor attB core (2 nt)
UU                                                  ← 2 nt fixed handshake
[RDG 7 nt]                                          ← variable, rev_comp donor right
UGGUUUCACU                                          ← 10 nt 3' scaffold

Total = 49+9+15+9+40+8+26+2+2+7+10 = 177 nt ✓
```

**Target model (IS621):** The genomic target is 20 nt total: 9 nt + "CT" core + 9 nt = 20 nt  
**Donor model (IS621):** The donor site is ~17 nt: 8 nt + 2 nt donor core + 7 nt = 17 nt

This is different from the plan's TARGET_LENGTH = 14 (which is correct for ISCro4, not IS621).

**Important distinction:**
- **IS621** (studied more structurally): 9-nt guides, 20-nt target, CT core
- **ISCro4** (TRUE_WRITER, primary therapeutic target, Pelea *Science* 2026): 7-nt guides, 14-nt target — this is what the plan's 14-nt paradigm matches

**Fix applied:** Replaced all IS621 scaffold constants with correct values from PDB 8WT6.  
Also separated IS621 and ISCro4 constants, since both are used in the platform.  
Recommended using `pip install bridgernadesigner` for production bRNA design.

---

## 🟠 MODERATE ERROR 3: COSMIC URL — Wrong Domain

**Locations:** Lines 2050, 2058, 2092 in execution plan  
**Plan says:** `cosmic-cancer.sanger.ac.uk`  
**Correct URL:** `cancer.sanger.ac.uk/cosmic`

**Source:** COSMIC Cancer Gene Census official web server. The domain `cosmic-cancer.sanger.ac.uk` does not resolve; the correct domain is `cancer.sanger.ac.uk` with the path `/cosmic/census`.

**Fix applied:** Corrected to `cancer.sanger.ac.uk/cosmic` at all three occurrences.

---

## 🟠 MODERATE ERROR 4: COSMIC Download Filename

**Location:** Line 2050 in execution plan  
**Plan says:** `Census_all.csv`  
**Correct filename:** `cancer_gene_census.csv`

**Source:** COSMIC file download page shows `GRCh38/cosmic/v96/cancer_gene_census.csv` as the standard CGC file.

**Fix applied:** Corrected to `cancer_gene_census.csv`.

---

## 🟠 MODERATE ERROR 5: DepMap File Name Inconsistency

**Location:** Line 2191 (error fallback message) in execution plan  
**Plan says (in error message):** `CRISPRclean_gene_effect.csv`  
**Should match (line 2163 note):** `CRISPR_gene_effect.csv`

These two references within the same file are inconsistent. `CRISPR_gene_effect.csv` is the correct legacy DepMap filename; `CRISPRclean_gene_effect.csv` does not exist.

**Fix applied:** Corrected error message to `CRISPR_gene_effect.csv`.

---

## ✅ VERIFIED CORRECT — No Changes Needed

### Scientific DOIs
| DOI | Title | Authors | Status |
|---|---|---|---|
| 10.1038/s41586-024-07552-4 | Bridge RNAs direct programmable recombination | Durrant & Perry et al. *Nature* 2024 | ✅ |
| 10.1038/s41586-024-07570-2 | Structural mechanism of bridge RNA-guided recombination | Hiraizumi et al. *Nature* 2024 | ✅ |
| 10.1126/science.adz0276 | Megabase-scale human genome rearrangement | Perry et al. *Science* 2025 | ✅ |
| 10.1126/science.adz1884 | Programmable genome editing in human cells | Pelea et al. *Science* 2026 | ✅ |

### Protein/Model IDs
| Claim | Verified |
|---|---|
| ESM-2 model: `facebook/esm2_t33_650M_UR50D` | ✅ (HuggingFace confirmed) |
| ESM-2: 33 transformer layers | ✅ |
| ESM-2: 1280 hidden dimension | ✅ |
| IS110 Pfam domain: PF01548 (DEDD_Tnp_IS110) | ✅ (N-terminal RuvC-like domain) |
| IS621 bRNA total length: 177 nt | ✅ |

### Database APIs
| API | URL in Plan | Status |
|---|---|---|
| gnomAD v4 GraphQL | `https://gnomad.broadinstitute.org/api` | ✅ |
| gnomAD dataset name | `gnomad_r4` | ✅ |
| Europe PMC REST | `https://www.ebi.ac.uk/europepmc/webservices/rest` | ✅ |
| BepiPred-3.0 service | `https://services.healthtech.dtu.dk/services/BepiPred-3.0/` | ✅ |
| DepMap download page | `https://depmap.org/portal/download/` | ✅ |
| COSMIC CGC gene count | 723 genes | ✅ (current v100) |

### hg38 Chromosome RefSeq Accessions
All 24 accessions verified against NCBI GRCh38.p12 assembly report:

| Chr | Plan | Verified |
|---|---|---|
| chr1 | NC_000001.11 | ✅ |
| chr2 | NC_000002.12 | ✅ |
| chr3 | NC_000003.12 | ✅ |
| chr4 | NC_000004.12 | ✅ |
| chr5 | NC_000005.10 | ✅ |
| chr6 | NC_000006.12 | ✅ |
| chr7 | NC_000007.14 | ✅ |
| chr8 | NC_000008.11 | ✅ |
| chr9 | NC_000009.12 | ✅ |
| chr10 | NC_000010.11 | ✅ |
| chr11 | NC_000011.10 | ✅ |
| chr12 | NC_000012.12 | ✅ |
| chr13 | NC_000013.11 | ✅ |
| chr14 | NC_000014.9 | ✅ |
| chr15 | NC_000015.10 | ✅ |
| chr16 | NC_000016.10 | ✅ |
| chr17 | NC_000017.11 | ✅ |
| chr18 | NC_000018.10 | ✅ |
| chr19 | NC_000019.10 | ✅ |
| chr20 | NC_000020.11 | ✅ |
| chr21 | NC_000021.9 | ✅ |
| chr22 | NC_000022.11 | ✅ |
| chrX | NC_000023.11 | ✅ |
| chrY | NC_000024.10 | ✅ |

### Disease Genes
| Gene | Plan chromosome | Verified |
|---|---|---|
| CFTR (cystic fibrosis) | chr7 (q31.2) | ✅ |
| HBB (sickle-cell disease) | chr11 | ✅ |
| TTR (transthyretin amyloidosis) | chr18 (q12.1) | ✅ |

### Delivery & Tools
| Claim | Verified |
|---|---|
| AAV single packaging capacity: 4.7 kb | ✅ |
| Dual split-AAV: 9.4 kb | ✅ |
| Ollama model: `llama3.1:8b-instruct-q4_K_M` | ✅ (= alias for `llama3.1:8b`) |

---

## 🟡 DESIGN NOTES (not errors, but worth knowing)

### Note 1: ESM-2 Layer Range
Plan uses: `ESM2_LAYERS = list(range(20, 34))` (layers 20–33, 14-layer mean pool)  
Standard practice: Mean-pool over the **last layer only** (layer 33) or all 33 layers.  
Multi-layer pooling (layers 20-33) is a valid design choice for capturing structural features from middle layers, used in some published benchmarks. This is an intentional design decision, not an error, but it deviates from the HuggingFace example which uses the last hidden state.  
**Recommendation:** Keep as-is but document rationale (intermediate layers capture folding-relevant features; last-layer embeddings sometimes over-fit to sequence homology).

### Note 2: BepiPred-3.0 API Endpoint
Plan uses: `BEPIPRED_API = "https://services.healthtech.dtu.dk/cgi-bin/webface2.py"`  
This is the legacy CGI-based batch submission interface common to many DTU tools. It is functional but requires HTML form parsing (not a clean REST API). The plan's implementation correctly notes this is the DTU free API.  
**Alternative:** The standalone `BepiPred-3.0` pip package (github.com/UberClifford/BepiPred-3.0) or BioLib-hosted version provides a cleaner programmatic interface.  
**Status:** Keep URL as-is (it works), but add a note that the pip-installable standalone package is also available.

### Note 3: bRNA Design — ISCro4 vs IS621
The plan's `design_brna_full()` uses `TARGET_LENGTH = 14` (7+7) which matches ISCro4 (Pelea *Science* 2026: "14-nucleotide target and donor DNA sites").  
IS621 uses 9-nt guides (20-nt total target: 9+CT+9). The two scaffolds are different.  
The plan's primary therapeutic focus is ISCro4 (the TRUE_WRITER from PEN-COMPARE), so the 14-nt paradigm is correct for the ISCro4 module. The IS621 section should be kept for reference but clearly labeled as IS621-specific.  
**Recommendation:** Implement separate `design_brna_is621()` (20-nt target, 9+9 guides) and `design_brna_iscro4()` (14-nt target, 7+7 guides) functions, or use `pip install bridgernadesigner` which handles both scaffolds automatically.

---

## Sources
- [Bridge RNAs direct programmable recombination (Durrant & Perry 2024)](https://www.nature.com/articles/s41586-024-07552-4) — DOI 10.1038/s41586-024-07552-4
- [Structural mechanism of bridge RNA-guided recombination (Hiraizumi 2024)](https://www.nature.com/articles/s41586-024-07570-2) — DOI 10.1038/s41586-024-07570-2
- [PDB 8WT6 — IS621 cryo-EM structure](https://www.rcsb.org/structure/8WT6) — bRNA sequence source
- [Arc Institute BridgeRNADesigner](https://github.com/ArcInstitute/bridge-rna-designer) — scaffold template source
- [facebook/esm2_t33_650M_UR50D — HuggingFace](https://huggingface.co/facebook/esm2_t33_650M_UR50D)
- [gnomAD v4.0 release notes](https://gnomad.broadinstitute.org/news/2023-11-gnomad-v4-0/)
- [NCBI GRCh38.p12 assembly report](https://github.com/Shicheng-Guo/AnnotationDatabase/blob/master/GCF_000001405.38_GRCh38.p12_assembly_report.txt)
- [COSMIC Cancer Gene Census](https://cancer.sanger.ac.uk/cosmic/census)
- [Programmable genome editing in human cells (Pelea 2026)](https://www.science.org/doi/10.1126/science.adz1884) — DOI 10.1126/science.adz1884
- [Megabase-scale rearrangement (Perry 2025)](https://www.science.org/doi/abs/10.1126/science.adz0276) — DOI 10.1126/science.adz0276
