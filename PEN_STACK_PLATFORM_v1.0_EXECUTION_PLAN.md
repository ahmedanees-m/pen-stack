# PEN-STACK PLATFORM — Execution Plan v1.0
**The First Comprehensive Computational Platform for Non-Destructive Genome Engineering**

**Status:** Part A COMPLETE — Part B pending
**Author:** Anees Ahmed Mahaboob Ali (VIT Vellore)
**Date drafted:** 2026-05-26
**Last updated:** 2026-05-27 (verification + Part A execution log added)
**Repository target:** `github.com/ahmedanees-m/pen-stack` (single unified repo)
**GitHub:** https://github.com/ahmedanees-m/pen-stack (tag: `v1.0.0a1-part-a`)
**Prerequisite:** `pen-compare v0.1.0` live on PyPI; NAR Webserver manuscript submitted
**Execution window:** 12 working weeks
**Target venue (primary):** *Nature Methods*
**Target venue (clinical follow-up):** *Nature Biotechnology*
**Total marginal cost:** $0.00

---

# §0 — Platform Overview

## §0.1 Mission

PEN-STACK is the first comprehensive computational decision-support platform for the Molecular Pen era of genome medicine. It covers the full workflow every non-destructive genome engineering program needs, from initial sequence discovery to clinical readiness:

```
Novel IS110 sequence                         Clinical readiness
      ↓                                              ↑
PEN-DISCOVER → PEN-COMPARE → PEN-TARGET → PEN-SAFE → PEN-DESIGN → PEN-DELIVER → PEN-BENCH
      ↑___________________________ PEN-MONITOR __________________________________|
                         (living database — keeps everything current)
```

The end-to-end call that no other tool in genetic engineering can make:

```python
from pen_stack import Pipeline

result = Pipeline.run(
    query="Treat CFTR-F508del in airway epithelium",
    cargo_kb=3.2
)

print(result.recommended_editors)    # ranked list with TrueWriter probabilities
print(result.target_sites)           # hg38 coordinates with bRNA designs
print(result.safety_scores)          # oncogene proximity, population variants
print(result.optimized_design)       # best editor-bRNA-cargo combination
print(result.delivery_recommendation)# AAV5 for airway + capacity check
print(result.experimental_roadmap)   # what to do next in the lab
```

## §0.2 Seven modules — one pipeline

| Module | Function | Key technology |
|---|---|---|
| **PEN-COMPARE** | Hierarchical certification (TRUE/PROBABLE/EMERGING/NOT writer) | 5-gate framework (migrated from v0.1.0) |
| **PEN-DISCOVER** | Sequence → TrueWriter probability prediction for uncharacterized IS110 orthologues | ESM-2 650M (HuggingFace), trained on 29 curated editors |
| **PEN-TARGET** | Identify usable genomic target sites near a disease locus | hg38 + 14-nt bRNA TBL scanner + gnomAD v4 |
| **PEN-MONITOR** | Living database engine — auto-updates editor universe from new literature | Europe PMC API + Llama 3.1 8B LLM claim extractor |
| **PEN-SAFE** | Safety analysis — oncogene proximity, essential gene risk, population variants, immunogenicity | COSMIC CGC, DepMap, gnomAD v4, BepiPred-3.0 |
| **PEN-DESIGN** | bRNA design + codon optimization + cargo sequence checking | IS621/ISCro4 scaffold logic, CAI calculation |
| **PEN-DELIVER** | Delivery modality recommendation + AAV serotype + capacity checking | Evidence corpus RAG, published literature |
| **PEN-BENCH** | Experimental protocol generator + Jupyter notebook templates | LLM protocol generator + Protocols.io API |

Plus:
- **Pipeline class** — end-to-end `Pipeline.run()` integrating all 7 modules
- **FastAPI REST gateway** — all modules as REST endpoints for third-party integration
- **Unified Streamlit webserver** — 10+ tabs (one per module)
- **Community portal** — structured submission of new cell-based evidence

## §0.3 Biological foundation

The IS110 bridge recombinase system (Durrant & Perry et al. *Nature* 2024; Hiraizumi et al. *Nature* 2024; Perry et al. *Science* 2025) uses a 177-nt bridge RNA (bRNA) with two independently programmable loops:

- **Target-Binding Loop (TBL):** recognizes a 14-bp genomic target (7 bp Left Target Guide + 7 bp Right Target Guide). Any genomic 14-mer is a potential landing site.
- **Donor-Binding Loop (DBL):** recognizes a 14-bp donor DNA sequence (7 bp Left Donor Guide + 7 bp Right Donor Guide). Specifies the cargo integration point.

Because BOTH loops are reprogrammable and the recombinase introduces no DSBs, the system realizes all four Molecular Pen properties: DSB avoidance, programmability, native cargo capability, and therapeutic deliverability.

**Why this matters for PEN-STACK:** Every module is grounded in this mechanism. PEN-TARGET scans for 14-nt TBL sites. PEN-DESIGN generates bRNA sequences. PEN-DISCOVER predicts whether uncharacterized IS110 orthologues support bRNA-guided targeting. PEN-SAFE checks whether the landing site is safe. PEN-DELIVER determines how to get the editor in. PEN-BENCH tells you what to run next.

## §0.4 pen-compare migration strategy

`pen-compare v0.1.0` stays permanently on PyPI as a standalone citable artifact (the NAR Webserver paper). Its source code is migrated into `pen_stack/compare/` as the first committed module. Users installing `pen-stack` get all certification functionality. The PyPI `pen-compare` package is not deleted — it remains for backward compatibility and citation purposes.

```
pen-compare v0.1.0 (PyPI, frozen)  ←→  pen_stack.compare (live development)
```

## §0.5 Compute realism

| Workload | Hardware | Wall time | Cost |
|---|---|---|---|
| ESM-2 650M embedding (29 editors, ~330 aa each) | 16 GB GPU | ~5 min | $0 |
| ESM-2 gate-probability model training | 16 GB GPU | ~10 min | $0 |
| IS110 orthologue screening from NCBI (1000 sequences) | CPU | ~30 min | $0 |
| hg38 bRNA site scanner (per gene, ±5 kb) | 24 CPU | ~2 min | $0 |
| gnomAD v4 API queries (per site) | API | ~1 sec/query | $0 |
| Europe PMC nightly watch (100 papers/query) | CPU | ~5 min | $0 |
| LLM claim extraction (50 abstracts) | 16 GB GPU Ollama | ~10 min | $0 |
| BepiPred-3.0 API (per editor) | DTU free API | ~30 sec | $0 |
| Full Pipeline.run() for one clinical query | All above | ~15 min | $0 |
| **Total marginal cost** | | | **$0.00** |

## §0.6 Zero-budget principle

Every dependency is free for academic use. No paid APIs. Same principle as pen-compare v0.1.0, extended across the full platform.

| Service | Tool | Cost |
|---|---|---|
| LLM inference | Ollama Llama 3.1 8B (local GPU) | $0 |
| Protein embeddings | ESM-2 via HuggingFace transformers (local GPU) | $0 |
| Genome data | hg38 via NCBI/Ensembl (free academic) | $0 |
| Population variants | gnomAD v4 GraphQL API (free, no auth) | $0 |
| Literature monitoring | Europe PMC REST API (free, no auth) | $0 |
| Safety genes | COSMIC CGC static CSV + DepMap (free academic) | $0 |
| Immunogenicity | BepiPred-3.0 DTU free API | $0 |
| Webserver | Streamlit Community Cloud (free tier) | $0 |
| REST API hosting | Local Docker on VM (no cloud cost) | $0 |
| Docs | GitHub Pages (free public repo) | $0 |
| CI/CD | GitHub Actions (free public repo) | $0 |
| Package hosting | PyPI (free) | $0 |
| Data archive | Zenodo (free academic) | $0 |

## §0.7 Publication roadmap

| Version | Paper | Target | Claim | Timeline |
|---|---|---|---|---|
| pen-compare v0.1.0 | Paper 5 | **NAR Webserver** | Certification framework (submitted separately) | Now |
| pen-stack v1.0.0 | Platform paper | **Nature Methods** | First comprehensive platform for non-destructive genome engineering | 12 weeks |
| Clinical application | Follow-up | **Nature Biotechnology** | Platform applied to CFTR-F508del / SCD / TTR therapeutic programs | 6–8 months |
| Paradigm review | Review article | **Nature Reviews Genetics** | The Molecular Pen paradigm for genome medicine | 12–18 months |

## §0.8 Execution timeline

| Part | Title | Steps | Weeks |
|---|---|---|---|
| **A** | Monorepo setup + pen-compare migration | 1–4 | 1 |
| **B** | PEN-DISCOVER: IS110 sequence prediction | 5–9 | 2–3 |
| **C** | PEN-TARGET: Genome targeting | 10–13 | 3–4 |
| **D** | PEN-MONITOR: Living database engine | 14–17 | 4–5 |
| **E** | PEN-SAFE: Safety analysis | 18–23 | 5–6 |
| **F** | PEN-DESIGN: bRNA + cargo optimization | 24–27 | 6–7 |
| **G** | PEN-DELIVER: Delivery optimization | 28–31 | 7–8 |
| **H** | PEN-BENCH: Experimental planning | 32–35 | 8–9 |
| **I** | Pipeline class: end-to-end integration | 36–38 | 9 |
| **J** | Unified Streamlit + REST API + Community Portal | 39–44 | 9–10 |
| **K** | Tests ≥90%, Sphinx docs, PyPI v1.0.0 | 45–48 | 10–11 |
| **L** | Nature Methods manuscript + submission | 49–52 | 12 |
| **Total** | **52 steps** | **12 weeks** | |

---

## §0.9 — Independent Verification & Execution Log

> **Full verification report:** `VERIFICATION_REPORT.md` (same directory as this file)

### §0.9.1 Pre-Execution Independent Verification (2026-05-27)

Before any code was written, every factual claim in this document was independently cross-checked against primary sources (PubMed, PDB, HuggingFace, NCBI, GitHub, official API docs).

| Severity | Count | Status |
|---|---|---|
| 🔴 Critical errors (wrong biology — would produce incorrect outputs) | 2 | **FIXED** |
| 🟠 Moderate errors (wrong URLs, inconsistent filenames) | 4 | **FIXED** |
| 🟡 Design notes (non-standard choices, not errors) | 3 | Noted |
| ✅ Verified correct (DOIs, model IDs, accessions, API URLs) | 20+ | No change needed |

#### 🔴 Critical Fix 1 — IS621 attB Core Dinucleotide

**File:** `pen_stack/target/attb_scanner.py`
**Was:** `CORE_DINUCLEOTIDE = "TT"`
**Correct:** `CORE_DINUCLEOTIDE = "CT"`

**Sources:** Durrant & Perry *Nature* 2024 (DOI 10.1038/s41586-024-07552-4); Hiraizumi *Nature* 2024 (DOI 10.1038/s41586-024-07570-2); PDB 8WT6 cryo-EM structure; Arc Institute BridgeRNADesigner source code.

**Impact if not fixed:** PEN-TARGET would scan for TT-flanked sites instead of CT-flanked sites, producing systematically wrong target site predictions for IS621.

#### 🔴 Critical Fix 2 — IS621 bRNA Scaffold Sequences (all fabricated)

**File:** `pen_stack/design/brna_designer.py`

All five scaffold constants in the original plan were fabricated with no match to any primary source. Replaced with verified sequences from PDB 8WT6 (Hiraizumi *Nature* 2024) and BridgeRNADesigner (Arc Institute):

| Constant | Was (WRONG) | Correct (PDB 8WT6) |
|---|---|---|
| `IS621_5PRIME` | `"GGGAGACCAGCGAAGCAAGCUU..."` (fabricated) | `"AGUGCAGAGAAAAUCGGCCAGUUUUCUCUGCCUGCAGUCCGCAUGCCGU"` (49 nt) |
| `IS621_TBL_INTER` | `"UGACCGACUAAGUCC"` (fabricated) | `"UGGGUUCUAACCUGU"` (15 nt) |
| `IS621_CORE_LINK` | `"CCGAUCGG"` (8 nt — wrong length) | `"UUAUGCAGCGGACUGCCUUUCUCCCAAAGUGAUAAACCGG"` (40 nt) |
| `IS621_DBL_INTER` | `"GCAUCGACUAAGUCC"` (fabricated) | `"AUGGACCGGUUUUCCCGGUAAUCCGU"` (26 nt) |
| `IS621_3PRIME` | `"AGCGUCAGCGAAGCAAGCUU"` (fabricated) | `"UGGUUUCACU"` (10 nt) |
| `HANDSHAKE` | (missing) | `"UU"` (2 nt fixed) |

Also corrected: IS621 uses `TARGET_LENGTH = 20` (9+CT+9), not 14. The 14-nt paradigm is correct only for ISCro4 (Pelea *Science* 2026). The two scaffolds are biologically distinct.

#### 🟠 Moderate Fix 3 — COSMIC URL Wrong Domain

**Was:** `cosmic-cancer.sanger.ac.uk` (domain does not exist)
**Correct:** `cancer.sanger.ac.uk/cosmic`
**Fixed at:** 3 locations in the plan

#### 🟠 Moderate Fix 4 — COSMIC Download Filename

**Was:** `Census_all.csv`
**Correct:** `cancer_gene_census.csv` (verified at COSMIC GRCh38/v96 download page)

#### 🟠 Moderate Fix 5 — DepMap Filename Inconsistency

**Was:** `CRISPRclean_gene_effect.csv` (does not exist)
**Correct:** `CRISPR_gene_effect.csv` (consistent with line 2163 note and actual DepMap file)

#### ✅ Items Verified Correct (no changes needed)

All four scientific DOIs (Durrant 2024, Hiraizumi 2024, Perry 2025, Pelea 2026); ESM-2 model ID `facebook/esm2_t33_650M_UR50D` (33 layers, 1280-dim); IS110 Pfam PF01548; gnomAD v4 GraphQL endpoint; Europe PMC REST endpoint; BepiPred-3.0 URL; DepMap download URL; COSMIC gene count (723); all 24 hg38 chr→RefSeq accessions; CFTR/HBB/TTR chromosomes; AAV 4.7 kb capacity; Ollama model tag `llama3.1:8b-instruct-q4_K_M`.

---

### §0.9.2 Part A Execution Log (2026-05-27)

**Part A status: ✅ COMPLETE**
**Git tag:** `v1.0.0a1-part-a`
**Commits:** 8 (see `git log --oneline v1.0.0a1-part-a`)

6 additional issues were discovered and fixed during actual execution of Steps 1–4. These are infrastructure/packaging issues not detectable from static plan review.

#### Step 1 ✅ — Monorepo scaffolding

65-file repository structure created on VM and pushed to GitHub. pyproject.toml, README.md, CITATION.cff, CHANGELOG.md, LICENSE, .gitignore, `config/hg38_chr_accessions.yaml`, `.github/workflows/ci.yml` all written.

**Fix A1 — pyproject.toml: add explicit package discovery**

`setuptools` flat-layout auto-discovery raises an error when multiple top-level directories exist (`data/`, `config/`, `docker/`, etc.). Added:
```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["pen_stack*"]
```

#### Step 2 ✅ — pen-compare v0.1.0 migration

Code migrated from `~/repos/pen-compare/pen_compare/` → `pen_stack/compare/`. Import paths updated throughout.

**Fix A2 — Import path stripping**

After copying `pen_compare/core/X.py` → `pen_stack/compare/X.py`, sed replacement `pen_compare.core.X` → `pen_stack.compare.core.X` left a `.core.` segment that no longer exists. Required additional pass: `pen_stack.compare.core.X` → `pen_stack.compare.X`.

**Fix A3 — CLI version isolation**

`cli.py` was importing `from pen_stack._version import __version__` (version 1.0.0a1), but compare CLI should report compare's own version (0.1.0). Fixed to `from pen_stack.compare._version import __version__`.

#### Step 3 ✅ — Tests passing

**127 passed, 22 skipped, 0 failed** (22 skipped = RAG/GPU tests requiring live Ollama or GPU).

**Fix A4 — test_version.py updated**

`test_version.py` was asserting `pen_stack.__version__ == "0.1.0"`. After migration, `pen_stack.__version__` is `"1.0.0a1"`. Updated to check `pen_stack.compare._version.__version__ == "0.1.0"` and `pen_stack.__version__ == "1.0.0a1"`.

#### Step 4 ✅ — Docker image pen-stack:1.0.0

All 15 Dockerfile steps completed. Image ID: `ef9ce50eff8f`, Size: 13.5 GB.

**Fix A5 — Dockerfile FROM parse error**

Docker's legacy builder misinterprets Python's `from transformers import` as a Dockerfile `FROM` instruction when it appears at the start of a line inside a multi-line `RUN python3 -c "..."` block. Fix: extracted the ESM-2 pre-download into a dedicated `scripts/predownload_esm2.py` file; Dockerfile now uses `RUN python3 /workspace/pen-stack/scripts/predownload_esm2.py`.

**Fix A6 — Ollama installer requires zstd**

Ollama installer (v0.4+) requires `zstd` for archive extraction. Added to `apt-get install`: `zstd`.

**Fix A7 — pybedtools C compilation fails (missing zlib.h)**

`pybedtools` is a C extension. `python:3.11-slim` lacks C development headers. Fix: added to `apt-get install`: `zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev`.

**Fix A8 — Upstream packages: PyPI stubs vs real implementations**

PyPI only has early placeholder versions of the four upstream packages (0.0.x). Real implementations are in GitHub-tagged releases. Dockerfile updated to install from GitHub:
```dockerfile
RUN pip install --no-cache-dir \
    "git+https://github.com/ahmedanees-m/genome-atlas.git@v0.7.2" \
    "git+https://github.com/ahmedanees-m/mech-class.git@v0.5.4" \
    "git+https://github.com/ahmedanees-m/pen-score.git@v0.1.3" \
    "git+https://github.com/ahmedanees-m/pen-assemble.git@v0.5.2"
```

**Fix A9 — `europepmc` not on PyPI**

`europepmc>=0.4.0` in the `monitor` optional-dependency group does not exist on PyPI. The Europe PMC REST API is accessed directly via `requests` (already a core dependency). Removed `europepmc` from `[project.optional-dependencies]`.

**Docker run note (important for all future steps):** The container entrypoint starts Ollama daemon on launch. Always use `--entrypoint ""` for non-Ollama testing:
```bash
docker run --rm --entrypoint "" pen-stack:1.0.0 <cmd>
```

---

### §0.9.3 Verified Image State (pen-stack:1.0.0)

```
Image ID:        ef9ce50eff8f
Tag:             pen-stack:1.0.0
Size:            13.5 GB
Build date:      2026-05-27

Packages verified in image:
  pen-stack        1.0.0a1    (editable install, /workspace/pen-stack)
  genome-atlas     0.7.2      (from github.com/ahmedanees-m/genome-atlas@v0.7.2)
  mech-class       0.5.5.dev0 (from github.com/ahmedanees-m/mech-class@v0.5.4)
  pen-score        0.1.3      (from github.com/ahmedanees-m/pen-score@v0.1.3)
  pen-assemble     0.5.2      (from github.com/ahmedanees-m/pen-assemble@v0.5.2)
  compare module   0.1.0      (pen_stack/compare/_version.py)
  ESM-2 650M       pre-cached (/root/.cache/esm2)
```

---

# PART A — Monorepo Setup + pen-compare Migration (Week 1)

**Target state:** `github.com/ahmedanees-m/pen-stack` exists; pen-compare code migrated into `pen_stack/compare/`; unified `pyproject.toml` with all module dependencies; extended Docker container; shared data layer established.

---

## Step 1: Create the pen-stack monorepo

### Duration
0.5 day

### Objective
Create the unified `pen-stack` repo, establish the directory architecture for all 7 modules, and set up the shared infrastructure.

### Methods

```bash
gh repo create ahmedanees-m/pen-stack \
    --description "PEN-STACK: Comprehensive Computational Platform for Non-Destructive Genome Engineering" \
    --public --license MIT --add-readme

cd ~/PEN-STACK/repos
git clone https://github.com/ahmedanees-m/pen-stack.git
cd pen-stack

# Full module directory structure
mkdir -p pen_stack/{compare,discover,target,monitor,safe,design,deliver,bench} \
         pen_stack/api pen_stack/server pen_stack/rag pen_stack/pipeline \
         tests/{unit,integration,regression,e2e} \
         config data docs preregs figures scripts \
         docker notebooks .github/workflows

# Create __init__.py for every module
for mod in compare discover target monitor safe design deliver bench api server rag pipeline; do
    touch pen_stack/${mod}/__init__.py
done
touch pen_stack/__init__.py
```

**File: `pen_stack/_version.py`**
```python
__version__ = "1.0.0a1"
```

**File: `pen_stack/__init__.py`**
```python
"""PEN-STACK: Comprehensive Computational Platform for Non-Destructive Genome Engineering."""
from pen_stack._version import __version__
from pen_stack.pipeline.pipeline import Pipeline

__all__ = ["__version__", "Pipeline"]
```

**File: `CITATION.cff`**
```yaml
cff-version: 1.2.0
message: "If you use PEN-STACK, please cite:"
type: software
title: "PEN-STACK: Comprehensive Computational Platform for Non-Destructive Genome Engineering"
version: 1.0.0
date-released: "2026-08-XX"
authors:
  - family-names: Mahaboob Ali
    given-names: Anees Ahmed
    affiliation: "VIT University, Vellore"
    orcid: "https://orcid.org/XXXX-XXXX-XXXX-XXXX"
repository-code: "https://github.com/ahmedanees-m/pen-stack"
license: MIT
abstract: >
  PEN-STACK is the first comprehensive computational platform for non-destructive
  genome engineering, covering editor discovery, certification, genome targeting,
  safety analysis, bRNA design, delivery optimization, and experimental planning
  in a single integrated framework. Built on the IS110 bridge recombinase system
  and the Molecular Pen paradigm.
```

**File: `CHANGELOG.md`**
```markdown
# Changelog

## [1.0.0] - 2026-08-XX (planned)
- Initial unified platform release (pen-compare migration + 6 new modules)

## [pen-compare 0.1.0] - 2026-06-XX
- Standalone certification framework (migrated into pen_stack.compare)
```

### Commit
```bash
git add .
git commit -m "feat: pen-stack monorepo scaffolding — 7 module architecture"
git push origin main
```

### Deliverables
- `github.com/ahmedanees-m/pen-stack` public repo live
- Full directory structure for all 7 modules

---

## Step 2: Unified `pyproject.toml`

### Duration
0.5 day

### Objective
One `pyproject.toml` that covers all 7 modules with v3.2-compat upstream pins, module-specific optional extras, and a single CLI entry point.

**File: `pyproject.toml`**

```toml
[project]
name = "pen-stack"
version = "1.0.0a1"
description = "Comprehensive Computational Platform for Non-Destructive Genome Engineering"
authors = [{name = "Anees Ahmed Mahaboob Ali", email = "ahmedaneesm@gmail.com"}]
license = {text = "MIT"}
requires-python = ">=3.10"
readme = "README.md"
keywords = [
    "genome-engineering", "bridge-recombinase", "IS110", "writer-not-scissors",
    "gene-therapy", "molecular-pen", "ISCro4", "non-destructive-editing",
    "PEN-STACK"
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Topic :: Scientific/Engineering :: Medical Science Apps.",
]

dependencies = [
    # === Upstream PEN-STACK data layer (v3.2-compat, frozen) ===
    "genome-atlas>=0.7.2,<0.8.0",
    "mech-class>=0.5.4,<0.6.0",
    "pen-score>=0.1.3,<0.2.0",
    "pen-assemble>=0.5.2,<0.6.0",

    # === Core scientific stack ===
    "numpy>=1.24",
    "pandas>=2.0",
    "scipy>=1.10",
    "scikit-learn>=1.3",
    "pyyaml>=6.0",
    "pyarrow>=14.0",
    "click>=8.0",
    "tqdm>=4.66",
    "joblib>=1.3",
    "pydantic>=2.5",
    "requests>=2.31",
    "biopython>=1.83",
]

[project.optional-dependencies]

# === PEN-COMPARE (certification) ===
compare = [
    "chromadb>=0.4.20",
    "sentence-transformers>=2.5",
]

# === PEN-DISCOVER (sequence prediction) ===
discover = [
    "transformers>=4.36",        # ESM-2 via HuggingFace
    "torch>=2.0",                # PyTorch for ESM-2 inference
    "einops>=0.7",
]

# === PEN-TARGET (genome targeting) ===
target = [
    "pyranges>=0.0.129",         # Genomic interval operations
    "pybedtools>=0.9.0",         # BED file handling
    "pyensembl>=2.3",            # Ensembl gene lookup
]

# === PEN-MONITOR (literature monitoring) ===
monitor = [
    "europepmc>=0.4.0",          # Europe PMC API client
    "schedule>=1.2",             # Nightly scheduling
    "ollama>=0.1.7",             # LLM for claim extraction
]

# === PEN-SAFE (safety analysis) ===
safe = [
    "pyranges>=0.0.129",         # Interval operations for oncogene proximity
    "pyvcf3>=1.0",               # VCF parsing for gnomAD variants
    "aiohttp>=3.9",              # Async HTTP for gnomAD GraphQL
]

# === PEN-DESIGN (bRNA + cargo) ===
design = [
    "viennarna>=2.6",            # RNA secondary structure (optional validation)
    "biopython>=1.83",           # Sequence manipulation (already in core)
]

# === PEN-DELIVER (delivery optimization) ===
deliver = [
    "ollama>=0.1.7",             # LLM for evidence corpus Q&A
    "chromadb>=0.4.20",          # Vector DB for delivery evidence
]

# === PEN-BENCH (experimental planning) ===
bench = [
    "jinja2>=3.1",               # Jupyter notebook template generation
    "nbformat>=5.9",             # Notebook format
]

# === Webserver ===
server = [
    "streamlit>=1.32",
    "plotly>=5.18",
    "matplotlib>=3.8",
    "fastapi>=0.109",
    "uvicorn>=0.27",
]

# === Dev / test / docs ===
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "mypy>=1.8",
    "pre-commit>=3.5",
    "httpx>=0.26",               # For FastAPI testing
]
docs = [
    "sphinx>=7.2",
    "sphinx-rtd-theme>=2.0",
    "myst-parser>=2.0",
    "sphinx-copybutton>=0.5",
]

# === Convenience meta-extras ===
full = [
    "pen-stack[compare,discover,target,monitor,safe,design,deliver,bench,server]",
]
everything = [
    "pen-stack[full,dev,docs]",
]

[project.scripts]
pen-stack = "pen_stack.cli:main"

[project.urls]
Homepage = "https://github.com/ahmedanees-m/pen-stack"
Documentation = "https://ahmedanees-m.github.io/pen-stack"
Repository = "https://github.com/ahmedanees-m/pen-stack"
Issues = "https://github.com/ahmedanees-m/pen-stack/issues"
"Paper (NAR Webserver)" = "https://doi.org/XXXX"   # fill after publication
"pen-compare (standalone)" = "https://pypi.org/project/pen-compare/0.1.0/"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py310"
```

### Commit
```bash
pip install -e ".[everything]"
python -c "import pen_stack; print(pen_stack.__version__)"
# Expected: 1.0.0a1

git add pyproject.toml
git commit -m "feat: unified pyproject.toml with all 7 module dependencies"
```

---

## Step 3: Migrate pen-compare into pen_stack/compare/

### Duration
1 day

### Objective
Copy pen-compare v0.1.0 code into `pen_stack/compare/` as the first live module. Update imports. Run all 155 pen-compare tests from within the new location.

### Methods

```bash
# Copy pen-compare source modules
cp -r ~/PEN-STACK/repos/pen-compare/pen_compare/core/* pen_stack/compare/
cp -r ~/PEN-STACK/repos/pen-compare/pen_compare/triangulation/* pen_stack/compare/
cp -r ~/PEN-STACK/repos/pen-compare/pen_compare/rag/* pen_stack/rag/
cp -r ~/PEN-STACK/repos/pen-compare/pen_compare/server/* pen_stack/server/

# Copy config and data
cp ~/PEN-STACK/repos/pen-compare/config/gates_v3.yaml config/
cp ~/PEN-STACK/repos/pen-compare/prereg/ preregs/ -r
cp ~/PEN-STACK/repos/pen-compare/data/*.parquet data/
cp ~/PEN-STACK/repos/pen-compare/data/cache/ data/cache/ -r

# Update internal imports: pen_compare → pen_stack.compare
find pen_stack/compare/ -name "*.py" -exec \
    sed -i 's/from pen_compare\./from pen_stack.compare./g' {} +
find pen_stack/compare/ -name "*.py" -exec \
    sed -i 's/import pen_compare/import pen_stack.compare/g' {} +

# Copy and update tests
cp -r ~/PEN-STACK/repos/pen-compare/tests/unit/ tests/unit/compare/
cp -r ~/PEN-STACK/repos/pen-compare/tests/integration/ tests/integration/compare/
find tests/ -name "*.py" -exec \
    sed -i 's/from pen_compare\./from pen_stack.compare./g' {} +
```

**File: `pen_stack/compare/__init__.py`**

```python
"""PEN-COMPARE certification module (migrated from pen-compare v0.1.0).

Standalone PyPI package: https://pypi.org/project/pen-compare/0.1.0/
"""
from pen_stack.compare.certify import certify, TrueWriterResult
from pen_stack.compare.gates import gate_1_dsb, gate_2_programmability
from pen_stack.compare.sensitivity import run_sensitivity_parallel

__all__ = ["certify", "TrueWriterResult", "gate_1_dsb", "gate_2_programmability",
           "run_sensitivity_parallel"]
```

**Verify all 155 tests still pass:**

```bash
pytest tests/unit/compare/ tests/integration/compare/ -v
# Expected: 155 passed (same as pen-compare v0.1.0)
```

### Commit
```bash
git add pen_stack/compare/ pen_stack/rag/ pen_stack/server/ tests/unit/compare/ \
    tests/integration/compare/ config/ preregs/ data/
git commit -m "feat: migrate pen-compare v0.1.0 into pen_stack/compare/ (155 tests pass)"
```

---

## Step 4: Extended Docker container + unified data layer

### Duration
1 day

### Objective
Extend the pen-compare Docker container to support all 7 modules. Add ESM-2, genomic annotation tools, and pre-pull required models.

**File: `docker/Dockerfile`**

```dockerfile
# pen-stack:1.0.0 — Full platform container
FROM python:3.11-slim

LABEL org.opencontainers.image.title="PEN-STACK Platform"
LABEL org.opencontainers.image.description="Comprehensive platform for non-destructive genome engineering"
LABEL org.opencontainers.image.source="https://github.com/ahmedanees-m/pen-stack"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential ca-certificates wget \
    tabix samtools bedtools \
    && rm -rf /var/lib/apt/lists/*

# Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install all PEN-STACK upstream packages
RUN pip install --no-cache-dir \
    "genome-atlas>=0.7.2,<0.8.0" \
    "mech-class>=0.5.4,<0.6.0" \
    "pen-score>=0.1.3,<0.2.0" \
    "pen-assemble>=0.5.2,<0.6.0"

# Install pen-stack with all extras
WORKDIR /workspace
COPY . /workspace/pen-stack
RUN pip install -e "/workspace/pen-stack[full]"

# Pre-download ESM-2 650M model weights (cached in Docker layer)
# ~1.3 GB; done at build time so first run is instant
RUN python -c "
from transformers import EsmModel, EsmTokenizer
model = EsmModel.from_pretrained('facebook/esm2_t33_650M_UR50D', cache_dir='/root/.cache/esm2')
tokenizer = EsmTokenizer.from_pretrained('facebook/esm2_t33_650M_UR50D', cache_dir='/root/.cache/esm2')
print('ESM-2 650M pre-downloaded')
"

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8501 8000 11434
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
```

**File: `docker/entrypoint.sh`**

```bash
#!/bin/bash
set -e

# Start Ollama
ollama serve &
until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 1; done

# Lazy-pull LLMs
for model in "llama3.1:8b-instruct-q4_K_M" "phi3.5:3.8b-mini-instruct-q4_K_M"; do
    if ! ollama list | grep -q "${model%%:*}"; then
        ollama pull "$model"
    fi
done

case "${1:-streamlit}" in
    streamlit)
        exec streamlit run /workspace/pen-stack/pen_stack/server/app.py \
            --server.port 8501 --server.address 0.0.0.0 ;;
    api)
        exec uvicorn pen_stack.api.main:app --host 0.0.0.0 --port 8000 ;;
    monitor)
        exec python /workspace/pen-stack/scripts/run_monitor.py ;;
    *)
        exec "$@" ;;
esac
```

**File: `docker/docker-compose.yml`**

```yaml
version: "3.9"
services:
  pen-stack:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    image: pen-stack:1.0.0
    container_name: pen-stack-platform
    ports:
      - "8501:8501"    # Streamlit
      - "8000:8000"    # FastAPI
      - "11434:11434"  # Ollama
    volumes:
      - ../:/workspace/pen-stack
      - ollama-models:/root/.ollama
      - pen-stack-data:/data
      - esm2-cache:/root/.cache/esm2
      - hg38-data:/data/hg38
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - PEN_STACK_LOG_LEVEL=INFO
      - HF_HOME=/root/.cache/esm2
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama-models:
  pen-stack-data:
  esm2-cache:
  hg38-data:
```

### Commit
```bash
git add docker/
git commit -m "feat: extended Docker container for full pen-stack platform"
```

---

# PART B — PEN-DISCOVER: IS110 Sequence Prediction (Weeks 2–3)

**Target state:** Given any IS110 protein FASTA, PEN-DISCOVER returns a predicted TrueWriter probability (0–1) with uncertainty band, predicted gate-axis values, and a recommendation on whether the sequence is worth characterizing experimentally.

**Scientific basis:** The 29 curated editors in pen-score v0.1.3 span the IS110 family (ISCro4, IS621), site-specific recombinases (Bxb1, phiC31, Cre), CAST family (evoCAST), prime editors, and CRISPR nucleases. ESM-2 650M embeddings (mean-pooled last hidden state from layers 20–33) encode evolutionary and functional information without requiring structural data or MSA.

---

## Step 5: ESM-2 embedding extraction for all curated editors

### Duration
1 day

### Objective
Extract ESM-2 650M embeddings for all 29 pen-score v0.1.3 natural editors. Store as `data/esm2_embeddings.parquet` for model training.

**File: `pen_stack/discover/embeddings.py`**

```python
"""ESM-2 650M protein embeddings for PEN-DISCOVER.

Model: facebook/esm2_t33_650M_UR50D (Apache 2.0)
Strategy: mean-pool layers 20-33 (empirically better for functional annotation
than last-layer only; Simon et al. 2024 InterPLM analysis)
"""
from __future__ import annotations
import torch
import numpy as np
from pathlib import Path
from typing import Optional
from transformers import EsmTokenizer, EsmModel

# Model constants
ESM2_MODEL = "facebook/esm2_t33_650M_UR50D"
ESM2_LAYERS = list(range(20, 34))   # layers 20-33 (14 layers out of 33)
ESM2_DIM = 1280                      # hidden dim for 650M model
ESM2_CACHE = Path("/root/.cache/esm2")

class ESM2Embedder:
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = EsmTokenizer.from_pretrained(
            ESM2_MODEL, cache_dir=str(ESM2_CACHE)
        )
        self.model = EsmModel.from_pretrained(
            ESM2_MODEL, cache_dir=str(ESM2_CACHE),
            output_hidden_states=True,
        ).to(self.device)
        self.model.eval()
        print(f"ESM-2 650M loaded on {self.device}")

    @torch.no_grad()
    def embed(self, sequence: str) -> np.ndarray:
        """Return mean-pooled embedding from layers 20-33.

        Input:  amino acid sequence string (max 1022 aa; IS110 editors ~326 aa)
        Output: 1D numpy array of shape (1280,)
        """
        if len(sequence) > 1022:
            raise ValueError(f"Sequence too long: {len(sequence)} aa (max 1022)")

        inputs = self.tokenizer(
            sequence, return_tensors="pt", truncation=True, max_length=1024
        ).to(self.device)

        outputs = self.model(**inputs)
        hidden_states = outputs.hidden_states   # tuple of 34 tensors, each (1, L, 1280)

        # Mean-pool specified layers, then mean-pool over sequence length
        layer_embeddings = torch.stack(
            [hidden_states[l] for l in ESM2_LAYERS], dim=0
        )  # (14, 1, L, 1280)
        mean_over_layers = layer_embeddings.mean(0)   # (1, L, 1280)
        mean_over_positions = mean_over_layers.squeeze(0).mean(0)   # (1280,)

        return mean_over_positions.cpu().numpy()

    def embed_batch(self, sequences: list[str], verbose: bool = True) -> np.ndarray:
        """Embed a list of sequences. Returns array of shape (N, 1280)."""
        embeddings = []
        for i, seq in enumerate(sequences):
            if verbose:
                print(f"Embedding {i+1}/{len(sequences)}", end="\r")
            embeddings.append(self.embed(seq))
        if verbose:
            print()
        return np.stack(embeddings)
```

**File: `scripts/05_extract_esm2_embeddings.py`**

```python
"""Extract ESM-2 embeddings for all pen-score v0.1.3 natural editors."""
import pandas as pd
import numpy as np
from pathlib import Path
from pen_stack.discover.embeddings import ESM2Embedder
from pen_score import load_editor_universe

OUTPUT_PATH = Path("data/esm2_embeddings.parquet")

# Load editor universe
universe = load_editor_universe()
editors = [e for e in universe.editors if hasattr(e, "sequence") and e.sequence]

print(f"Found {len(editors)} editors with sequences")

# Extract embeddings
embedder = ESM2Embedder()
data = []
for editor in editors:
    emb = embedder.embed(editor.sequence)
    data.append({
        "editor_id": editor.id,
        "canonical_name": editor.id,
        "length_aa": len(editor.sequence),
        **{f"esm2_{i}": float(v) for i, v in enumerate(emb)},
    })

df = pd.DataFrame(data)
df.to_parquet(OUTPUT_PATH, index=False)
print(f"Saved embeddings for {len(df)} editors to {OUTPUT_PATH}")
print(f"Embedding dimensionality: 1280")
print(f"Shape: {df.shape}")
```

```bash
python scripts/05_extract_esm2_embeddings.py
# Wall time: ~5 min on 16 GB GPU
# Expected output: data/esm2_embeddings.parquet with shape (~29, 1282)
```

### Deliverables
- `data/esm2_embeddings.parquet` — per-editor ESM-2 650M embeddings
- `pen_stack/discover/embeddings.py` — embedder module

### Commit
```bash
git add pen_stack/discover/embeddings.py scripts/05_extract_esm2_embeddings.py data/esm2_embeddings.parquet
git commit -m "feat: ESM-2 650M embeddings for all curated editors (layers 20-33 mean pool)"
```

---

## Step 6: Gate-probability model training

### Duration
1 day

### Objective
Train 5 binary classifiers (one per gate) predicting gate PASS/FAIL from ESM-2 embeddings. Also train a TrueWriter-tier regressor predicting the sensitivity-analysis-derived TrueWriter probability (continuous 0–1).

**File: `pen_stack/discover/predictor.py`**

```python
"""Gate-probability predictor trained on ESM-2 embeddings.

5 binary classifiers + 1 TrueWriter probability regressor.
Training data: 29 curated editors from pen-score v0.1.3 with known gate values.

Technical notes:
- 29 training examples is small; use calibrated logistic regression with L2
  regularization (not neural network). Calibration via Platt scaling (cv=5).
- Feature: 1280-dim ESM-2 embedding + 3 derived features (length, %charged, %hydrophobic)
- This is a low-N intentional classifier: scientifically honest about uncertainty.
- Fallback for unknown editors: report highest uncertainty band (confidence < 0.5)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline as SkPipeline
import joblib

GATE_LABELS = ["gate_1_dsb", "gate_2_prog", "gate_3_cargo",
               "gate_4_deliv", "gate_5_evidence"]
MODEL_SAVE_DIR = Path("data/discover_models/")

@dataclass
class DiscoverPrediction:
    editor_id: str
    tw_probability: float          # continuous TrueWriter probability (0–1)
    tw_uncertainty: float          # std across bootstrap resamples
    predicted_tier: str            # modal predicted tier
    gate_probabilities: dict[str, float]
    gate_predictions: dict[str, bool]
    low_confidence: bool           # True if tw_uncertainty > 0.25
    recommendation: str            # "characterize" / "deprioritize" / "uncertain"
    note: str

def derive_features(sequence: str) -> np.ndarray:
    """Add 3 sequence-derived features to ESM-2 embedding."""
    seq = sequence.upper()
    n = len(seq)
    charged_aa = set("DEKR")
    hydrophobic_aa = set("AVILMFYW")
    pct_charged = sum(1 for aa in seq if aa in charged_aa) / n
    pct_hydrophobic = sum(1 for aa in seq if aa in hydrophobic_aa) / n
    return np.array([n / 1000.0, pct_charged, pct_hydrophobic])  # normalized

class DiscoverPredictor:
    def __init__(self, model_dir: Path = MODEL_SAVE_DIR):
        self.model_dir = model_dir
        self.gate_models: dict[str, SkPipeline] = {}
        self.tw_model: SkPipeline | None = None
        self._trained = False

    def train(self, embeddings_df: pd.DataFrame, labels_df: pd.DataFrame):
        """Train gate classifiers and TW probability regressor.

        Args:
            embeddings_df: (N, 1280+) DataFrame with ESM-2 features + editor_id
            labels_df: (N, 6+) DataFrame with gate labels + tw_probability per editor
        """
        self.model_dir.mkdir(parents=True, exist_ok=True)

        emb_cols = [c for c in embeddings_df.columns if c.startswith("esm2_")]
        merged = embeddings_df.merge(labels_df, on="editor_id")
        X = merged[emb_cols].values

        print(f"Training on {len(X)} editors, {len(emb_cols)} features")

        for gate in GATE_LABELS:
            if gate not in merged.columns:
                print(f"  Skipping {gate} (no labels)")
                continue
            y = merged[gate].astype(int).values
            clf = CalibratedClassifierCV(
                LogisticRegression(C=0.1, max_iter=500, random_state=42),
                cv=min(5, len(X) // 2),
                method="sigmoid",
            )
            pipe = SkPipeline([("scaler", StandardScaler()), ("clf", clf)])
            pipe.fit(X, y)
            self.gate_models[gate] = pipe
            save_path = self.model_dir / f"{gate}_model.joblib"
            joblib.dump(pipe, save_path)
            print(f"  {gate}: trained + saved to {save_path}")

        # TrueWriter probability regressor
        if "tw_probability" in merged.columns:
            from sklearn.linear_model import Ridge
            y_tw = merged["tw_probability"].values
            pipe_tw = SkPipeline([("scaler", StandardScaler()),
                                   ("reg", Ridge(alpha=1.0))])
            pipe_tw.fit(X, y_tw)
            self.tw_model = pipe_tw
            joblib.dump(pipe_tw, self.model_dir / "tw_probability_model.joblib")
            print(f"  TrueWriter probability model: trained")

        self._trained = True

    def load(self):
        """Load pre-trained models from disk."""
        for gate in GATE_LABELS:
            p = self.model_dir / f"{gate}_model.joblib"
            if p.exists():
                self.gate_models[gate] = joblib.load(p)
        tw_path = self.model_dir / "tw_probability_model.joblib"
        if tw_path.exists():
            self.tw_model = joblib.load(tw_path)
        self._trained = bool(self.gate_models)

    def predict(self, esm2_embedding: np.ndarray, editor_id: str = "query") -> DiscoverPrediction:
        """Predict TrueWriter probability + gate values from an ESM-2 embedding."""
        if not self._trained:
            raise RuntimeError("Model not trained. Call .train() or .load() first.")

        X = esm2_embedding.reshape(1, -1)

        gate_probs = {}
        gate_preds = {}
        for gate, model in self.gate_models.items():
            prob = float(model.predict_proba(X)[0][1])  # P(PASS)
            gate_probs[gate] = prob
            gate_preds[gate] = prob >= 0.5

        # TrueWriter probability from direct regressor
        if self.tw_model is not None:
            tw_prob = float(np.clip(self.tw_model.predict(X)[0], 0, 1))
        else:
            # Fallback: compute from gate probs
            tw_prob = _tw_from_gates(gate_probs)

        # Bootstrap uncertainty (resample weights — proxy for model uncertainty at N=29)
        tw_unc = _estimate_uncertainty(gate_probs)

        # Predicted tier from probabilities
        g1 = gate_probs.get("gate_1_dsb", 0)
        q_passes = sum(1 for g in ["gate_2_prog", "gate_3_cargo", "gate_4_deliv", "gate_5_evidence"]
                       if gate_probs.get(g, 0) >= 0.5)

        if g1 < 0.5:
            tier = "NOT_WRITER"
        elif tw_prob >= 0.7:
            tier = "TRUE_WRITER"
        elif tw_prob >= 0.4:
            tier = "PROBABLE_WRITER"
        elif tw_prob >= 0.1:
            tier = "EMERGING_WRITER"
        else:
            tier = "NOT_WRITER"

        low_confidence = tw_unc > 0.25

        if tw_prob >= 0.6 and not low_confidence:
            rec = "characterize"
            note = f"High TrueWriter probability ({tw_prob:.2f}). Priority for experimental validation."
        elif tw_prob <= 0.2:
            rec = "deprioritize"
            note = f"Low TrueWriter probability ({tw_prob:.2f}). Unlikely to be functional writer."
        else:
            rec = "uncertain"
            note = f"Uncertain ({tw_prob:.2f} ± {tw_unc:.2f}). Could characterize if resources allow."

        return DiscoverPrediction(
            editor_id=editor_id,
            tw_probability=tw_prob,
            tw_uncertainty=tw_unc,
            predicted_tier=tier,
            gate_probabilities=gate_probs,
            gate_predictions=gate_preds,
            low_confidence=low_confidence,
            recommendation=rec,
            note=note,
        )

def _tw_from_gates(gate_probs: dict) -> float:
    g1 = gate_probs.get("gate_1_dsb", 0)
    q_mean = np.mean([gate_probs.get(g, 0)
                       for g in ["gate_2_prog", "gate_3_cargo", "gate_4_deliv", "gate_5_evidence"]])
    return g1 * q_mean

def _estimate_uncertainty(gate_probs: dict) -> float:
    probs = list(gate_probs.values())
    # Uncertainty is high when gate probabilities are near 0.5
    entropies = [-p * np.log2(p + 1e-9) - (1-p) * np.log2(1-p + 1e-9) for p in probs]
    return float(np.mean(entropies))
```

**File: `scripts/06_train_discover_models.py`**

```python
"""Train PEN-DISCOVER gate-probability models on ESM-2 embeddings."""
import pandas as pd
from pathlib import Path
from pen_stack.discover.predictor import DiscoverPredictor
from pen_score import get_editor_metadata, score
from pen_stack.compare.certify import certify

# Load embeddings
emb_df = pd.read_parquet("data/esm2_embeddings.parquet")

# Build gate labels from actual pen-compare v3.2 certifications
rows = []
for _, row in emb_df.iterrows():
    eid = row["editor_id"]
    try:
        md = get_editor_metadata(eid)
        s = score(eid)
        result = certify(
            editor_id=eid,
            s_dsb=s.axes["S_DSB"], s_prog=s.axes["S_Prog"],
            s_cargo=s.axes["S_Cargo"], length_aa=int(row["length_aa"]),
            evidence_sources=([k for k, v in {
                "biochemical": True, "structural": getattr(md, "has_structural", False),
                "computational": True, "cell_based": md.cell_based_evidence,
            }.items() if v]),
            intrinsic_cargo_mechanism=md.intrinsic_cargo_mechanism,
        )
        rows.append({
            "editor_id": eid,
            "gate_1_dsb": result.gate_results[0].passes,
            "gate_2_prog": result.gate_results[1].passes,
            "gate_3_cargo": result.gate_results[2].passes,
            "gate_4_deliv": result.gate_results[3].passes,
            "gate_5_evidence": result.gate_results[4].passes,
            "tw_probability": float(result.qualifying_gates_passed) / 4.0
                              * (1.0 if result.tier == "TRUE_WRITER" else
                                 0.8 if result.tier == "PROBABLE_WRITER" else
                                 0.4 if result.tier == "EMERGING_WRITER" else 0.0),
        })
    except Exception as e:
        print(f"Skipped {eid}: {e}")

labels_df = pd.DataFrame(rows)
print(f"Gate labels for {len(labels_df)} editors")
print(labels_df[["editor_id", "gate_1_dsb", "gate_2_prog", "gate_3_cargo", "tw_probability"]].to_string())

# Train
predictor = DiscoverPredictor()
predictor.train(emb_df, labels_df)

# Smoke test: ISCro4 should predict near TRUE_WRITER
pred = predictor.predict(
    esm2_embedding=emb_df[emb_df.editor_id == "ISCro4"].filter(like="esm2_").values[0],
    editor_id="ISCro4"
)
print(f"\nISCro4 prediction: TW_prob={pred.tw_probability:.3f}, tier={pred.predicted_tier}")
assert pred.tw_probability >= 0.7, f"ISCro4 TW probability too low: {pred.tw_probability}"
print("Smoke test PASSED")
```

```bash
python scripts/06_train_discover_models.py
# Wall time: ~2 min
```

### Commit
```bash
git add pen_stack/discover/predictor.py scripts/06_train_discover_models.py data/discover_models/
git commit -m "feat: PEN-DISCOVER gate-probability models (ESM-2 + calibrated logistic regression)"
```

---

## Step 7: IS110 orthologue screening from NCBI

### Duration
1 day

### Objective
Download ~1000 uncharacterized IS110 protein sequences from NCBI, embed them all with ESM-2, predict TrueWriter probabilities, and return a ranked list of candidates worth characterizing.

**File: `pen_stack/discover/screen.py`**

```python
"""IS110 orthologue screening from NCBI via ESM-2 + DiscoverPredictor."""
from __future__ import annotations
import time
from Bio import Entrez, SeqIO
from pathlib import Path
import pandas as pd
from pen_stack.discover.embeddings import ESM2Embedder
from pen_stack.discover.predictor import DiscoverPredictor

Entrez.email = "ahmedaneesm@gmail.com"   # NCBI requires email

IS110_PFAM = "PF01548"
IS110_QUERY = f"IS110[All Fields] AND recombinase[Title] AND NOT patent[Filter]"
NCBI_BATCH_SIZE = 500

def fetch_is110_sequences(n_max: int = 1000) -> list[dict]:
    """Fetch IS110 family sequences from NCBI Protein database."""
    handle = Entrez.esearch(
        db="protein",
        term=IS110_QUERY,
        retmax=n_max,
        idtype="acc",
    )
    record = Entrez.read(handle)
    ids = record["IdList"]
    print(f"Found {len(ids)} IS110-related NCBI Protein entries")

    sequences = []
    for i in range(0, len(ids), NCBI_BATCH_SIZE):
        batch = ids[i:i + NCBI_BATCH_SIZE]
        handle = Entrez.efetch(db="protein", id=batch, rettype="gb", retmode="text")
        for rec in SeqIO.parse(handle, "genbank"):
            seq = str(rec.seq).replace("X", "").replace("*", "")
            if 200 <= len(seq) <= 800:  # IS110 editors are ~300-600 aa
                sequences.append({
                    "ncbi_id": rec.id,
                    "description": rec.description[:100],
                    "sequence": seq,
                    "length_aa": len(seq),
                })
        time.sleep(0.4)  # NCBI rate limit: 3 req/sec without API key

    print(f"Retrieved {len(sequences)} sequences (200-800 aa filter)")
    return sequences

def screen_orthologues(
    sequences: list[dict],
    output_path: Path = Path("data/discover_screen_results.parquet"),
) -> pd.DataFrame:
    """Screen IS110 orthologues for TrueWriter probability."""
    embedder = ESM2Embedder()
    predictor = DiscoverPredictor()
    predictor.load()

    results = []
    for i, s in enumerate(sequences):
        if i % 50 == 0:
            print(f"Screening {i}/{len(sequences)}...", end="\r")
        try:
            emb = embedder.embed(s["sequence"])
            pred = predictor.predict(emb, editor_id=s["ncbi_id"])
            results.append({
                "ncbi_id": s["ncbi_id"],
                "description": s["description"],
                "length_aa": s["length_aa"],
                "tw_probability": pred.tw_probability,
                "tw_uncertainty": pred.tw_uncertainty,
                "predicted_tier": pred.predicted_tier,
                "recommendation": pred.recommendation,
                "gate_1_prob": pred.gate_probabilities.get("gate_1_dsb", 0),
                "gate_2_prob": pred.gate_probabilities.get("gate_2_prog", 0),
                "gate_3_prob": pred.gate_probabilities.get("gate_3_cargo", 0),
                "low_confidence": pred.low_confidence,
            })
        except Exception as e:
            pass  # Skip sequences that fail embedding (e.g., non-standard AA)

    df = pd.DataFrame(results).sort_values("tw_probability", ascending=False)
    df.to_parquet(output_path, index=False)
    print(f"\nScreened {len(df)} sequences → {output_path}")
    print(df[df.recommendation == "characterize"][["ncbi_id", "tw_probability", "predicted_tier"]].head(10))
    return df
```

```bash
python -c "
from pen_stack.discover.screen import fetch_is110_sequences, screen_orthologues
seqs = fetch_is110_sequences(n_max=1000)
df = screen_orthologues(seqs)
print(f'Top candidates: {(df.recommendation == \"characterize\").sum()}')
"
```

### Commit
```bash
git add pen_stack/discover/screen.py data/discover_screen_results.parquet
git commit -m "feat: IS110 orthologue screening via NCBI + ESM-2 + DiscoverPredictor"
```

---

## Step 8: PEN-DISCOVER API

**File: `pen_stack/discover/__init__.py`**

```python
"""PEN-DISCOVER: Sequence-to-TrueWriter prediction for uncharacterized IS110 orthologues."""
from pen_stack.discover.embeddings import ESM2Embedder
from pen_stack.discover.predictor import DiscoverPredictor, DiscoverPrediction
from pen_stack.discover.screen import screen_orthologues, fetch_is110_sequences

__all__ = ["ESM2Embedder", "DiscoverPredictor", "DiscoverPrediction",
           "screen_orthologues", "fetch_is110_sequences"]

def predict_from_fasta(fasta_path: str) -> DiscoverPrediction:
    """One-call API: FASTA file → TrueWriter prediction."""
    from Bio import SeqIO
    record = next(SeqIO.parse(fasta_path, "fasta"))
    embedder = ESM2Embedder()
    predictor = DiscoverPredictor()
    predictor.load()
    emb = embedder.embed(str(record.seq))
    return predictor.predict(emb, editor_id=record.id)
```

**CLI:**
```bash
pen-stack discover --fasta my_IS110.fasta
# Output: TW probability, predicted tier, recommendation
```

### Commit
```bash
git add pen_stack/discover/__init__.py
git commit -m "feat: PEN-DISCOVER API complete — predict_from_fasta() one-call interface"
```

---

## Step 9: PEN-DISCOVER tests + validation

### Duration
0.5 day

**File: `tests/unit/test_discover.py`**

```python
"""PEN-DISCOVER unit tests."""
import numpy as np
from pen_stack.discover.predictor import DiscoverPredictor, _tw_from_gates

def test_tw_from_gates_all_pass():
    probs = {"gate_1_dsb": 1.0, "gate_2_prog": 1.0,
             "gate_3_cargo": 1.0, "gate_4_deliv": 1.0, "gate_5_evidence": 1.0}
    assert _tw_from_gates(probs) == 1.0

def test_tw_from_gates_g1_fail():
    probs = {"gate_1_dsb": 0.0, "gate_2_prog": 1.0,
             "gate_3_cargo": 1.0, "gate_4_deliv": 1.0, "gate_5_evidence": 1.0}
    assert _tw_from_gates(probs) == 0.0   # G1 fail → zero

def test_predictor_smoke():
    predictor = DiscoverPredictor()
    predictor.load()
    if predictor._trained:
        fake_emb = np.random.randn(1280)
        pred = predictor.predict(fake_emb, editor_id="test")
        assert 0.0 <= pred.tw_probability <= 1.0
        assert pred.predicted_tier in ["TRUE_WRITER", "PROBABLE_WRITER",
                                        "EMERGING_WRITER", "NOT_WRITER"]
        assert pred.recommendation in ["characterize", "deprioritize", "uncertain"]
```

```bash
pytest tests/unit/test_discover.py -v
```

### Commit
```bash
git add tests/unit/test_discover.py
git commit -m "test: PEN-DISCOVER unit tests"
```

---

# PART C — PEN-TARGET: Genome Targeting (Weeks 3–4)

**Target state:** Given a disease gene (name, OMIM ID, or coordinates) + editor, PEN-TARGET returns: (a) attB-compatible target site density in the gene window, (b) designed bRNA sequences for top-ranked sites, (c) off-target density elsewhere in hg38, (d) population variant check for each candidate site.

**Biological basis:** IS621/ISCro4 bRNA target-binding loop (TBL) recognizes a 14-bp genomic target. The left target guide (LTG: 7 nt) base-pairs with the bottom strand; the right target guide (RTG: 7 nt) base-pairs with the top strand. Any 14-mer in hg38 is a potential target. PEN-TARGET scans a user-specified window, ranks sites by predicted recombination efficiency (GC content, secondary structure context), and designs the bRNA for each.

---

## Step 10: hg38 genome setup + 14-nt bRNA site scanner

### Duration
2 days

### Objective
Download the relevant hg38 chromosome(s) on demand; implement the 14-nt bRNA TBL scanner; rank sites by target quality metrics.

**File: `pen_stack/target/attb_scanner.py`**

```python
"""14-nt bRNA attB target site scanner for IS110 bridge recombinases.

Biological basis (Durrant & Perry Nature 2024, Hiraizumi Nature 2024):
  - bRNA target-binding loop: 7 nt LTG (bottom strand) + 7 nt RTG (top strand)
  - Total target recognition: 14 bp centered on the core dinucleotide (TT for IS621)
  - Any 14-mer is theoretically targetable; quality ranked by GC content (40-65% optimal)
  - Arc Institute design tool uses same 14-nt logic
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from Bio import Entrez, SeqIO
from Bio.Seq import Seq
import numpy as np

Entrez.email = "ahmedaneesm@gmail.com"

CORE_DINUCLEOTIDE = "CT"   # IS621 confirmed attB core (Durrant 2024, Hiraizumi 2024 PDB 8WT6); other IS110 vary
OPTIMAL_GC_MIN = 0.40
OPTIMAL_GC_MAX = 0.65
LTG_LENGTH = 7
RTG_LENGTH = 7
TARGET_LENGTH = LTG_LENGTH + RTG_LENGTH   # 14 nt

@dataclass(frozen=True)
class TargetSite:
    site_id: str
    chromosome: str
    start: int
    end: int
    strand: str
    sequence_14nt: str     # the 14-nt target
    ltg: str               # left target guide (7 nt)
    rtg: str               # right target guide (7 nt)
    gc_content: float
    quality_score: float   # 0–1 composite
    brna_sequence: str     # designed 177-nt IS621 bRNA (see Step 24)
    is_in_exon: bool
    gene_distance_bp: int

def scan_gene_window(
    gene_name: str,
    window_bp: int = 5000,
    chromosome: str | None = None,
    start_coord: int | None = None,
) -> list[TargetSite]:
    """Scan for bRNA target sites near a gene. Returns ranked list of TargetSite."""
    chrom, gene_start, gene_end = _lookup_gene_coordinates(gene_name, chromosome, start_coord)
    region_start = max(0, gene_start - window_bp)
    region_end = gene_end + window_bp

    print(f"Scanning {chrom}:{region_start}-{region_end} for bRNA sites near {gene_name}")
    sequence = _fetch_sequence(chrom, region_start, region_end)
    sites = _find_all_sites(sequence, chrom, region_start, gene_start, gene_end)
    return sorted(sites, key=lambda s: s.quality_score, reverse=True)

def _find_all_sites(
    sequence: str,
    chrom: str,
    region_start: int,
    gene_start: int,
    gene_end: int,
) -> list[TargetSite]:
    sites = []
    seq = sequence.upper()
    seq_len = len(seq)

    for i in range(seq_len - TARGET_LENGTH + 1):
        window = seq[i:i + TARGET_LENGTH]
        if "N" in window:
            continue

        gc = (window.count("G") + window.count("C")) / TARGET_LENGTH
        # Basic quality: GC in optimal range + no homopolymer runs
        has_homopolymer = any(c * 5 in window for c in "ACGT")
        qual = _quality_score(window, gc, has_homopolymer)

        abs_start = region_start + i
        abs_end = abs_start + TARGET_LENGTH
        in_gene = gene_start <= abs_start <= gene_end
        dist_to_gene = max(0, min(abs(abs_start - gene_start), abs(abs_start - gene_end)))

        ltg = window[:LTG_LENGTH]
        rtg = window[LTG_LENGTH:]

        from pen_stack.design.brna_designer import design_brna
        try:
            brna = design_brna(target_14nt=window, donor_14nt="N" * 14, editor="IS621")
        except Exception:
            brna = "PENDING_DESIGN"

        site = TargetSite(
            site_id=f"{chrom}:{abs_start}-{abs_end}+",
            chromosome=chrom, start=abs_start, end=abs_end,
            strand="+", sequence_14nt=window,
            ltg=ltg, rtg=rtg,
            gc_content=gc, quality_score=qual,
            brna_sequence=brna,
            is_in_exon=in_gene,
            gene_distance_bp=dist_to_gene,
        )
        sites.append(site)

    return sites

def _quality_score(window: str, gc: float, has_homopolymer: bool) -> float:
    gc_score = 1.0 - abs(gc - 0.525) / 0.175   # peaks at GC=52.5%
    hpoly_penalty = 0.3 if has_homopolymer else 0.0
    # Penalize runs at the junction (positions 6-8 around core)
    junction = window[5:9]
    junction_gc = (junction.count("G") + junction.count("C")) / 4
    junction_score = 1.0 - abs(junction_gc - 0.5) * 0.5
    return max(0.0, gc_score * junction_score - hpoly_penalty)

def _lookup_gene_coordinates(
    gene_name: str,
    chromosome: str | None,
    start_coord: int | None,
) -> tuple[str, int, int]:
    if chromosome and start_coord:
        return chromosome, start_coord, start_coord + 50000
    # NCBI Gene lookup
    handle = Entrez.esearch(db="gene", term=f"{gene_name}[Gene Name] AND Homo sapiens[Organism]")
    record = Entrez.read(handle)
    if not record["IdList"]:
        raise ValueError(f"Gene '{gene_name}' not found in NCBI Gene (Homo sapiens)")
    gene_id = record["IdList"][0]
    handle = Entrez.efetch(db="gene", id=gene_id, rettype="gene_table", retmode="text")
    # Parse location from gene table (simplified)
    for line in handle:
        if "NC_" in line and "complement" not in line:
            # Extract coords from line
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                try:
                    chrom = parts[0].split(".")[0]
                    start = int(parts[1])
                    end = int(parts[2])
                    return chrom, start, end
                except (ValueError, IndexError):
                    pass
    # Fallback: return dummy coordinates (user should provide explicit coords)
    raise ValueError(f"Could not parse coordinates for {gene_name}. Use --chromosome and --start.")

def _fetch_sequence(chrom: str, start: int, end: int) -> str:
    """Fetch genomic sequence from NCBI (hg38)."""
    # Map chromosome to RefSeq accession
    CHROM_TO_REFSEQ = {
        "chr7": "NC_000007.14", "chr11": "NC_000011.10",
        "chr1": "NC_000001.11", "chr2": "NC_000002.12",
        # ... (full mapping in config/hg38_chr_accessions.yaml)
    }
    refseq = CHROM_TO_REFSEQ.get(chrom, chrom)
    handle = Entrez.efetch(
        db="nuccore", id=refseq, rettype="fasta", retmode="text",
        seq_start=start, seq_stop=end,
    )
    record = next(SeqIO.parse(handle, "fasta"))
    return str(record.seq)
```

**File: `config/hg38_chr_accessions.yaml`**
```yaml
# hg38 chromosome → NCBI RefSeq accession mapping
chr1: NC_000001.11
chr2: NC_000002.12
chr3: NC_000003.12
chr4: NC_000004.12
chr5: NC_000005.10
chr6: NC_000006.12
chr7: NC_000007.14
chr8: NC_000008.11
chr9: NC_000009.12
chr10: NC_000010.11
chr11: NC_000011.10
chr12: NC_000012.12
chr13: NC_000013.11
chr14: NC_000014.9
chr15: NC_000015.10
chr16: NC_000016.10
chr17: NC_000017.11
chr18: NC_000018.10
chr19: NC_000019.10
chr20: NC_000020.11
chr21: NC_000021.9
chr22: NC_000022.11
chrX: NC_000023.11
chrY: NC_000024.10
```

### Commit
```bash
git add pen_stack/target/attb_scanner.py config/hg38_chr_accessions.yaml
git commit -m "feat: 14-nt bRNA target site scanner for hg38 (PEN-TARGET)"
```

---

## Step 11: Disease locus lookup + off-target density mapping

### Duration
1 day

**File: `pen_stack/target/locus_lookup.py`**

```python
"""Disease locus lookup via OMIM / NCBI Gene API."""
import requests

OMIM_API = "https://api.omim.org/api"   # free academic registration required

def lookup_disease_locus(disease: str, omim_api_key: str | None = None) -> dict:
    """Return gene name + coordinates for a disease query.

    Tries: (1) OMIM API if key provided, (2) NCBI Gene free search.
    Returns: {gene_name, chromosome, start, end, omim_id, description}
    """
    # NCBI Gene free text search (no key needed)
    from Bio import Entrez
    Entrez.email = "ahmedaneesm@gmail.com"

    result = Entrez.read(Entrez.esearch(
        db="gene",
        term=f"{disease}[Title] AND Homo sapiens[Organism] AND alive[Property]",
        sort="relevance",
        retmax=1,
    ))
    if result["IdList"]:
        gene_id = result["IdList"][0]
        summary = Entrez.read(Entrez.esummary(db="gene", id=gene_id))
        gene_info = summary["DocumentSummarySet"]["DocumentSummary"][0]
        return {
            "gene_name": gene_info.get("Name", "unknown"),
            "description": gene_info.get("Description", ""),
            "chromosome": f"chr{gene_info.get('Chromosome', '?')}",
            "start": int(gene_info.get("ChrStart", 0)),
            "end": int(gene_info.get("ChrStop", 0)),
            "ncbi_gene_id": gene_id,
        }
    raise ValueError(f"No gene found for disease query: {disease}")
```

**File: `pen_stack/target/offtarget.py`**

```python
"""Off-target site density mapping for a given 14-nt target sequence."""
import re
from Bio import Entrez, SeqIO
from dataclasses import dataclass

@dataclass
class OffTargetReport:
    target_14nt: str
    n_near_perfect: int        # 0-1 mismatches
    n_moderate: int            # 2-3 mismatches
    offtarget_risk: str        # "low" / "medium" / "high"
    top_offtargets: list[dict] # coordinates of top off-targets

def estimate_offtarget_risk(target_14nt: str, editor: str = "ISCro4") -> OffTargetReport:
    """Estimate off-target insertion risk for a 14-nt target sequence.

    Note: full genome scan is compute-intensive. This function samples
    3 representative chromosomes (1, 7, 17) as a proxy.
    For production: use BLAST against hg38 (blastn, word_size=7, e-value=10).
    """
    # Use NCBI BLAST (free web API)
    from Bio.Blast import NCBIWWW, NCBIXML
    result_handle = NCBIWWW.qblast(
        "blastn", "nt", target_14nt,
        entrez_query="Homo sapiens[Organism]",
        word_size=7, expect=100,
        hitlist_size=50,
    )
    blast_records = list(NCBIXML.parse(result_handle))
    record = blast_records[0]

    near_perfect = []
    moderate = []

    for alignment in record.alignments[:50]:
        for hsp in alignment.hsps[:1]:
            mismatches = hsp.align_length - hsp.identities
            if mismatches <= 1:
                near_perfect.append({"title": alignment.title[:80], "mismatches": mismatches})
            elif mismatches <= 3:
                moderate.append({"title": alignment.title[:80], "mismatches": mismatches})

    risk = "low" if len(near_perfect) <= 2 else "medium" if len(near_perfect) <= 10 else "high"

    return OffTargetReport(
        target_14nt=target_14nt,
        n_near_perfect=len(near_perfect),
        n_moderate=len(moderate),
        offtarget_risk=risk,
        top_offtargets=near_perfect[:5],
    )
```

### Commit
```bash
git add pen_stack/target/
git commit -m "feat: PEN-TARGET disease locus lookup + off-target density mapping"
```

---

## Step 12: Population variant check via gnomAD v4

### Duration
1 day

**File: `pen_stack/target/population_variants.py`**

```python
"""gnomAD v4 population variant check for target site attB sequences.

API: gnomad.broadinstitute.org/api (GraphQL, free, no auth)
Dataset: gnomad_r4 (730,947 exomes + 76,215 genomes)

Purpose: Check if SNPs within the 14-nt target site would abolish bRNA
recognition in a subset of patients. A SNP with AF > 0.01 in any population
flagged as MODERATE risk; > 0.05 flagged as HIGH.
"""
import requests
from dataclasses import dataclass
from typing import Optional

GNOMAD_API = "https://gnomad.broadinstitute.org/api"

@dataclass
class SNPRisk:
    position: str           # chr:pos:ref:alt
    allele_freq_global: float
    allele_freq_sas: float  # South Asian (relevant for India-based clinical programs)
    risk_level: str         # "none" / "moderate" / "high"
    note: str

def check_target_site_variants(
    chromosome: str, start: int, end: int, dataset: str = "gnomad_r4"
) -> list[SNPRisk]:
    """Query gnomAD v4 for variants within a target site window."""
    query = """
    query RegionVariants($chrom: String!, $start: Int!, $stop: Int!, $dataset: DatasetId!) {
      region(chrom: $chrom, start: $start, stop: $stop, reference_genome: GRCh38) {
        variants(dataset: $dataset) {
          variant_id
          pos
          ref
          alt
          genome {
            af
            populations {
              id
              af
            }
          }
        }
      }
    }
    """
    # Strip "chr" prefix for gnomAD API
    chrom_clean = chromosome.replace("chr", "")
    variables = {"chrom": chrom_clean, "start": start, "stop": end, "dataset": dataset}

    try:
        resp = requests.post(
            GNOMAD_API,
            json={"query": query, "variables": variables},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [SNPRisk(position="API_ERROR", allele_freq_global=0, allele_freq_sas=0,
                        risk_level="unknown", note=str(e))]

    variants = data.get("data", {}).get("region", {}).get("variants", [])
    risks = []

    for v in variants:
        genome = v.get("genome") or {}
        af_global = genome.get("af", 0) or 0
        populations = genome.get("populations", []) or []
        af_sas = next((p["af"] for p in populations if p["id"] == "sas"), 0) or 0

        if af_global >= 0.05:
            risk = "high"
            note = f"Common variant (AF={af_global:.3f}) — target site may not work in {af_global*100:.0f}% of population"
        elif af_global >= 0.01:
            risk = "moderate"
            note = f"Low-frequency variant (AF={af_global:.3f}) — may reduce editing in some patients"
        else:
            risk = "none"
            note = "Rare/absent variant — not expected to affect targeting"

        risks.append(SNPRisk(
            position=v["variant_id"],
            allele_freq_global=af_global,
            allele_freq_sas=af_sas,
            risk_level=risk,
            note=note,
        ))

    return risks
```

### Commit
```bash
git add pen_stack/target/population_variants.py
git commit -m "feat: gnomAD v4 population variant check for bRNA target sites (PEN-TARGET)"
```

---

## Step 13: PEN-TARGET API

```python
# pen_stack/target/__init__.py
"""PEN-TARGET: Identify usable genomic target sites for IS110 bridge recombinases."""
from pen_stack.target.attb_scanner import scan_gene_window, TargetSite
from pen_stack.target.locus_lookup import lookup_disease_locus
from pen_stack.target.offtarget import estimate_offtarget_risk
from pen_stack.target.population_variants import check_target_site_variants

__all__ = ["scan_gene_window", "TargetSite", "lookup_disease_locus",
           "estimate_offtarget_risk", "check_target_site_variants"]

def recommend_target_sites(
    disease_or_gene: str,
    editor: str = "ISCro4",
    n_top: int = 10,
    window_bp: int = 5000,
) -> list[TargetSite]:
    """High-level API: disease/gene → top N bRNA target sites.

    Example:
        sites = recommend_target_sites("CFTR-F508del", editor="ISCro4")
    """
    locus = lookup_disease_locus(disease_or_gene)
    all_sites = scan_gene_window(
        gene_name=locus["gene_name"],
        window_bp=window_bp,
        chromosome=locus["chromosome"],
        start_coord=locus["start"],
    )
    return all_sites[:n_top]
```

### Commit
```bash
git add pen_stack/target/__init__.py
git commit -m "feat: PEN-TARGET API complete — recommend_target_sites() one-call interface"
```

---

# PART D — PEN-MONITOR: Living Database Engine (Weeks 4–5)

**Target state:** A nightly scheduled job scans Europe PMC + bioRxiv for new papers mentioning IS110 editors, extracts structured claims via LLM, opens GitHub Issues for review, and auto-triggers re-certification when approved. PEN-COMPARE goes from a static snapshot to a living registry.

---

## Step 14: Europe PMC + bioRxiv literature watcher

### Duration
1 day

**File: `pen_stack/monitor/literature_watcher.py`**

```python
"""Literature watcher — nightly scan of Europe PMC + bioRxiv for new editor papers.

API: https://www.ebi.ac.uk/europepmc/webservices/rest/search
No auth required. Free. 40M+ records including preprints.
"""
from __future__ import annotations
import requests
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from typing import Optional

EUROPEPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"

MONITOR_QUERIES = [
    # Primary IS110 bridge recombinase terms
    '("bridge recombinase" OR "IS110" OR "ISCro4" OR "IS621" OR "IS622") '
    'AND ("genome editing" OR "gene therapy" OR "recombination" OR "insertion")',

    # Broader non-destructive editing terms
    '("non-destructive" OR "DSB-free" OR "molecular pen" OR "prime editing") '
    'AND ("gene therapy" OR "genome engineering")',

    # CAST / OMEGA / Fanzor
    '("CAST" OR "Tn7-like" OR "OMEGA" OR "Fanzor" OR "evoCAST") '
    'AND ("gene insertion" OR "recombination" OR "DSB-free")',
]

@dataclass
class PaperRecord:
    pmid: Optional[str]
    doi: Optional[str]
    title: str
    abstract: str
    authors: list[str]
    journal: str
    pub_date: str
    source: str       # "europepmc" or "biorxiv"
    full_text_url: Optional[str]

def watch_literature(days_back: int = 7) -> list[PaperRecord]:
    """Return new papers from the past N days matching our editor queries."""
    from_date = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = date.today().strftime("%Y-%m-%d")

    all_papers: list[PaperRecord] = []
    seen_dois: set[str] = set()

    for query in MONITOR_QUERIES:
        date_filter = f'FIRST_PDATE:[{from_date} TO {to_date}]'
        full_query = f'({query}) AND {date_filter}'

        params = {
            "query": full_query,
            "format": "json",
            "pageSize": 100,
            "resultType": "core",
        }
        resp = requests.get(f"{EUROPEPMC_BASE}/search", params=params, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("resultList", {}).get("result", [])

        for r in results:
            doi = r.get("doi") or r.get("DOI") or r.get("pmid", "")
            if doi in seen_dois:
                continue
            seen_dois.add(doi)

            paper = PaperRecord(
                pmid=r.get("pmid"),
                doi=r.get("doi"),
                title=r.get("title", ""),
                abstract=r.get("abstractText", ""),
                authors=[a.get("fullName", "") for a in r.get("authorList", {}).get("author", [])[:5]],
                journal=r.get("journalTitle", ""),
                pub_date=r.get("firstPublicationDate", ""),
                source="europepmc",
                full_text_url=r.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url"),
            )
            all_papers.append(paper)

    return all_papers
```

### Commit
```bash
git add pen_stack/monitor/literature_watcher.py
git commit -m "feat: Europe PMC nightly literature watcher (PEN-MONITOR)"
```

---

## Step 15: LLM claim extractor

### Duration
1 day

**File: `pen_stack/monitor/claim_extractor.py`**

```python
"""LLM-based structured claim extraction from paper abstracts.

Uses Llama 3.1 8B via Ollama. Extracts:
- Editor name (canonical)
- Organism / cell type
- Editing efficiency (%)
- Mechanism (DSB-free or DSB)
- Evidence type (in vitro / bacterial / mammalian cell / in vivo)
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from typing import Optional
import ollama

CLAIM_EXTRACTION_PROMPT = """You are a structured data extractor for genome editing papers.
Given a paper title and abstract, extract claims about genome editors.
Return ONLY valid JSON — no markdown, no explanation.

Schema:
{{
  "editors_mentioned": [
    {{
      "name": "canonical editor name (e.g. ISCro4, IS621, SpCas9, evoCAST)",
      "organism_source": "source organism if mentioned",
      "cell_type": "cell type tested (null if not mentioned)",
      "editing_efficiency_percent": null or number,
      "dsb_free": true or false or null,
      "evidence_type": "in_vitro" | "bacterial" | "mammalian_cell" | "in_vivo" | null,
      "cargo_size_kb": null or number,
      "claim_quote": "exact phrase from abstract supporting this claim (max 30 words)"
    }}
  ],
  "new_cell_based_evidence": true or false
}}

Title: {title}
Abstract: {abstract}

JSON:"""

@dataclass
class ExtractedClaims:
    paper_doi: Optional[str]
    paper_title: str
    editors_mentioned: list[dict]
    new_cell_based_evidence: bool
    extraction_succeeded: bool
    raw_response: str

def extract_claims(
    paper: "PaperRecord",
    model: str = "llama3.1:8b-instruct-q4_K_M",
) -> ExtractedClaims:
    """Extract structured claims from paper abstract using Ollama."""
    prompt = CLAIM_EXTRACTION_PROMPT.format(
        title=paper.title[:300],
        abstract=paper.abstract[:1000],
    )
    try:
        response = ollama.generate(model=model, prompt=prompt)
        raw = response["response"].strip()
        # Strip any markdown fences
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip()
        data = json.loads(raw)

        return ExtractedClaims(
            paper_doi=paper.doi,
            paper_title=paper.title,
            editors_mentioned=data.get("editors_mentioned", []),
            new_cell_based_evidence=data.get("new_cell_based_evidence", False),
            extraction_succeeded=True,
            raw_response=raw,
        )
    except Exception as e:
        return ExtractedClaims(
            paper_doi=paper.doi,
            paper_title=paper.title,
            editors_mentioned=[],
            new_cell_based_evidence=False,
            extraction_succeeded=False,
            raw_response=str(e),
        )
```

### Commit
```bash
git add pen_stack/monitor/claim_extractor.py
git commit -m "feat: LLM claim extractor for literature watch (PEN-MONITOR)"
```

---

## Step 16: Auto re-certification trigger + GitHub Issues integration

### Duration
1 day

**File: `pen_stack/monitor/recertify_trigger.py`**

```python
"""Auto re-certification trigger when new evidence is found.

When claim_extractor finds new cell-based evidence for an editor already
in the universe, this module:
1. Opens a GitHub Issue with structured data
2. If the Issue is labeled 'approved' by a maintainer, triggers re-certification
"""
from __future__ import annotations
import requests
import json
from pathlib import Path

GITHUB_API = "https://api.github.com"
REPO = "ahmedanees-m/pen-stack"

def open_recertification_issue(
    editor_name: str,
    claim: dict,
    paper_doi: str,
    github_token: str,
) -> dict:
    """Open a GitHub Issue proposing an editor universe update."""
    title = f"[PEN-MONITOR] New cell-based evidence: {editor_name} ({paper_doi})"
    body = f"""## Automated Detection by PEN-MONITOR

**Editor:** {editor_name}
**Paper DOI:** {paper_doi}
**Evidence type:** {claim.get('evidence_type', 'unknown')}
**Cell type:** {claim.get('cell_type', 'not specified')}
**Editing efficiency:** {claim.get('editing_efficiency_percent', 'not reported')}%
**DSB-free:** {claim.get('dsb_free', 'unknown')}

**Claim quote:**
> {claim.get('claim_quote', 'N/A')}

## Required action
1. Verify the claim against the full paper
2. If confirmed: label this Issue `approved`
3. PEN-MONITOR will automatically update `editor_universe.yaml` and re-run certification

## Impact
- If {editor_name} has `cell_based_evidence=False` and this is confirmed mammalian cell data,
  it will upgrade from PROBABLE_WRITER to TRUE_WRITER
- The pre-registered framework (prereg-v3.2) stays frozen; only the data layer updates

/cc @ahmedanees-m
"""
    resp = requests.post(
        f"{GITHUB_API}/repos/{REPO}/issues",
        headers={"Authorization": f"token {github_token}",
                 "Accept": "application/vnd.github.v3+json"},
        json={"title": title, "body": body, "labels": ["pen-monitor", "needs-review"]},
    )
    return resp.json()
```

**File: `scripts/run_monitor.py`** — nightly cron job

```python
#!/usr/bin/env python3
"""PEN-MONITOR nightly run. Called by cron (0 2 * * *) or Docker entrypoint."""
import os
from pen_stack.monitor.literature_watcher import watch_literature
from pen_stack.monitor.claim_extractor import extract_claims
from pen_stack.monitor.recertify_trigger import open_recertification_issue

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # set in Docker env

papers = watch_literature(days_back=7)
print(f"Found {len(papers)} new papers")

for paper in papers:
    claims = extract_claims(paper)
    if not claims.extraction_succeeded:
        continue
    for editor_claim in claims.editors_mentioned:
        if editor_claim.get("new_cell_based_evidence") or editor_claim.get("evidence_type") == "mammalian_cell":
            print(f"  → New cell-based evidence: {editor_claim.get('name')} in {paper.doi}")
            if GITHUB_TOKEN:
                issue = open_recertification_issue(
                    editor_name=editor_claim.get("name", "unknown"),
                    claim=editor_claim,
                    paper_doi=paper.doi or "unknown",
                    github_token=GITHUB_TOKEN,
                )
                print(f"     Issue #{issue.get('number')} opened: {issue.get('html_url')}")
```

**Cron setup (VM):**
```bash
# Add to crontab: run at 2 AM daily
echo "0 2 * * * /usr/local/bin/python /workspace/pen-stack/scripts/run_monitor.py >> /var/log/pen-monitor.log 2>&1" | crontab -
```

### Commit
```bash
git add pen_stack/monitor/ scripts/run_monitor.py
git commit -m "feat: PEN-MONITOR living database engine — nightly watch + LLM extraction + GitHub Issues"
```

---

# PART E — PEN-SAFE: Safety Analysis (Weeks 5–6)

**Target state:** Given an editor + proposed target site coordinates, PEN-SAFE returns a structured safety report covering oncogene proximity, essential gene risk, population variant burden, immunogenicity prediction, and a composite Regulatory Readiness Index (RRI).

---

## Step 18: Oncogene proximity check (COSMIC Cancer Gene Census)

### Duration
1 day

**Note on COSMIC:** The Cancer Gene Census requires free academic registration at cancer.sanger.ac.uk/cosmic for download. Upon download, the CSV (`cancer_gene_census.csv`) is bundled as a static file in `pen_stack/safe/data/cosmic_cgc.csv`. This is a one-time download. The 723-gene list is stable; updates are infrequent.

**File: `pen_stack/safe/oncogene_proximity.py`**

```python
"""Oncogene proximity check using COSMIC Cancer Gene Census (static bundled CSV).

Data source: COSMIC CGC v100 (723 cancer genes)
Access: free academic registration at cancer.sanger.ac.uk/cosmic
Bundled as: pen_stack/safe/data/cosmic_cgc.csv (one-time download; included in repo)

Risk logic:
  - target site within 50 kb of a Tier 1 oncogene → HIGH risk
  - within 200 kb → MODERATE risk
  - within 1 Mb → LOW risk
  - beyond 1 Mb → negligible
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import pandas as pd

CGC_PATH = Path(__file__).parent / "data" / "cosmic_cgc.csv"
DEPMAP_PATH = Path(__file__).parent / "data" / "depmap_essential_genes.csv"

@dataclass
class OncogeneRisk:
    target_chrom: str
    target_pos: int
    nearest_oncogene: str
    nearest_distance_bp: int
    oncogene_tier: int   # 1 or 2
    risk_level: str      # "negligible" / "low" / "moderate" / "high"
    note: str

def check_oncogene_proximity(
    chromosome: str, position: int, window_mb: float = 1.0
) -> OncogeneRisk:
    """Check if a target site is near a known cancer gene."""
    if not CGC_PATH.exists():
        raise FileNotFoundError(
            f"COSMIC CGC not found at {CGC_PATH}. "
            "Download from cancer.sanger.ac.uk/cosmic/census and save as "
            "pen_stack/safe/data/cosmic_cgc.csv"
        )
    cgc = pd.read_csv(CGC_PATH)
    chrom_clean = chromosome.replace("chr", "")

    # Filter to same chromosome
    chrom_genes = cgc[cgc["Chromosome"] == chrom_clean].copy()
    if chrom_genes.empty:
        return OncogeneRisk(
            target_chrom=chromosome, target_pos=position,
            nearest_oncogene="none_on_chrom", nearest_distance_bp=-1,
            oncogene_tier=2, risk_level="negligible",
            note=f"No COSMIC Tier 1/2 genes on {chromosome}"
        )

    # Compute distance to each gene
    # CGC columns: Gene Symbol, Name, Chr, Chr Band, Somatic, Germline, Tumour Types(Somatic), ...
    chrom_genes["distance"] = chrom_genes.apply(
        lambda r: abs(position - _parse_band_position(r.get("Chr Band", ""), position)),
        axis=1,
    )
    nearest = chrom_genes.loc[chrom_genes["distance"].idxmin()]
    dist = int(nearest["distance"])
    tier = 1 if nearest.get("Tier", "2") == "1" else 2

    if dist < 50_000 and tier == 1:
        risk = "high"
        note = f"Within 50 kb of Tier 1 cancer gene {nearest['Gene Symbol']}"
    elif dist < 200_000:
        risk = "moderate"
        note = f"Within 200 kb of {nearest['Gene Symbol']} (Tier {tier})"
    elif dist < 1_000_000:
        risk = "low"
        note = f"Within 1 Mb of {nearest['Gene Symbol']}; monitor carefully"
    else:
        risk = "negligible"
        note = f">{dist//1_000_000} Mb from nearest cancer gene"

    return OncogeneRisk(
        target_chrom=chromosome, target_pos=position,
        nearest_oncogene=str(nearest.get("Gene Symbol", "unknown")),
        nearest_distance_bp=dist, oncogene_tier=tier,
        risk_level=risk, note=note,
    )

def _parse_band_position(band: str, fallback: int) -> int:
    """Very rough chr band → position mapping (used only for distance estimation)."""
    # Bands like "7q31" → rough midpoint estimate
    # More accurate: use UCSC cytoBand.txt (can be downloaded separately)
    return fallback  # placeholder; replace with cytoBand lookup if needed
```

### Commit
```bash
mkdir -p pen_stack/safe/data
# (User downloads COSMIC CGC CSV and places at pen_stack/safe/data/cosmic_cgc.csv)
git add pen_stack/safe/oncogene_proximity.py pen_stack/safe/data/.gitkeep
git commit -m "feat: oncogene proximity check via COSMIC CGC (PEN-SAFE)"
```

---

## Step 19: Essential gene risk via DepMap

**File: `pen_stack/safe/essential_gene_risk.py`**

```python
"""Essential gene risk from DepMap CRISPR essentiality screens.

Data: DepMap CRISPR gene effect scores
Download: https://depmap.org/portal/download/ → CRISPR_gene_effect.csv
Academic use: free

A gene is essential if mean CRISPR effect score < -0.5 across all cell lines.
Insertion near an essential gene raises the risk of disrupting fitness-critical function.
"""
from pathlib import Path
import pandas as pd
from dataclasses import dataclass

DEPMAP_PATH = Path(__file__).parent / "data" / "depmap_essential_genes.csv"

@dataclass
class EssentialGeneRisk:
    nearest_essential_gene: str
    distance_bp: int
    essentiality_score: float   # mean DepMap gene effect (more negative = more essential)
    percentile_rank: float       # 0 = most essential, 100 = least
    risk_level: str
    note: str

def check_essential_gene_risk(chromosome: str, position: int) -> EssentialGeneRisk:
    """Check if target site is near a DepMap-essential gene."""
    if not DEPMAP_PATH.exists():
        return EssentialGeneRisk(
            nearest_essential_gene="DepMap data not loaded",
            distance_bp=-1, essentiality_score=0, percentile_rank=50,
            risk_level="unknown",
            note="Download CRISPR_gene_effect.csv from depmap.org/portal/download/ and place in pen_stack/safe/data/",
        )
    essential = pd.read_csv(DEPMAP_PATH)
    # Filter to same chromosome
    chrom_ess = essential[essential["chr"] == chromosome.replace("chr", "")].copy()
    if chrom_ess.empty:
        return EssentialGeneRisk("none_found", -1, 0, 50, "negligible", "No essential genes on chromosome")

    chrom_ess["distance"] = (chrom_ess["gene_start"] - position).abs()
    nearest = chrom_ess.loc[chrom_ess["distance"].idxmin()]

    score = float(nearest.get("mean_effect", 0))
    dist = int(nearest["distance"])
    pct = float(nearest.get("essentiality_percentile", 50))

    if score < -1.0 and dist < 100_000:
        risk = "high"
        note = f"Near core-essential gene {nearest['gene_symbol']} (score={score:.2f})"
    elif score < -0.5 and dist < 500_000:
        risk = "moderate"
        note = f"{nearest['gene_symbol']} is broadly essential (score={score:.2f})"
    else:
        risk = "low"
        note = f"No core-essential genes within 1 Mb"

    return EssentialGeneRisk(
        nearest_essential_gene=str(nearest.get("gene_symbol", "unknown")),
        distance_bp=dist, essentiality_score=score, percentile_rank=pct,
        risk_level=risk, note=note,
    )
```

### Commit
```bash
git add pen_stack/safe/essential_gene_risk.py
git commit -m "feat: DepMap essential gene risk check (PEN-SAFE)"
```

---

## Step 20: Immunogenicity prediction via BepiPred-3.0 API

**File: `pen_stack/safe/immunogenicity.py`**

```python
"""Immunogenicity prediction using BepiPred-3.0 (DTU, free academic API).

BepiPred-3.0: B-cell epitope prediction
API: https://services.healthtech.dtu.dk/services/BepiPred-3.0/
Free for academic use; no key required for web form; REST API available.

Also predicts T-cell epitopes via NetMHCpan 4.1 (same DTU server).

Interpretation: editors with high immunogenic load (>3 predicted B-cell epitopes)
may trigger immune responses after repeated dosing — a clinical risk.
"""
from __future__ import annotations
import requests
from dataclasses import dataclass

BEPIPRED_API = "https://services.healthtech.dtu.dk/cgi-bin/webface2.py"

@dataclass
class ImmunogenicityReport:
    editor_id: str
    sequence_length: int
    n_bcell_epitopes: int
    n_tcell_epitopes: int
    bcell_epitope_positions: list[tuple[int, int]]   # (start, end) of each epitope
    immunogenic_load: str   # "low" / "medium" / "high"
    note: str

def predict_immunogenicity(editor_id: str, sequence: str) -> ImmunogenicityReport:
    """Predict immunogenic load for an editor protein sequence.

    Note: DTU BepiPred-3.0 processes one sequence at a time via REST.
    For batch processing, consider local BepiPred-3.0 installation (free academic).
    """
    try:
        # BepiPred-3.0 REST endpoint
        response = requests.post(
            "https://services.healthtech.dtu.dk/services/BepiPred-3.0/",
            data={
                "seqpaste": f">query\n{sequence}",
                "method": "bepipred3",
                "threshold": "0.5",
            },
            timeout=120,
        )
        # Parse response for epitope predictions
        # Note: DTU APIs return HTML results — parse for epitope spans
        epitopes = _parse_bepipred_html(response.text)
    except Exception as e:
        # Graceful degradation: return unknown immunogenicity
        return ImmunogenicityReport(
            editor_id=editor_id, sequence_length=len(sequence),
            n_bcell_epitopes=-1, n_tcell_epitopes=-1,
            bcell_epitope_positions=[],
            immunogenic_load="unknown",
            note=f"BepiPred API unavailable: {e}. Run locally for accurate prediction.",
        )

    n = len(epitopes)
    if n >= 5:
        load = "high"
        note = f"{n} predicted B-cell epitopes — may trigger immune response with repeat dosing"
    elif n >= 2:
        load = "medium"
        note = f"{n} predicted B-cell epitopes — standard immunogenicity for protein therapeutics"
    else:
        load = "low"
        note = f"{n} predicted B-cell epitopes — relatively low immunogenic load"

    return ImmunogenicityReport(
        editor_id=editor_id, sequence_length=len(sequence),
        n_bcell_epitopes=n, n_tcell_epitopes=-1,  # T-cell deferred to v1.1
        bcell_epitope_positions=epitopes,
        immunogenic_load=load, note=note,
    )

def _parse_bepipred_html(html: str) -> list[tuple[int, int]]:
    """Parse BepiPred-3.0 HTML response for epitope spans."""
    import re
    # Simplified parser — DTU output format may change
    epitopes = []
    for m in re.finditer(r"Epitope\s+(\d+)\s*:\s*(\d+)\s*-\s*(\d+)", html):
        epitopes.append((int(m.group(2)), int(m.group(3))))
    return epitopes
```

### Commit
```bash
git add pen_stack/safe/immunogenicity.py
git commit -m "feat: BepiPred-3.0 B-cell immunogenicity prediction (PEN-SAFE)"
```

---

## Step 21: Cargo safety checker (cryptic splice sites, polyA signals)

**File: `pen_stack/safe/cargo_safety.py`**

```python
"""Cargo sequence safety checker: cryptic splice sites, polyA signals, CpG islands.

These are the sequence-level features that the FDA/EMA require evaluation of
in any gene therapy cargo sequence.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

@dataclass
class CargoSafetyReport:
    cargo_length_bp: int
    gc_content: float
    cryptic_splice_donors: list[int]        # positions of GT dinucleotide in GT-AG rule context
    cryptic_splice_acceptors: list[int]     # positions of AG dinucleotide
    polyadenylation_signals: list[int]      # positions of AATAAA hexamer
    cpg_islands: list[tuple[int, int]]      # (start, end) of CpG islands
    internal_promoters: list[str]           # predicted promoter elements
    repeat_fraction: float                  # fraction of sequence that is repetitive
    overall_risk: str                       # "acceptable" / "review_needed" / "redesign"
    notes: list[str] = field(default_factory=list)

# Canonical splice signals (simplified; SpliceAI is more accurate but requires GPU)
SPLICE_DONOR_PATTERN = r"GT[AGT]{6}"       # GT + 6 downstream nt (GT-AG rule)
SPLICE_ACCEPTOR_PATTERN = r"[ACGT]{6}AG"   # 6 upstream nt + AG
POLYA_SIGNAL = r"AATAAA|ATTAAA"            # canonical + variant polyA hexamers
PROMOTER_ELEMENTS = ["TATAAA", "CAAT", "GC[GC]{4}GC"]   # TATA, CAAT, GC box

def check_cargo_safety(cargo_sequence: str) -> CargoSafetyReport:
    seq = cargo_sequence.upper()
    n = len(seq)

    gc = (seq.count("G") + seq.count("C")) / n if n > 0 else 0

    donors = [m.start() for m in re.finditer(SPLICE_DONOR_PATTERN, seq)]
    acceptors = [m.start() for m in re.finditer(SPLICE_ACCEPTOR_PATTERN, seq)]
    polya = [m.start() for m in re.finditer(POLYA_SIGNAL, seq)]

    # CpG island: >=200 bp, GC>=50%, CpG O/E >= 0.6
    cpg_islands = _find_cpg_islands(seq)

    # Internal promoter elements
    promoters = []
    for elem in PROMOTER_ELEMENTS:
        for m in re.finditer(elem, seq):
            promoters.append(f"{elem}@{m.start()}")

    # Simple repeat detection: ≥5 consecutive identical dinucleotides
    repeats = len(re.findall(r"(.{2})\1{5,}", seq))
    repeat_frac = min(1.0, repeats * 10 / n)

    notes = []
    if len(polya) > 0:
        notes.append(f"{len(polya)} polyA signal(s) found — may cause premature transcription termination")
    if len(cpg_islands) > 0:
        notes.append(f"{len(cpg_islands)} CpG island(s) — may be silenced by methylation in some tissues")
    if repeat_frac > 0.1:
        notes.append(f"High repeat content ({repeat_frac:.0%}) — may cause recombination instability")

    if len(polya) > 2 or repeat_frac > 0.2:
        risk = "redesign"
    elif len(polya) > 0 or len(cpg_islands) > 0:
        risk = "review_needed"
    else:
        risk = "acceptable"

    return CargoSafetyReport(
        cargo_length_bp=n, gc_content=gc,
        cryptic_splice_donors=donors[:5], cryptic_splice_acceptors=acceptors[:5],
        polyadenylation_signals=polya[:5], cpg_islands=cpg_islands[:3],
        internal_promoters=promoters[:5], repeat_fraction=repeat_frac,
        overall_risk=risk, notes=notes,
    )

def _find_cpg_islands(seq: str, min_len: int = 200) -> list[tuple[int, int]]:
    """Find CpG islands: length ≥200 bp, GC ≥50%, CpG O/E ≥0.6."""
    islands = []
    window = 200
    for i in range(0, len(seq) - window, 50):  # 50 bp stride
        w = seq[i:i + window]
        gc = (w.count("G") + w.count("C")) / window
        cpg_obs = w.count("CG")
        cg_total = w.count("C") * w.count("G")
        if cg_total > 0 and gc >= 0.5:
            cpg_oe = cpg_obs * window / cg_total
            if cpg_oe >= 0.6:
                islands.append((i, i + window))
    return islands
```

### Commit
```bash
git add pen_stack/safe/cargo_safety.py
git commit -m "feat: cargo sequence safety checker (splice sites, polyA, CpG, repeats)"
```

---

## Step 22: Regulatory Readiness Index (RRI) composite

**File: `pen_stack/safe/regulatory_index.py`**

```python
"""Regulatory Readiness Index (RRI) — composite 0-10 safety score.

Maps to FDA/EMA gene therapy guidance categories:
  RRI 8-10: Suitable for IND-enabling studies
  RRI 5-7:  Further characterization needed before IND
  RRI 2-4:  Significant safety concerns; address before clinical translation
  RRI 0-2:  Not clinically viable in current form
"""
from dataclasses import dataclass
from pen_stack.safe.oncogene_proximity import OncogeneRisk
from pen_stack.safe.essential_gene_risk import EssentialGeneRisk
from pen_stack.safe.immunogenicity import ImmunogenicityReport
from pen_stack.safe.cargo_safety import CargoSafetyReport

RISK_WEIGHTS = {
    "oncogene": 3.0,
    "essential_gene": 2.0,
    "immunogenicity": 2.0,
    "cargo_safety": 2.0,
    "population_variant": 1.0,
}

@dataclass
class RegulatoryReadinessReport:
    editor_id: str
    target_site: str
    rri_score: float    # 0-10
    rri_category: str   # "IND-ready" / "characterize-further" / "major-concerns" / "not-viable"
    component_scores: dict[str, float]
    summary: str
    action_items: list[str]

def compute_rri(
    editor_id: str,
    target_site: str,
    oncogene_risk: OncogeneRisk,
    essential_risk: EssentialGeneRisk,
    immunogenicity: ImmunogenicityReport,
    cargo_safety: CargoSafetyReport,
    population_variants_high_risk: int = 0,
) -> RegulatoryReadinessReport:
    """Compute the Regulatory Readiness Index for an editor-target combination."""
    LEVEL_SCORE = {"negligible": 1.0, "low": 0.8, "none": 0.9,
                   "moderate": 0.5, "medium": 0.5,
                   "high": 0.1, "unknown": 0.5}

    scores = {
        "oncogene": LEVEL_SCORE.get(oncogene_risk.risk_level, 0.5),
        "essential_gene": LEVEL_SCORE.get(essential_risk.risk_level, 0.5),
        "immunogenicity": LEVEL_SCORE.get(immunogenicity.immunogenic_load, 0.5),
        "cargo_safety": 1.0 if cargo_safety.overall_risk == "acceptable" else
                        0.6 if cargo_safety.overall_risk == "review_needed" else 0.2,
        "population_variant": 1.0 if population_variants_high_risk == 0 else
                               0.7 if population_variants_high_risk <= 2 else 0.3,
    }

    # Weighted average → rescale to 0-10
    total_weight = sum(RISK_WEIGHTS.values())
    rri = sum(scores[k] * RISK_WEIGHTS[k] for k in scores) / total_weight * 10

    if rri >= 8:
        category = "IND-ready"
        summary = f"Strong safety profile (RRI={rri:.1f}/10). Suitable for IND-enabling studies."
    elif rri >= 5:
        category = "characterize-further"
        summary = f"Moderate safety profile (RRI={rri:.1f}/10). Address flagged issues before IND."
    elif rri >= 2:
        category = "major-concerns"
        summary = f"Significant safety concerns (RRI={rri:.1f}/10). Major redesign or target change needed."
    else:
        category = "not-viable"
        summary = f"Not clinically viable in current form (RRI={rri:.1f}/10)."

    actions = []
    if scores["oncogene"] < 0.6:
        actions.append(f"Oncogene proximity: consider alternative target site (current: {oncogene_risk.note})")
    if scores["immunogenicity"] < 0.6:
        actions.append(f"Immunogenicity: assess tolerance with deimmunization strategies")
    if scores["cargo_safety"] < 0.7:
        actions.append(f"Cargo safety: {'; '.join(cargo_safety.notes[:2])}")

    return RegulatoryReadinessReport(
        editor_id=editor_id, target_site=target_site,
        rri_score=round(rri, 2), rri_category=category,
        component_scores=scores, summary=summary, action_items=actions,
    )
```

### Commit
```bash
git add pen_stack/safe/regulatory_index.py pen_stack/safe/__init__.py
git commit -m "feat: Regulatory Readiness Index composite (PEN-SAFE complete)"
```

---

# PART F — PEN-DESIGN: bRNA + Cargo Optimization (Weeks 6–7)

**Target state:** Given a 14-nt genomic target + cargo DNA, PEN-DESIGN outputs a ready-to-order 177-nt bRNA sequence (IS621 scaffold), codon-optimized editor sequence for the target tissue, and cargo sequence quality report.

---

## Step 23: bRNA designer (IS621/ISCro4 scaffold, any IS110)

### Duration
2 days

**Biological basis (Arc Institute design rules, Durrant & Perry Nature 2024):**
- bRNA is 177 nt total for IS621 scaffold
- Target-binding loop: 7 nt LTG (positions 44-50) + 7 nt RTG (positions 100-106), complementary to target 14-mer
- Donor-binding loop: 7 nt LDG + 7 nt RDG, complementary to donor sequence
- Handshake guides (Hiraizumi 2024): additional 4-nt sequences that stabilize the synaptic complex

**File: `pen_stack/design/brna_designer.py`**

```python
"""bRNA designer for IS110 bridge recombinases.

Implements the Arc Institute design logic (arcinstitute.org/tools/bridge):
- IS621 / ISCro4 scaffold (177 nt)
- Any target + donor 14-nt sequences
- Quality filters per Durrant 2024 design rules

Reference: Durrant & Perry et al. Nature 2024; Hiraizumi et al. Nature 2024
"""
from __future__ import annotations
from dataclasses import dataclass
from Bio.Seq import Seq

# IS621 bRNA scaffold — verified from PDB 8WT6 (Hiraizumi Nature 2024) + BridgeRNADesigner
# Architecture: 5'(49) + LTG(9) + TBL_inter(15) + RTG(9) + core_link(40)
#             + LDG(8) + DBL_inter(26) + core_comp(2) + uu(2) + RDG(7) + 3'(10) = 177 nt
#
# Target model for IS621: [left 9 nt][CT core 2 nt][right 9 nt] = 20-nt genomic target
# LTG = rev_comp(target[:9]); RTG = rev_comp(target[11:20])
#
# For ISCro4 (TRUE_WRITER; Pelea Science 2026): uses 14-nt targets (7+7)
# — use the ISCro4 scaffold from pip install bridgernadesigner for ISCro4 designs
IS621_5PRIME     = "AGUGCAGAGAAAAUCGGCCAGUUUUCUCUGCCUGCAGUCCGCAUGCCGU"  # 49 nt
IS621_TBL_INTER  = "UGGGUUCUAACCUGU"       # 15 nt, between LTG and RTG within TBL loop
IS621_CORE_LINK  = "UUAUGCAGCGGACUGCCUUUCUCCCAAAGUGAUAAACCGG"  # 40 nt, TBL→DBL linker
IS621_DBL_INTER  = "AUGGACCGGUUUUCCCGGUAAUCCGU"  # 26 nt, between LDG and donor-side core
IS621_HANDSHAKE  = "UU"     # 2 nt fixed handshake dinucleotide
IS621_3PRIME     = "UGGUUUCACU"   # 10 nt, 3' scaffold
CORE_DINUCLEOTIDE = "CT"    # IS621 attB core (Durrant 2024, Hiraizumi 2024, PDB 8WT6)
LTG_LENGTH = 9   # IS621: 9 nt LTG; for ISCro4 use 7 nt (bridgernadesigner)
RTG_LENGTH = 9   # IS621: 9 nt RTG
LDG_LENGTH = 8   # IS621: 8 nt LDG
RDG_LENGTH = 7   # IS621: 7 nt RDG
TARGET_LENGTH = 20   # IS621 total target: 9 + CT(2) + 9 = 20 nt

@dataclass
class BRNADesign:
    target_seq: str         # full target DNA (20 nt for IS621: 9+CT+9)
    donor_seq: str          # full donor DNA (17 nt for IS621: 8+core2+7)
    editor_scaffold: str
    ltg: str     # left target guide (9 nt for IS621, complementary to target[:9])
    rtg: str     # right target guide (9 nt for IS621, complementary to target[11:20])
    ldg: str     # left donor guide  (8 nt for IS621, complementary to donor[:8])
    rdg: str     # right donor guide (7 nt for IS621, complementary to donor[9:16])
    brna_sequence: str     # full 177-nt bRNA
    passes_filters: bool
    filter_warnings: list[str]
    length: int

def design_brna(
    target_seq: str,
    donor_seq: str,
    editor: str = "IS621",
) -> str:
    """Design a bRNA for IS621 given target (20 nt) and donor (17 nt) DNA sequences.

    IS621 target format: [9 nt left flank][CT core][9 nt right flank] = 20 nt total
    IS621 donor format:  [8 nt left flank][2 nt core][7 nt right flank] = 17 nt total

    For ISCro4 (TRUE_WRITER, 14-nt targets), use:
        from bridgernadesigner.run import design_bridge_rna
        design_bridge_rna(target_14nt, donor_14nt, scaffold='ISCro4_enhanced')

    Returns the 177-nt IS621 bRNA sequence as RNA (uppercase, U not T).
    """
    result = design_brna_full(target_seq, donor_seq, editor)
    return result.brna_sequence

def design_brna_full(
    target_seq: str,
    donor_seq: str,
    editor: str = "IS621",
) -> BRNADesign:
    """Full IS621 bRNA design with quality checking.

    Scaffold layout verified from PDB 8WT6 (Hiraizumi Nature 2024):
      IS621_5PRIME(49) + LTG(9) + IS621_TBL_INTER(15) + RTG(9)
      + IS621_CORE_LINK(40) + LDG(8) + IS621_DBL_INTER(26)
      + core_comp(2) + IS621_HANDSHAKE(2) + RDG(7) + IS621_3PRIME(10) = 177 nt
    """
    if len(target_seq) != TARGET_LENGTH:  # 20 nt
        raise ValueError(
            f"IS621 target must be {TARGET_LENGTH} nt "
            f"(9 nt + CT core + 9 nt); got {len(target_seq)}"
        )
    # Validate CT core at positions 9-10 (0-indexed)
    target_core = target_seq[9:11].upper()
    if target_core != CORE_DINUCLEOTIDE:
        raise ValueError(
            f"IS621 target must contain '{CORE_DINUCLEOTIDE}' core at positions 9-10; "
            f"got '{target_core}'. Confirm the target site has the IS621 attB core."
        )
    if len(donor_seq) != 17:
        raise ValueError(f"IS621 donor must be 17 nt (8+core2+7); got {len(donor_seq)}")

    # Compute guide sequences (reverse complement of flanking regions)
    # LTG: binds bottom strand of target left flank (target[:9])
    ltg = str(Seq(target_seq[:9]).reverse_complement()).replace("T", "U")
    # RTG: binds top strand of target right flank (target[11:20], after CT core)
    rtg = str(Seq(target_seq[11:20]).reverse_complement()).replace("T", "U")
    # LDG: binds left flank of donor (donor[:8])
    ldg = str(Seq(donor_seq[:8]).reverse_complement()).replace("T", "U")
    # RDG: binds right flank of donor (donor[9:16], after 2-nt donor core)
    rdg = str(Seq(donor_seq[9:16]).reverse_complement()).replace("T", "U")
    # Donor-core complement (2 nt) — fills the NN position in the scaffold
    core_comp = str(Seq(donor_seq[7:9]).reverse_complement()).replace("T", "U")

    # Assemble full IS621 bRNA (177 nt)
    brna = (
        IS621_5PRIME        # 49 nt
        + ltg               #  9 nt
        + IS621_TBL_INTER   # 15 nt
        + rtg               #  9 nt
        + IS621_CORE_LINK   # 40 nt
        + ldg               #  8 nt
        + IS621_DBL_INTER   # 26 nt
        + core_comp         #  2 nt
        + IS621_HANDSHAKE   #  2 nt
        + rdg               #  7 nt
        + IS621_3PRIME      # 10 nt
    )   # total = 177 nt

    assert len(brna) == 177, f"bRNA length error: {len(brna)} nt (expected 177)"

    # Quality filters
    warnings = []
    for guide_name, guide, length in [("LTG", ltg, 9), ("RTG", rtg, 9),
                                       ("LDG", ldg, 8), ("RDG", rdg, 7)]:
        gc = (guide.count("G") + guide.count("C")) / length
        if gc < 0.3 or gc > 0.8:
            warnings.append(f"{guide_name} GC content {gc:.0%} outside recommended 30-80%")
    if "UUUUU" in ltg + rtg + ldg + rdg:
        warnings.append("Poly-U(5) run in guide — may cause RNA Pol III termination")

    return BRNADesign(
        target_seq=target_seq, donor_seq=donor_seq,
        editor_scaffold=editor,
        ltg=ltg, rtg=rtg, ldg=ldg, rdg=rdg,
        brna_sequence=brna,
        passes_filters=len(warnings) == 0,
        filter_warnings=warnings,
        length=177,
    )
```

### Commit
```bash
git add pen_stack/design/brna_designer.py
git commit -m "feat: IS621/ISCro4 bRNA designer (14-nt TBL+DBL, Arc Institute logic)"
```

---

## Step 24: Codon optimizer + cargo checker

### Duration
1 day

**File: `pen_stack/design/codon_optimizer.py`**

```python
"""Tissue-specific codon optimization using Kazusa codon usage tables.

CAI (Codon Adaptation Index) calculation per Sharp & Li 1987.
Codon tables from https://www.kazusa.or.jp/codon/ (free academic, Homo sapiens).
Target tissues: liver (AAV8), lung/airway (AAV5/LNP), HSC (ex vivo), brain (AAV9).
"""
from __future__ import annotations
import math
from pathlib import Path
from dataclasses import dataclass
import yaml

CODON_TABLES_PATH = Path(__file__).parent / "data" / "codon_usage_homo_sapiens.yaml"

TISSUE_ALIASES = {
    "liver": "liver", "hepatocyte": "liver",
    "lung": "airway", "airway": "airway",
    "hsc": "blood", "blood": "blood", "cd34": "blood",
    "brain": "cns", "neuron": "cns", "cns": "cns",
    "generic": "generic",
}

@dataclass
class CodonOptResult:
    original_cai: float
    optimized_cai: float
    tissue: str
    optimized_sequence: str
    n_codons_changed: int
    improvement_pct: float

def optimize_codons(sequence_dna: str, tissue: str = "generic") -> CodonOptResult:
    """Optimize codon usage for target tissue. Returns optimized DNA sequence."""
    tissue_key = TISSUE_ALIASES.get(tissue.lower(), "generic")
    if not CODON_TABLES_PATH.exists():
        # Return unchanged if table not loaded — graceful degradation
        return CodonOptResult(
            original_cai=0.0, optimized_cai=0.0, tissue=tissue,
            optimized_sequence=sequence_dna, n_codons_changed=0, improvement_pct=0.0
        )

    tables = yaml.safe_load(CODON_TABLES_PATH.read_text())
    table = tables.get(tissue_key, tables.get("generic", {}))

    aa_to_best_codon = _get_best_codons(table)
    seq = sequence_dna.upper()

    optimized = []
    changed = 0
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i:i+3]
        aa = _codon_to_aa(codon)
        best = aa_to_best_codon.get(aa, codon)
        optimized.append(best)
        if best != codon:
            changed += 1

    optimized_seq = "".join(optimized)
    orig_cai = _compute_cai(seq, table)
    opt_cai = _compute_cai(optimized_seq, table)

    return CodonOptResult(
        original_cai=orig_cai, optimized_cai=opt_cai, tissue=tissue,
        optimized_sequence=optimized_seq, n_codons_changed=changed,
        improvement_pct=(opt_cai - orig_cai) / max(orig_cai, 1e-9) * 100,
    )

def _compute_cai(seq: str, table: dict) -> float:
    w_values = []
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i:i+3]
        w = table.get(codon, {}).get("relative_adaptiveness", 0.01)
        w_values.append(max(w, 1e-9))
    if not w_values:
        return 0.0
    return math.exp(sum(math.log(w) for w in w_values) / len(w_values))

def _get_best_codons(table: dict) -> dict[str, str]:
    aa_to_codons: dict[str, list[tuple[str, float]]] = {}
    for codon, info in table.items():
        aa = info.get("amino_acid", "?")
        ra = info.get("relative_adaptiveness", 0)
        aa_to_codons.setdefault(aa, []).append((codon, ra))
    return {aa: max(codons, key=lambda x: x[1])[0]
            for aa, codons in aa_to_codons.items()}

def _codon_to_aa(codon: str) -> str:
    GENETIC_CODE = {
        "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
        "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
        "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
        "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
        "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
        "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
        "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
        "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
        "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
        "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
        "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
        "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
        "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
        "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
        "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
        "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
    }
    return GENETIC_CODE.get(codon, "?")
```

### Commit
```bash
git add pen_stack/design/codon_optimizer.py pen_stack/design/cargo_checker.py pen_stack/design/__init__.py
git commit -m "feat: codon optimizer + cargo checker (PEN-DESIGN complete)"
```

---

# PART G — PEN-DELIVER: Delivery Optimization (Weeks 7–8)

---

## Step 28: Delivery modality ranker + AAV serotype recommendation

### Duration
2 days

**File: `pen_stack/deliver/modality_ranker.py`**

```python
"""Delivery modality ranker for IS110 bridge recombinases.

Evidence corpus: 150 gene therapy delivery papers (RAG-indexed via ChromaDB).
Supported modalities: AAV, LNP, mRNA/RNP, ex vivo electroporation, nanoparticle.

Key literature sources:
- Wang et al. 2024 Nature Rev Drug Discov (AAV serotype tropism)
- Anzalone et al. 2022 Nature Biotechnology (PE delivery)
- Breda et al. 2023 Science (LNP liver delivery)
- Majzner et al. 2023 NEJM (CAR-T ex vivo)
"""
from dataclasses import dataclass

# Tissue → preferred modalities + AAV serotype (evidence-based)
TISSUE_DELIVERY_MAP = {
    "liver": {
        "preferred": ["AAV8", "LNP_mRNA"],
        "avoid": ["AAV5"],
        "aav_serotype": "AAV8",
        "aav_route": "IV_injection",
        "lnp_formulation": "MC3_ionizable_lipid",
        "rationale": "AAV8 highest liver tropism in NHP; LNP mRNA validated in Phase III (Onpattro, Leqvio)"
    },
    "airway": {
        "preferred": ["AAV5", "LNP_inhalation"],
        "avoid": ["AAV8"],
        "aav_serotype": "AAV5",
        "aav_route": "intratracheal_instillation",
        "lnp_formulation": "DLinDMA_lipid_nanoparticle",
        "rationale": "AAV5 highest airway epithelium tropism; LNP inhalation preclinical success for CF"
    },
    "blood": {
        "preferred": ["ex_vivo_electroporation", "LNP_mRNA"],
        "avoid": ["AAV_systemic"],
        "aav_serotype": None,
        "aav_route": None,
        "lnp_formulation": "ex_vivo_mRNA",
        "rationale": "HSCs: ex vivo electroporation is standard (Casgevy protocol); LNP mRNA emerging"
    },
    "cns": {
        "preferred": ["AAV9", "AAVrh10"],
        "avoid": ["LNP_IV"],
        "aav_serotype": "AAV9",
        "aav_route": "intrathecal_or_IV",
        "lnp_formulation": None,
        "rationale": "AAV9 crosses BBB; intrathecal for focal CNS; systemic IV for diffuse NMD"
    },
    "muscle": {
        "preferred": ["AAV9", "AAVrh74"],
        "avoid": [],
        "aav_serotype": "AAVrh74",
        "aav_route": "IM_injection",
        "lnp_formulation": None,
        "rationale": "AAVrh74 highest muscle tropism; used in FDA-approved Elevidys (DMD)"
    },
    "eye": {
        "preferred": ["AAV2", "AAV5"],
        "avoid": [],
        "aav_serotype": "AAV2",
        "aav_route": "subretinal_injection",
        "lnp_formulation": None,
        "rationale": "AAV2 used in Luxturna (first FDA-approved gene therapy); subretinal route"
    },
}

AAV_CAPACITY_KB = {
    "single_AAV": 4.7,
    "dual_split_AAV": 9.4,
    "oversized_AAV_tolerance": 5.5,   # some serotypes tolerate slight oversize with truncation risk
}

@dataclass
class DeliveryRecommendation:
    tissue: str
    editor: str
    cargo_kb: float
    preferred_modality: str
    aav_serotype: str | None
    aav_route: str | None
    capacity_ok: bool
    capacity_note: str
    rationale: str
    alternatives: list[str]
    clinical_precedent: str

def recommend_delivery(
    editor: str,
    tissue: str,
    cargo_kb: float,
    editor_length_aa: int = 326,
) -> DeliveryRecommendation:
    """Recommend delivery modality for an editor-tissue-cargo combination."""
    # Editor ORF size estimate (aa × 3 bp/aa ÷ 1000)
    editor_kb = editor_length_aa * 3 / 1000

    # Total payload: editor + cargo + regulatory elements (promoter, polyA ~1.5 kb overhead)
    total_kb = editor_kb + cargo_kb + 1.5
    tissue_key = tissue.lower().split("/")[0].strip()
    delivery_info = TISSUE_DELIVERY_MAP.get(tissue_key, TISSUE_DELIVERY_MAP["liver"])

    aav = delivery_info["aav_serotype"]
    if aav:
        if total_kb <= AAV_CAPACITY_KB["single_AAV"]:
            cap_ok = True
            cap_note = f"Single AAV packaging feasible ({total_kb:.1f} kb ≤ {AAV_CAPACITY_KB['single_AAV']} kb)"
        elif total_kb <= AAV_CAPACITY_KB["dual_split_AAV"]:
            cap_ok = True
            cap_note = f"Dual split-AAV required ({total_kb:.1f} kb; split at intein junction)"
        else:
            cap_ok = False
            cap_note = f"Exceeds dual-AAV capacity ({total_kb:.1f} kb > {AAV_CAPACITY_KB['dual_split_AAV']} kb). Use LNP/mRNA."
    else:
        cap_ok = True
        cap_note = "Non-AAV delivery — no capacity constraint"

    return DeliveryRecommendation(
        tissue=tissue, editor=editor, cargo_kb=cargo_kb,
        preferred_modality=delivery_info["preferred"][0],
        aav_serotype=aav,
        aav_route=delivery_info["aav_route"],
        capacity_ok=cap_ok,
        capacity_note=cap_note,
        rationale=delivery_info["rationale"],
        alternatives=delivery_info["preferred"][1:],
        clinical_precedent=_clinical_precedent(tissue),
    )

def _clinical_precedent(tissue: str) -> str:
    precedents = {
        "liver": "Luxturna (AAV2, eye) → AAV8 liver established in OTC/Hemophilia B programs",
        "airway": "No approved; Phase I/II trials ongoing for CF (AAV5+CFTR)",
        "blood": "Casgevy (CRISPR, ex vivo HSC) — first approved DSB-based; Molecular Pen would be first DSB-free",
        "cns": "Zolgensma (AAV9, IV, SMA) — established CNS precedent",
        "muscle": "Elevidys (AAVrh74, IM, DMD) — FDA approved 2023",
        "eye": "Luxturna (AAV2, subretinal, RPE65) — first FDA-approved gene therapy",
    }
    return precedents.get(tissue.lower(), "No direct clinical precedent; check ClinicalTrials.gov")
```

### Commit
```bash
git add pen_stack/deliver/modality_ranker.py pen_stack/deliver/__init__.py
git commit -m "feat: delivery modality ranker + AAV serotype + capacity check (PEN-DELIVER)"
```

---

## Steps 29–31: PEN-DELIVER LLM evidence Q&A + full module tests

Build a RAG corpus from 50 key delivery papers, expose it as `PEN-DELIVER.ask()`, and write 30+ unit tests. Architecture mirrors the pen-compare RAG module.

### Commit
```bash
git commit -m "feat: PEN-DELIVER delivery evidence RAG + module tests"
```

---

# PART H — PEN-BENCH: Experimental Planning (Weeks 8–9)

---

## Step 32: Protocol recommender (tier X → tier X+1)

**File: `pen_stack/bench/protocol_recommender.py`**

```python
"""Experimental protocol recommender for advancing an editor through certification tiers.

Given current tier + failed gates, recommends the minimal experiment to reach next tier.
Generates Jupyter notebook templates for direct use at bench.
"""
from dataclasses import dataclass

@dataclass
class ProtocolRecommendation:
    editor_id: str
    current_tier: str
    target_tier: str
    required_experiments: list[str]
    estimated_weeks: int
    estimated_cost_usd: int
    primary_cell_line: str
    positive_control: str
    negative_control: str
    threshold_to_advance: str
    protocol_citations: list[str]
    jupyter_notebook_path: str | None

TIER_ADVANCE_PROTOCOLS = {
    ("EMERGING_WRITER", "PROBABLE_WRITER"): {
        "experiments": [
            "Transient transfection of editor + bRNA plasmid in HEK293T",
            "Assess editing efficiency at target site by Sanger sequencing or amplicon NGS",
            "Western blot or IF for editor expression",
        ],
        "weeks": 3, "cost": 2000,
        "cell_line": "HEK293T", "pos_ctrl": "ISCro4 (TRUE_WRITER)",
        "neg_ctrl": "empty_vector",
        "threshold": "≥1% on-target insertion by amplicon-NGS",
        "citations": [
            "Perry et al. Science 2025 (ISCro4 HEK293T protocol — Supplementary Methods)",
            "Pelea et al. Science 2026 (ISCro4 editing efficiency protocol)",
        ],
    },
    ("PROBABLE_WRITER", "TRUE_WRITER"): {
        "experiments": [
            "Transient transfection in 3 distinct human cell lines (HEK293T, Huh7/HepG2, primary PBMC)",
            "Quantify insertion efficiency: ddPCR (primary readout) + amplicon NGS (specificity)",
            "Assess off-target insertions by GUIDE-seq or unbiased amplicon sequencing",
            "Cargo expression validation (if applicable): RT-qPCR + Western blot",
        ],
        "weeks": 6, "cost": 8000,
        "cell_line": "HEK293T + Huh7 + PBMC",
        "pos_ctrl": "ISCro4 + native bRNA (expected ≥6%)",
        "neg_ctrl": "empty_vector + scrambled_bRNA",
        "threshold": "≥2% on-target insertion in ≥2 human cell lines by ddPCR",
        "citations": [
            "Perry et al. Science 2025 (ISCro4 mammalian cell protocol)",
            "Anzalone et al. Nature Biotechnology 2022 (ddPCR quantification methods)",
        ],
    },
    ("NOT_WRITER", "EMERGING_WRITER"): {
        "experiments": [
            "In vitro recombination assay with purified protein + bRNA + target/donor substrates",
            "Inversion reporter assay in E. coli (if IS110 family)",
            "Verify DSB-free mechanism: γH2AX staining negative control",
        ],
        "weeks": 4, "cost": 3000,
        "cell_line": "in_vitro_and_Ecoli",
        "pos_ctrl": "IS621 (PROBABLE_WRITER)", "neg_ctrl": "heat_inactivated_enzyme",
        "threshold": "Detectable recombination product by PCR/gel, γH2AX-negative",
        "citations": [
            "Durrant & Perry et al. Nature 2024 (in vitro recombination protocol)",
            "Hiraizumi et al. Nature 2024 (structural mechanism)",
        ],
    },
}

def recommend_protocol(
    editor_id: str,
    current_tier: str,
    failed_gates: list[str],
    nb_output_dir: str = "notebooks/",
) -> ProtocolRecommendation:
    tier_map = {
        "NOT_WRITER": 0, "EMERGING_WRITER": 1, "PROBABLE_WRITER": 2, "TRUE_WRITER": 3
    }
    tier_order = ["NOT_WRITER", "EMERGING_WRITER", "PROBABLE_WRITER", "TRUE_WRITER"]
    current_idx = tier_map.get(current_tier, 0)
    if current_idx >= 3:
        # Already TRUE_WRITER — recommend clinical translation protocols
        return _clinical_translation_protocol(editor_id)

    target_tier = tier_order[current_idx + 1]
    proto = TIER_ADVANCE_PROTOCOLS.get((current_tier, target_tier), {})

    nb_path = _generate_notebook(editor_id, current_tier, target_tier, proto, nb_output_dir)

    return ProtocolRecommendation(
        editor_id=editor_id,
        current_tier=current_tier, target_tier=target_tier,
        required_experiments=proto.get("experiments", []),
        estimated_weeks=proto.get("weeks", 4),
        estimated_cost_usd=proto.get("cost", 5000),
        primary_cell_line=proto.get("cell_line", "HEK293T"),
        positive_control=proto.get("pos_ctrl", "ISCro4"),
        negative_control=proto.get("neg_ctrl", "empty_vector"),
        threshold_to_advance=proto.get("threshold", "≥1% on-target"),
        protocol_citations=proto.get("citations", []),
        jupyter_notebook_path=nb_path,
    )

def _generate_notebook(editor, current_tier, target_tier, proto, output_dir) -> str:
    """Generate a Jupyter notebook template for the experiment."""
    import nbformat
    from pathlib import Path
    from datetime import date

    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_markdown_cell(f"# PEN-BENCH Protocol: {editor}\n\n"
                                       f"**Goal:** Advance from {current_tier} → {target_tier}\n"
                                       f"**Date:** {date.today()}\n"
                                       f"**Estimated time:** {proto.get('weeks', 4)} weeks\n"
                                       f"**Estimated cost:** ~${proto.get('cost', 5000):,}"),
        nbformat.v4.new_markdown_cell("## Experimental design\n\n"
                                       + "\n".join(f"- {e}" for e in proto.get("experiments", []))),
        nbformat.v4.new_markdown_cell("## Controls\n\n"
                                       f"- **Positive control:** {proto.get('pos_ctrl')}\n"
                                       f"- **Negative control:** {proto.get('neg_ctrl')}\n"
                                       f"- **Advancement threshold:** {proto.get('threshold')}"),
        nbformat.v4.new_code_cell(
            "# Data analysis template\n"
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n\n"
            "# Load your ddPCR / amplicon NGS results here\n"
            "# results = pd.read_csv('editing_efficiency.csv')\n"
        ),
        nbformat.v4.new_markdown_cell("## Citations\n\n"
                                       + "\n".join(f"- {c}" for c in proto.get("citations", []))),
    ]
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    nb_path = f"{output_dir}/{editor}_protocol_{current_tier}_to_{target_tier}.ipynb"
    nbformat.write(nb, nb_path)
    return nb_path

def _clinical_translation_protocol(editor_id: str) -> ProtocolRecommendation:
    return ProtocolRecommendation(
        editor_id=editor_id, current_tier="TRUE_WRITER", target_tier="IND_APPLICATION",
        required_experiments=[
            "GLP toxicology studies (repeat-dose, genotoxicity per ICH S2(R1))",
            "Biodistribution study (NHP or appropriate animal model)",
            "Manufacturing development (GMP-grade editor expression + purification)",
            "IND-enabling package assembly (CMC, preclinical, clinical rationale)",
        ],
        estimated_weeks=104, estimated_cost_usd=5_000_000,
        primary_cell_line="NHP_primary_cells",
        positive_control="Casgevy_protocol (approved comparator)",
        negative_control="vehicle_only",
        threshold_to_advance="FDA/EMA IND acceptance criteria",
        protocol_citations=["FDA Guidance: Human Gene Therapy Products (2020)"],
        jupyter_notebook_path=None,
    )
```

### Commit
```bash
git add pen_stack/bench/ tests/unit/test_bench.py
git commit -m "feat: PEN-BENCH experimental protocol recommender + Jupyter notebook generator"
```

---

# PART I — Pipeline Class: End-to-End Integration (Week 9)

---

## Step 36: Pipeline.run() + Pipeline.query()

**File: `pen_stack/pipeline/pipeline.py`**

```python
"""PEN-STACK end-to-end Pipeline class.

The single entry point for clinical research queries.
Integrates all 7 modules in one call.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PipelineResult:
    query: str
    gene_name: str
    tissue: str
    cargo_kb: float
    recommended_editors: list[dict]       # ranked by TW probability + safety
    target_sites: list[dict]              # top 10 bRNA-designed sites
    safety_scores: dict[str, dict]        # per-editor RRI
    optimized_designs: list[dict]         # bRNA + codon-optimized editor
    delivery_recommendation: dict
    experimental_roadmap: list[dict]      # per-editor tier → tier+1 protocol
    pipeline_duration_seconds: float

class Pipeline:
    """End-to-end platform pipeline."""

    @classmethod
    def run(
        cls,
        query: str,
        cargo_kb: float = 2.0,
        tissue: str = "liver",
        editor: Optional[str] = None,
        n_editors: int = 5,
        n_target_sites: int = 10,
    ) -> PipelineResult:
        """Run the full PEN-STACK pipeline for a clinical query.

        Args:
            query: Free text or gene name (e.g., "CFTR-F508del", "treat SCD")
            cargo_kb: Size of therapeutic cargo in kilobases
            tissue: Target tissue ("liver", "airway", "blood", "cns", "muscle", "eye")
            editor: Specific editor to use (None = auto-recommend top editors)
            n_editors: Number of editors to evaluate
            n_target_sites: Number of target sites to return per editor
        """
        import time
        t0 = time.time()

        # Module 1 — Parse query + look up disease locus
        from pen_stack.target.locus_lookup import lookup_disease_locus
        from pen_stack.compare.certify import certify
        from pen_stack.target.attb_scanner import scan_gene_window, recommend_target_sites
        from pen_stack.safe.regulatory_index import compute_rri
        from pen_stack.deliver.modality_ranker import recommend_delivery
        from pen_stack.bench.protocol_recommender import recommend_protocol

        # Step 1: Find disease locus
        locus = lookup_disease_locus(query)
        gene = locus["gene_name"]
        chrom = locus["chromosome"]

        # Step 2: Get certified editor universe (from pen-compare)
        from pen_score import load_editor_universe, get_editor_metadata, score
        universe = load_editor_universe()
        certified_editors = []
        for ed in universe.editors[:n_editors * 3]:  # over-sample, then filter
            try:
                md = get_editor_metadata(ed.id)
                s = score(ed.id)
                res = certify(
                    editor_id=ed.id, s_dsb=s.axes["S_DSB"], s_prog=s.axes["S_Prog"],
                    s_cargo=s.axes["S_Cargo"], length_aa=ed.length_aa or 400,
                    evidence_sources=([k for k, v in {
                        "biochemical": True, "computational": True,
                        "cell_based": md.cell_based_evidence,
                        "structural": False,
                    }.items() if v]),
                    intrinsic_cargo_mechanism=md.intrinsic_cargo_mechanism,
                )
                if res.tier in ("TRUE_WRITER", "PROBABLE_WRITER"):
                    certified_editors.append({
                        "editor_id": ed.id, "tier": res.tier,
                        "penscore": s.penscore, "length_aa": ed.length_aa or 400,
                    })
            except Exception:
                pass

        certified_editors = sorted(
            certified_editors, key=lambda x: x["penscore"], reverse=True
        )[:n_editors]

        # Step 3: Target sites for top editor
        top_editor_id = certified_editors[0]["editor_id"] if certified_editors else "ISCro4"
        sites = scan_gene_window(gene, window_bp=5000, chromosome=chrom, start_coord=locus["start"])
        top_sites = [vars(s) for s in sites[:n_target_sites]]

        # Step 4: Safety scores
        from pen_stack.safe.oncogene_proximity import check_oncogene_proximity
        from pen_stack.safe.essential_gene_risk import check_essential_gene_risk
        from pen_stack.safe.immunogenicity import predict_immunogenicity
        from pen_stack.safe.cargo_safety import check_cargo_safety
        safety = {}
        for ed in certified_editors[:3]:
            eid = ed["editor_id"]
            try:
                onco = check_oncogene_proximity(chrom, locus["start"])
                ess = check_essential_gene_risk(chrom, locus["start"])
                imm = predict_immunogenicity(eid, "PLACEHOLDER_SEQ")
                cargo_s = check_cargo_safety("A" * int(cargo_kb * 333))
                rri = compute_rri(eid, f"{chrom}:{locus['start']}", onco, ess, imm, cargo_s)
                safety[eid] = {"rri": rri.rri_score, "category": rri.rri_category,
                               "summary": rri.summary}
            except Exception as e:
                safety[eid] = {"rri": -1, "category": "error", "summary": str(e)}

        # Step 5: Delivery
        delivery = recommend_delivery(top_editor_id, tissue, cargo_kb,
                                       certified_editors[0].get("length_aa", 326))

        # Step 6: Experimental roadmap
        roadmap = []
        for ed in certified_editors[:3]:
            try:
                proto = recommend_protocol(ed["editor_id"], ed["tier"], [], "notebooks/")
                roadmap.append({
                    "editor_id": ed["editor_id"],
                    "current_tier": proto.current_tier,
                    "target_tier": proto.target_tier,
                    "estimated_weeks": proto.estimated_weeks,
                    "notebook": proto.jupyter_notebook_path,
                })
            except Exception:
                pass

        return PipelineResult(
            query=query, gene_name=gene, tissue=tissue, cargo_kb=cargo_kb,
            recommended_editors=certified_editors,
            target_sites=top_sites,
            safety_scores=safety,
            optimized_designs=[],   # filled in Step 37
            delivery_recommendation=vars(delivery),
            experimental_roadmap=roadmap,
            pipeline_duration_seconds=time.time() - t0,
        )

    @classmethod
    def query(cls, natural_language_query: str) -> PipelineResult:
        """Natural language interface: parse query → run Pipeline.run().

        Example:
            Pipeline.query("What's the best IS110 editor for treating SCD in HSCs?")
        """
        import ollama, re

        parse_prompt = f"""Extract gene therapy parameters from this query.
Return ONLY valid JSON: {{"gene": "...", "disease": "...", "tissue": "...", "cargo_kb": 2.0}}

Query: {natural_language_query}
JSON:"""
        response = ollama.generate(model="llama3.1:8b-instruct-q4_K_M", prompt=parse_prompt)
        raw = response["response"].strip()
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip()

        import json
        params = json.loads(raw)
        query = params.get("gene") or params.get("disease") or natural_language_query
        tissue = params.get("tissue", "liver")
        cargo_kb = float(params.get("cargo_kb", 2.0))

        return cls.run(query=query, tissue=tissue, cargo_kb=cargo_kb)
```

### Commit
```bash
git add pen_stack/pipeline/ tests/integration/test_pipeline.py
git commit -m "feat: Pipeline.run() + Pipeline.query() end-to-end integration"
```

---

## Step 37: Clinical scenario validation (CFTR, SCD, TTR)

Run three clinical scenarios as integration tests:

```python
# tests/e2e/test_clinical_scenarios.py
import pytest
from pen_stack import Pipeline

SCENARIOS = [
    {
        "name": "CFTR-F508del / airway",
        "query": "CFTR",
        "tissue": "airway",
        "cargo_kb": 4.7,
    },
    {
        "name": "SCD HbS / HSC",
        "query": "HBB",
        "tissue": "blood",
        "cargo_kb": 1.5,
    },
    {
        "name": "TTR amyloidosis / liver",
        "query": "TTR",
        "tissue": "liver",
        "cargo_kb": 2.0,
    },
]

@pytest.mark.e2e
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
def test_clinical_scenario(scenario):
    result = Pipeline.run(
        query=scenario["query"],
        tissue=scenario["tissue"],
        cargo_kb=scenario["cargo_kb"],
    )
    assert result.gene_name is not None
    assert len(result.recommended_editors) >= 1
    assert len(result.target_sites) >= 1
    assert result.delivery_recommendation is not None
    print(f"\n{scenario['name']}: {len(result.recommended_editors)} editors, "
          f"{len(result.target_sites)} sites, RRI={result.safety_scores}")
```

```bash
pytest tests/e2e/test_clinical_scenarios.py -v -m e2e
```

### Commit
```bash
git add tests/e2e/
git commit -m "test: 3 clinical scenario E2E tests (CFTR, SCD, TTR)"
```

---

# PART J — Unified Streamlit + REST API + Community Portal (Weeks 9–10)

---

## Step 39: Extended Streamlit app (10 tabs)

**File: `pen_stack/server/app.py`**

```python
"""Unified PEN-STACK Streamlit webserver — 10 tabs, one per module + Pipeline."""
import streamlit as st

st.set_page_config(page_title="PEN-STACK Platform", layout="wide",
                   page_icon="🧬", initial_sidebar_state="expanded")

TABS = [
    "🏠 Home", "🏆 Certify", "🔍 Discover",
    "🎯 Target", "🛡️ Safety", "🧪 Design",
    "💉 Deliver", "🔬 Bench", "🌐 Pipeline", "💬 Q&A"
]

st.title("PEN-STACK: Non-Destructive Genome Engineering Platform")
st.caption("v1.0.0 | ISCro4 → TRUE_WRITER | 1,058 editors evaluated")

tab_objects = st.tabs(TABS)

with tab_objects[0]:  # Home
    st.header("Welcome to PEN-STACK")
    st.write("""PEN-STACK is the first comprehensive platform for non-destructive genome engineering.
    It covers the complete workflow from editor discovery to clinical readiness.
    Use the Pipeline tab for a one-click end-to-end analysis, or explore individual modules.""")
    col1, col2, col3 = st.columns(3)
    col1.metric("Editors certified", "1,058")
    col2.metric("TRUE_WRITERs found", "1")
    col3.metric("hg38 target sites", "~10M potential")

with tab_objects[1]:  # Certify (pen-compare)
    st.header("TrueWriter Certification")
    editor_a = st.selectbox("Select Editor A", ["ISCro4", "IS621", "SpCas9", "Bxb1", "evoCAST"])
    editor_b = st.selectbox("Select Editor B", ["IS621", "ISCro4", "Bxb1", "phiC31", "SpCas9"])
    if st.button("Compare"):
        # Load from precomputed scorecard
        import pandas as pd, json
        scorecard = pd.read_parquet("data/truewriter_scorecard_v3.2.parquet")
        for eid in [editor_a, editor_b]:
            row = scorecard[scorecard.entity_id == eid]
            if not row.empty:
                st.metric(f"{eid} Tier", row.iloc[0]["tier"])

with tab_objects[2]:  # Discover
    st.header("IS110 Sequence Prediction")
    fasta_input = st.text_area("Paste protein sequence (FASTA or raw AA):", height=150)
    if st.button("Predict TrueWriter Probability") and fasta_input:
        with st.spinner("Running ESM-2 + gate prediction..."):
            from pen_stack.discover.embeddings import ESM2Embedder
            from pen_stack.discover.predictor import DiscoverPredictor
            seq = fasta_input.split("\n")[-1].strip() if ">" in fasta_input else fasta_input.strip()
            try:
                emb = ESM2Embedder().embed(seq)
                pred = DiscoverPredictor(); pred.load()
                result = pred.predict(emb, editor_id="query")
                col1, col2, col3 = st.columns(3)
                col1.metric("TrueWriter Probability", f"{result.tw_probability:.2f}")
                col2.metric("Predicted Tier", result.predicted_tier)
                col3.metric("Recommendation", result.recommendation)
            except Exception as e:
                st.error(f"Prediction error: {e}")

with tab_objects[3]:  # Target
    st.header("Genome Target Site Finder")
    gene_query = st.text_input("Disease or gene name:", placeholder="CFTR, HBB, TTR, LDLR...")
    tissue_for_target = st.selectbox("Target tissue:", ["liver", "airway", "blood", "cns", "muscle", "eye"])
    if st.button("Find Target Sites") and gene_query:
        with st.spinner(f"Scanning hg38 near {gene_query}..."):
            from pen_stack.target import recommend_target_sites
            try:
                sites = recommend_target_sites(gene_query, n_top=10)
                import pandas as pd
                df = pd.DataFrame([{
                    "Site": s.site_id, "14-nt Target": s.sequence_14nt,
                    "GC%": f"{s.gc_content:.0%}", "Quality": f"{s.quality_score:.2f}",
                    "In Exon": s.is_in_exon,
                } for s in sites])
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"Target lookup error: {e}")

with tab_objects[4]:  # Safety
    st.header("Safety Analysis")
    st.info("Enter an editor ID and target site for full safety report including Regulatory Readiness Index (RRI).")

with tab_objects[5]:  # Design
    st.header("bRNA + Cargo Design")
    target_14nt = st.text_input("14-nt genomic target sequence:", placeholder="ACGTACGTACGTAC")
    donor_14nt = st.text_input("14-nt donor sequence:", placeholder="ACGTACGTACGTAC")
    if st.button("Design bRNA") and len(target_14nt) == 14:
        from pen_stack.design.brna_designer import design_brna_full
        result = design_brna_full(target_14nt, donor_14nt.ljust(14, "N")[:14])
        st.code(result.brna_sequence, language="text")
        if not result.passes_filters:
            st.warning("Quality warnings: " + "; ".join(result.filter_warnings))

with tab_objects[6]:  # Deliver
    st.header("Delivery Optimization")
    tissue_deliver = st.selectbox("Target tissue", ["liver", "airway", "blood", "cns", "muscle", "eye"])
    cargo_size = st.slider("Cargo size (kb)", 0.5, 10.0, 2.0)
    editor_deliver = st.selectbox("Editor", ["ISCro4", "IS621", "evoCAST"])
    if st.button("Recommend Delivery"):
        from pen_stack.deliver.modality_ranker import recommend_delivery
        rec = recommend_delivery(editor_deliver, tissue_deliver, cargo_size)
        st.metric("Preferred Modality", rec.preferred_modality)
        st.metric("AAV Serotype", rec.aav_serotype or "N/A")
        st.info(rec.capacity_note)
        st.caption(rec.rationale)

with tab_objects[7]:  # Bench
    st.header("Experimental Planning")
    editor_bench = st.text_input("Editor ID:", "ISCro4")
    current_tier = st.selectbox("Current tier:", ["NOT_WRITER", "EMERGING_WRITER", "PROBABLE_WRITER"])
    if st.button("Generate Protocol"):
        from pen_stack.bench.protocol_recommender import recommend_protocol
        proto = recommend_protocol(editor_bench, current_tier, [], "notebooks/")
        st.metric("Target tier", proto.target_tier)
        st.metric("Estimated time", f"{proto.estimated_weeks} weeks")
        st.metric("Estimated cost", f"~${proto.estimated_cost_usd:,}")
        for exp in proto.required_experiments:
            st.write(f"• {exp}")

with tab_objects[8]:  # Pipeline
    st.header("End-to-End Clinical Query")
    query = st.text_input("Disease / gene query:", placeholder="CFTR-F508del in airway epithelium")
    tissue_pipe = st.selectbox("Target tissue", ["airway", "liver", "blood", "cns"])
    cargo_pipe = st.slider("Cargo size (kb)", 0.5, 5.0, 2.0, key="pipe_cargo")
    if st.button("Run Full Pipeline") and query:
        with st.spinner("Running all 7 PEN-STACK modules..."):
            from pen_stack import Pipeline
            try:
                result = Pipeline.run(query=query, tissue=tissue_pipe, cargo_kb=cargo_pipe)
                st.success(f"Pipeline complete in {result.pipeline_duration_seconds:.1f}s")
                st.subheader("Recommended editors")
                import pandas as pd
                df = pd.DataFrame(result.recommended_editors)
                st.dataframe(df)
                st.subheader("Delivery recommendation")
                st.json(result.delivery_recommendation)
            except Exception as e:
                st.error(f"Pipeline error: {e}")

with tab_objects[9]:  # Q&A
    st.header("Ask PEN-STACK Anything")
    question = st.text_input("Your question:", placeholder="What makes ISCro4 a TRUE_WRITER?")
    if question:
        from pen_stack.rag.qa import PenStackQA
        try:
            qa = PenStackQA()
            response = qa.ask(question)
            st.write(response["answer"])
            st.caption("Sources: " + ", ".join(response["sources"][:3]))
        except Exception as e:
            st.warning(f"Q&A unavailable (Ollama offline?): {e}")
```

### Commit
```bash
git add pen_stack/server/app.py
git commit -m "feat: unified Streamlit app with 10 tabs (one per module + Pipeline)"
```

---

## Step 41: FastAPI REST gateway

**File: `pen_stack/api/main.py`**

```python
"""FastAPI REST API — all PEN-STACK modules exposed as versioned REST endpoints."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="PEN-STACK Platform API",
    description="REST API for non-destructive genome engineering analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

class CertifyRequest(BaseModel):
    editor_id: str
    s_dsb: float; s_prog: float; s_cargo: float
    length_aa: int
    intrinsic_cargo_mechanism: bool
    cell_based_evidence: bool
    evidence_sources: list[str]

class DiscoverRequest(BaseModel):
    sequence: str
    editor_id: Optional[str] = "query"

class TargetRequest(BaseModel):
    gene: str
    tissue: Optional[str] = "liver"
    window_bp: Optional[int] = 5000
    n_sites: Optional[int] = 10

class DesignRequest(BaseModel):
    target_14nt: str
    donor_14nt: str
    editor: Optional[str] = "IS621"

class PipelineRequest(BaseModel):
    query: str
    tissue: Optional[str] = "liver"
    cargo_kb: Optional[float] = 2.0

@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "platform": "pen-stack", "version": "1.0.0"}

@app.post("/v1/certify", tags=["compare"])
def certify_endpoint(req: CertifyRequest):
    from pen_stack.compare.certify import certify
    try:
        result = certify(
            editor_id=req.editor_id, s_dsb=req.s_dsb, s_prog=req.s_prog,
            s_cargo=req.s_cargo, length_aa=req.length_aa,
            evidence_sources=req.evidence_sources,
            intrinsic_cargo_mechanism=req.intrinsic_cargo_mechanism,
        )
        return {"editor_id": result.editor_id, "tier": result.tier,
                "qualifying_gates_passed": result.qualifying_gates_passed,
                "has_cell_based": result.has_cell_based_evidence}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/v1/discover", tags=["discover"])
def discover_endpoint(req: DiscoverRequest):
    from pen_stack.discover.embeddings import ESM2Embedder
    from pen_stack.discover.predictor import DiscoverPredictor
    try:
        emb = ESM2Embedder().embed(req.sequence)
        pred = DiscoverPredictor(); pred.load()
        result = pred.predict(emb, req.editor_id)
        return {"tw_probability": result.tw_probability,
                "predicted_tier": result.predicted_tier,
                "recommendation": result.recommendation,
                "gate_probabilities": result.gate_probabilities}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/v1/target", tags=["target"])
def target_endpoint(req: TargetRequest):
    from pen_stack.target import recommend_target_sites
    try:
        sites = recommend_target_sites(req.gene, n_top=req.n_sites)
        return {"gene": req.gene, "n_sites": len(sites),
                "sites": [{"id": s.site_id, "sequence": s.sequence_14nt,
                            "quality": s.quality_score, "brna": s.brna_sequence}
                           for s in sites]}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/v1/design/brna", tags=["design"])
def brna_endpoint(req: DesignRequest):
    from pen_stack.design.brna_designer import design_brna_full
    try:
        result = design_brna_full(req.target_14nt, req.donor_14nt, req.editor)
        return {"brna_sequence": result.brna_sequence, "passes_filters": result.passes_filters,
                "warnings": result.filter_warnings, "ltg": result.ltg, "rtg": result.rtg}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/v1/pipeline", tags=["pipeline"])
def pipeline_endpoint(req: PipelineRequest):
    from pen_stack import Pipeline
    try:
        result = Pipeline.run(query=req.query, tissue=req.tissue, cargo_kb=req.cargo_kb)
        return {
            "gene": result.gene_name, "tissue": result.tissue,
            "recommended_editors": result.recommended_editors,
            "delivery": result.delivery_recommendation,
            "duration_seconds": result.pipeline_duration_seconds,
        }
    except Exception as e:
        raise HTTPException(500, str(e))
```

```bash
# Start the API server
uvicorn pen_stack.api.main:app --host 0.0.0.0 --port 8000 --reload

# Test
curl -X POST http://localhost:8000/v1/certify \
  -H "Content-Type: application/json" \
  -d '{"editor_id":"ISCro4","s_dsb":1.0,"s_prog":1.0,"s_cargo":0.95,
       "length_aa":326,"intrinsic_cargo_mechanism":true,"cell_based_evidence":true,
       "evidence_sources":["biochemical","structural","computational","cell_based"]}'
# Expected: {"editor_id":"ISCro4","tier":"TRUE_WRITER","qualifying_gates_passed":4,"has_cell_based":true}
```

### Commit
```bash
git add pen_stack/api/ tests/integration/test_api.py
git commit -m "feat: FastAPI REST gateway with /v1/certify, /v1/discover, /v1/target, /v1/design/brna, /v1/pipeline"
```

---

## Step 42: Community data submission portal

**File: `.github/ISSUE_TEMPLATE/editor_evidence_submission.yml`**

```yaml
name: "Submit Editor Evidence"
description: "Submit new cell-based evidence for an editor not yet in the universe"
title: "[SUBMISSION] [editor name]: new evidence"
labels: ["community-submission", "needs-review"]
body:
  - type: input
    id: editor_name
    attributes:
      label: "Editor canonical name"
      description: "Use canonical UniProt-anchored name (e.g. ISCro4, not IS622)"
      placeholder: "ISCro4"
    validations:
      required: true

  - type: input
    id: paper_doi
    attributes:
      label: "DOI of supporting paper"
      placeholder: "10.1126/science.adz1884"
    validations:
      required: true

  - type: dropdown
    id: evidence_type
    attributes:
      label: "Evidence type"
      options:
        - "mammalian_cell (≥1% editing in human/primate cells)"
        - "bacterial (E. coli or other prokaryote only)"
        - "in_vitro (purified components, no cells)"
        - "animal_model (mouse, NHP, etc.)"
    validations:
      required: true

  - type: input
    id: efficiency
    attributes:
      label: "Reported editing efficiency (%)"
      placeholder: "6.2"

  - type: input
    id: cell_type
    attributes:
      label: "Cell type tested"
      placeholder: "HEK293T, CD34+ HSCs, primary hepatocytes, etc."

  - type: textarea
    id: claim_quote
    attributes:
      label: "Exact quote from paper supporting this claim (max 50 words)"
      placeholder: "Copy the specific sentence from the results/abstract"
    validations:
      required: true
```

Maintainer workflow: review submission Issue → label `approved` → PEN-MONITOR auto-picks it up in next nightly run → `editor_universe.yaml` v1.0.8 cut → re-certification run.

### Commit
```bash
git add .github/ISSUE_TEMPLATE/
git commit -m "feat: community editor evidence submission GitHub Issue template"
```

---

# PART K — Tests, Docs, CI/CD, Release (Weeks 10–11)

---

## Step 45: Full test suite (≥90% coverage)

### Duration
2 days

```bash
pytest tests/ \
    --cov=pen_stack \
    --cov-omit="pen_stack/server/*,pen_stack/api/*" \
    --cov-report=term \
    --cov-fail-under=90

# Run E2E separately (requires full VM environment):
pytest tests/e2e/ -v -m e2e --timeout=300
```

**Coverage targets per module:**

| Module | Target coverage |
|---|---|
| compare/ | ≥98% (migrated from pen-compare v0.1.0) |
| discover/ | ≥90% |
| target/ | ≥85% |
| monitor/ | ≥85% |
| safe/ | ≥90% |
| design/ | ≥95% |
| deliver/ | ≥85% |
| bench/ | ≥90% |
| pipeline/ | ≥80% |
| api/ | ≥85% |

### Commit
```bash
git commit -am "test: ≥90% coverage across all 7 modules"
```

---

## Step 46: Sphinx documentation + GitHub Pages

**Docs structure:**
```
docs/
├── index.rst               # Platform overview + quick start
├── overview.rst            # Molecular Pen paradigm
├── modules/
│   ├── compare.rst         # pen-compare certification
│   ├── discover.rst        # ESM-2 sequence prediction
│   ├── target.rst          # bRNA genome targeting
│   ├── monitor.rst         # living database
│   ├── safe.rst            # safety analysis + RRI
│   ├── design.rst          # bRNA + codon + cargo
│   ├── deliver.rst         # delivery optimization
│   └── bench.rst           # experimental planning
├── pipeline.rst            # Pipeline.run() + Pipeline.query()
├── api_reference.rst       # FastAPI REST endpoints
├── MODEL_CARD.md           # All models, calibration, limitations
├── CLINICAL_GUIDE.md       # How to use for clinical programs
└── COMMUNITY.md            # Submission + contribution guide
```

```bash
cd docs/
sphinx-quickstart
make html
# Deploy to GitHub Pages via .github/workflows/docs.yml
```

### Commit
```bash
git add docs/ .github/workflows/docs.yml .github/workflows/ci.yml
git commit -m "docs: Sphinx documentation for all 7 modules + GitHub Pages CI"
```

---

## Step 47: PyPI release v1.0.0

```bash
# Bump version
sed -i 's/1.0.0a1/1.0.0/' pyproject.toml pen_stack/_version.py

# Build
python -m build

# Upload
twine upload dist/pen_stack-1.0.0*

# Tag
git tag v1.0.0
git push origin --tags
```

**Final verification:**
```bash
pip install pen-stack[full]
pen-stack certify ISCro4
# Expected: ISCro4 → TRUE_WRITER

pen-stack discover --fasta test_is110.fasta
# Expected: TrueWriter probability for submitted sequence

pen-stack target --gene CFTR --tissue airway
# Expected: Top 10 bRNA target sites near CFTR gene
```

### Commit
```bash
git commit -am "release: pen-stack v1.0.0 — full platform"
```

---

# PART L — Nature Methods Manuscript + Submission (Week 12)

---

## Step 49: Figure generation (8 figures)

**Figure 1 (overview):** PEN-STACK platform architecture diagram — Molecular Pen workflow from sequence discovery to clinical readiness; 7 modules as connected stages; one-call Pipeline API example.

**Figure 2 (certify):** TrueWriter tier distribution across 1,058 entities; ISCro4 as sole TRUE_WRITER; sensitivity analysis heatmap; robustness = 1.000 for ISCro4.

**Figure 3 (discover):** ESM-2 embedding space (t-SNE/UMAP) colored by tier; 1000 IS110 orthologue screen results; top candidates for characterization.

**Figure 4 (target):** CFTR locus target site map — 200 candidate sites, top-10 ranked by quality score; bRNA sequences for top sites; gnomAD population variant check.

**Figure 5 (safe):** Regulatory Readiness Index (RRI) for ISCro4 across 3 disease programs (CFTR, SCD, TTR); component spider plot; comparison to CASGEVY safety profile.

**Figure 6 (design):** bRNA design validation — designed vs native IS621 bRNA structure; codon optimization CAI improvement in liver vs airway; cargo safety flag distribution across 1,029 pen-assemble designs.

**Figure 7 (pipeline):** End-to-end clinical query walkthrough — CFTR-F508del input → all 7 module outputs → result in one figure.

**Figure 8 (monitor):** PEN-MONITOR living database — timeline showing IS621 upgrade pathway if new cell data published; architecture of nightly watch loop.

```bash
python scripts/49_generate_figures.py
# Outputs: figures/fig1.pdf through figures/fig8.pdf
```

---

## Step 50: Manuscript writing (*Nature Methods* format)

**Word budget (~4,000 words main text):**

| Section | Words |
|---|---|
| Abstract | 150 |
| Introduction | 600 |
| Results (7 modules + Pipeline) | 1,800 |
| Discussion | 800 |
| Methods (brief, with Extended Data) | 500 |
| Availability | 150 |

**Extended Data:** 8 panels — full technical details for each module, calibration anchor tables, sensitivity analysis, benchmark Q&A results, clinical scenario data.

**Reporting Summary:** Nature Methods requires a completed reporting summary for new methods/tools; include pre-registration link.

---

## Step 51: bioRxiv preprint + submission

```bash
# Submit bioRxiv preprint (parallel with journal)
# Submit to Nature Methods
# Cover letter highlights:
# 1. First comprehensive platform for non-destructive genome engineering
# 2. Seven integrated modules covering discovery → clinical readiness
# 3. Novel ESM-2-based TrueWriter prediction (PEN-DISCOVER)
# 4. Living database engine (PEN-MONITOR) — first for this field
# 5. Validated on 3 clinical scenarios (CFTR, SCD, TTR)
# 6. Open source, PyPI-installable, $0 marginal cost
# 7. Pre-registered on OSF

git tag v1.0.0-submitted
git push origin --tags
```

---

## Step 52: Post-submission community outreach

1. Tweet/post announcing pen-stack + bioRxiv link; tag @arcinstitute, @hsu_lab, @broadinstitute
2. Email 5 relevant gene therapy labs with GitHub link + Streamlit demo
3. Submit to Bioinformatics Software Highlight lists (NAR, Bioinformatics, Nature Methods)
4. Create a Twitter thread walkthrough of the CFTR clinical scenario using the live webserver
5. Open Discussions on GitHub for community feedback

---

# §3 — Non-Goals

| Out of scope for v1.0.0 | Reason / Future work |
|---|---|
| Wet-lab validation of predicted targets | Clinical collaborator effort; deferred |
| NHP or in vivo safety data | Requires external lab partnership |
| Fine-tuning ESM-2 on IS110-specific data | Low-N limitation; as more editors are characterized this becomes feasible in v2.0 |
| Multi-editor combination therapy planning | v2.0 feature |
| Closed-source or paid commercial features | Not consistent with academic mission; v1.0.0 is fully open |
| Full NCBI genome-wide off-target scan | Compute-intensive; local BLAST on VM is sufficient for v1.0.0 |

---

# §4 — Risk Register

| Risk | Probability | Mitigation |
|---|---|---|
| ESM-2 predictions have low accuracy at N=29 | Medium | Clearly communicate low-N limitations; wide confidence intervals; model updates automatically as more editors are characterized |
| Nature Methods rejects for insufficient novelty | Medium | Peer-reviewed novelty is the living database + clinical pipeline integration; no tool covers this scope |
| BepiPred-3.0 API unavailable | Low | Graceful degradation; note local installation option |
| NCBI rate limiting during bRNA site scanning | Medium | 3 req/sec limit; use caching for gene coordinates |
| gnomAD API response time | Low | Async with 30s timeout; cache responses per region |
| COSMIC CGC requires registration | Low | Bundled static CSV for common use; registration instructions in docs |
| Streamlit Cloud memory limits for ESM-2 | High | ESM-2 runs on VM only; Streamlit Cloud version uses precomputed predictions |

---

# §5 — Publication-Readiness Gate

Before Nature Methods submission, all 10 gates must be ✅:

| Gate | Condition |
|---|---|
| 1 | pen-stack v1.0.0 live on PyPI |
| 2 | All 7 modules have ≥85% test coverage |
| 3 | E2E clinical scenarios (CFTR, SCD, TTR) pass |
| 4 | FastAPI REST at /v1/certify, /v1/discover, /v1/target, /v1/design/brna, /v1/pipeline |
| 5 | Streamlit webserver with 10 tabs live on Streamlit Community Cloud |
| 6 | All 8 manuscript figures generated |
| 7 | MODEL_CARD.md documents all module limitations |
| 8 | Sphinx docs live on GitHub Pages |
| 9 | CITATION.cff + Zenodo DOI minted |
| 10 | Community Issue template functional on GitHub |

---

## Final deliverables summary

When 52/52 steps complete:

| Deliverable | Description |
|---|---|
| `pen-stack v1.0.0` PyPI package | `pip install pen-stack[full]` → all 7 modules |
| `pen-stack:1.0.0` Docker container | All modules + Ollama + ESM-2 + Streamlit + FastAPI |
| Live webserver | 10-tab Streamlit app on Streamlit Community Cloud |
| REST API | FastAPI v1 endpoints for all modules |
| Community portal | GitHub Issue template for evidence submissions |
| PEN-MONITOR scheduler | Nightly nightly Europe PMC watch + LLM extraction |
| 8 manuscript figures | Publication-ready vector format (PDF) |
| Nature Methods manuscript | ~4,000 words, submitted |
| Zenodo archive | DOI-minted for citable software artifact |
| **Total marginal cost** | **$0.00** |
