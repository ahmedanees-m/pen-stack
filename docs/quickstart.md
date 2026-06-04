# Quickstart - run a Genome-Writing Bench task in under five minutes

This is the fastest path from a clean checkout to a reproducible benchmark result. It needs only the core
install; tasks that require the large Phase-1 atlas or the copyrighted Perry tables report `available: false`
rather than failing, so the command always succeeds.

## 1. Install (about 1 minute)

```bash
git clone https://github.com/ahmedanees-m/pen-stack.git && cd pen-stack
pip install -e ".[dev]"          # core + tests (numpy/pandas/scikit-learn/lightgbm)
```

## 2. Run the bench (about 1 minute)

```bash
python bench/run.py              # deterministic solvers -> out/bench_results.json + LEADERBOARD.md
```

You get a leaderboard comparing the deterministic planner against the naive baseline on every available
task, and the no-fabrication hard gate (T6), which runs without any model:

```
tasks available: .../6 ; planner beats naive on N/M ; agent no-fabrication: True
-> out/bench_results.json
-> benchmarks/genome_writing_bench/LEADERBOARD.md
```

## 3. Add the LLM agent (optional, about 2 minutes)

```bash
python bench/run.py --agent      # also runs the real LLM orchestrator as the llm_agent solver
```

The agent reaches the planner's numbers **only by grounding every value in a tool call** - it is
disqualified if it fabricates. With no model server reachable it degrades to the deterministic state machine
in seconds (no hang). To use a local model, point `configs/llm.yaml` at Ollama and `ollama pull
qwen2.5:7b-instruct`; otherwise set `NVIDIA_API_KEY` for the hosted fallback.

## 4. Verify the frozen reference set

```bash
python bench/run.py --verify     # checks benchmarks/genome_writing_bench/SHA256SUMS
```

## On a clean Docker image

```bash
docker compose run --rm bench python bench/run.py --agent
```

## What the tasks measure

| Task | Family | Scorer | Ground truth |
|---|---|---|---|
| site_selection_blind_gsh | site selection | blind GSH discovery AUROC | DOI-validated safe harbours vs matched controls |
| writer_family_recovery | writer selection | recovery@1 vs prevalence | DOI-documented writes across 4 families |
| within_locus_ranking | within-locus | fraction in top quartile | documented integration bins |
| bridge_offtarget_discrimination | off-target | model vs Hamming AUROC | Perry et al. 2025 measured off-targets |
| intent_specification_compliance | intent | specification-correct cases | edit-intent table |
| agent_no_fabrication | no-fabrication | hard gate: 0 fabricated | agent trace = direct tool calls |

No task is scored against a circular label. To submit a solver, see the
[leaderboard submission guide](../benchmarks/genome_writing_bench/SUBMISSIONS.md).
