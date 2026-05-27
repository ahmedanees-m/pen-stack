# PEN-STACK: Comprehensive Computational Platform for Non-Destructive Genome Engineering

[![CI](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/pen-stack)](https://pypi.org/project/pen-stack/)

**PEN-STACK** is the first comprehensive computational platform for the Molecular Pen era of genome medicine.
It integrates editor discovery, certification, genome targeting, safety analysis, bRNA design, delivery
optimization, and experimental planning in a single unified framework — grounded in the IS110 bridge
recombinase system (DSB-free genome engineering).

## Platform Architecture

```
Novel IS110 sequence                            Clinical readiness
      |                                                  ^
PEN-DISCOVER -> PEN-COMPARE -> PEN-TARGET -> PEN-SAFE -> PEN-DESIGN -> PEN-DELIVER -> PEN-BENCH
      ^__________________________ PEN-MONITOR ___________________________________|
                          (living database -- keeps everything current)
```

| Module | Function |
|---|---|
| **PEN-COMPARE** | Hierarchical certification (TRUE / PROBABLE / EMERGING / NOT writer) |
| **PEN-DISCOVER** | Sequence -> TrueWriter probability for uncharacterized IS110 orthologues |
| **PEN-TARGET** | bRNA TBL site scanner in hg38 + gnomAD v4 population variant check |
| **PEN-MONITOR** | Living database -- auto-updates from literature via Europe PMC + LLM |
| **PEN-SAFE** | Oncogene proximity (COSMIC CGC), essentiality (DepMap), immunogenicity (BepiPred-3.0) |
| **PEN-DESIGN** | IS621/ISCro4 bRNA design + codon optimization + cargo checking |
| **PEN-DELIVER** | Delivery modality recommendation + AAV serotype + capacity checking |
| **PEN-BENCH** | Experimental protocol generator + Jupyter notebook templates |

## Quick Start

```python
from pen_stack import Pipeline

result = Pipeline.run(
    query="Treat CFTR-F508del in airway epithelium",
    cargo_kb=3.2
)
print(result.recommended_editors)
print(result.target_sites)
print(result.delivery_recommendation)
```

## Installation

```bash
pip install pen-stack[full]                      # all modules
pip install pen-stack[discover,target,safe]      # specific modules
```

## Biological Foundation

Built on the IS110 bridge recombinase system (Durrant & Perry et al. *Nature* 2024;
Hiraizumi et al. *Nature* 2024; Perry et al. *Science* 2025; Pelea et al. *Science* 2026).
IS621 attB core dinucleotide: **CT** (verified PDB 8WT6).

## Citation

```bibtex
@software{pen-stack,
  author = {Mahaboob Ali, Anees Ahmed},
  title  = {PEN-STACK: Comprehensive Computational Platform for Non-Destructive Genome Engineering},
  year   = {2026},
  url    = {https://github.com/ahmedanees-m/pen-stack}
}
```

## License

MIT (c) Anees Ahmed Mahaboob Ali
