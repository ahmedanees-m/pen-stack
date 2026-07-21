# PEN-STACK - one-command reproduction (GigaScience reproducibility criterion).
#
#   make install      install the package (editable) with dev extras
#   make test         run the unit test suite
#   make repro        reproduce every result that runs on the committed data + demo atlas (no download)
#   make fetch        download the full released atlas + models from Zenodo (needs ZENODO_DOI)
#   make repro-full   make fetch, then also run the genome-wide atlas benchmarks
#   make help         show this help
#
# lightgbm needs the OpenMP runtime. On a minimal Debian image, first run: apt-get install -y libgomp1
# (standard Linux/conda/macOS environments already provide it; CI runs on such an image).

PYTHON ?= python3

.DEFAULT_GOAL := help
.PHONY: help install fetch test repro repro-human repro-full

help:
	@echo "PEN-STACK reproduction targets:"
	@echo "  make install      pip install -e .[dev]"
	@echo "  make test         run the unit test suite (pytest -q)"
	@echo "  make repro        reproduce results from committed data + the demo atlas (no download, no key)"
	@echo "  make repro-human  recompute the headline human K562 expression-robustness result from source data"
	@echo "  make fetch        download the full atlas + models from Zenodo (set ZENODO_DOI)"
	@echo "  make repro-full   make fetch, then also run the genome-wide atlas benchmarks"
	@echo ""
	@echo "  Override the interpreter with e.g.  make repro PYTHON=python"
	@echo "  lightgbm needs libgomp; on a minimal Debian image first run: apt-get install -y libgomp1"

install:
	$(PYTHON) -m pip install -e '.[dev]'

fetch:
	bash scripts/fetch_artifacts.sh

test:
	$(PYTHON) -m pytest -q

# One-command reproduction on a FRESH CLONE: every result that runs on the committed artifacts and the
# chr19 demo atlas, with no external download and no API key. The genome-wide atlas benchmarks (which need
# the full Zenodo release) are in repro-full.
repro:
	$(PYTHON) scripts/reproduce.py
	@echo ""
	@echo "== Headline result recomputed from source: human K562 expression-robustness head =="
	$(PYTHON) scripts/p2_build_human_head.py
	@echo ""
	@echo "== Prior-art distinctness recomputed from source: durability axis vs ePRIDICT =="
	$(PYTHON) scripts/pa_epridict_distinctness.py
	@echo ""
	@echo "== Genome-Writing Bench integrity check (frozen SHA256SUMS) + PEN-Agent no-fabrication gate =="
	$(PYTHON) bench/run.py --verify
	$(PYTHON) bench/run.py --agent

# Recompute the headline human K562 expression-robustness result from the committed Leemans source data,
# training the shipped twin on the chr3/8/12-held-out split and asserting the correlation matches the metrics.
repro-human:
	$(PYTHON) scripts/p2_build_human_head.py

# Full reproduction: fetch the released atlas + models, then run repro plus the genome-wide benchmarks.
repro-full: fetch
	$(MAKE) repro PYTHON=$(PYTHON)
	@echo ""
	@echo "== Position-effect benchmark (TPE-Bench, sealed chrom_holdout leaderboard) =="
	$(PYTHON) -c "from benchmarks.position_effect.harness import baseline_leaderboard as b; import json; print(json.dumps(b(), indent=2, default=str))"
	@echo ""
	@echo "== GSH safe-harbour discrimination benchmark (learned model vs GSH rule-set) =="
	$(PYTHON) -m pen_stack.wgenome.gsh_baseline
