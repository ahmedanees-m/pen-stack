# Distribution

Where PEN-STACK and its benchmark are published, and what each channel carries.

## Channels

- **Package.** PyPI: `pip install pen-stack`. A tagged GitHub release accompanies each version, with a
  pinned Docker image.
- **Agent interface.** The MCP server is documented for agent developers in [`MCP.md`](MCP.md); a
  five-minute path through the system is in [`quickstart.md`](quickstart.md).
- **Benchmark.** The Genome-Writing Bench leaderboard is
  [`benchmarks/genome_writing_bench/LEADERBOARD.md`](../benchmarks/genome_writing_bench/LEADERBOARD.md) and
  is open to external solvers; the submission route and its rules are in
  [`SUBMISSIONS.md`](../benchmarks/genome_writing_bench/SUBMISSIONS.md). The no-fabrication gate is
  mandatory for agent submissions.
- **Archive.** A Zenodo deposit carries the data and results for each release, with a DOI recorded in
  `CITATION.cff`.
- **Positioning.** How the writing-side benchmark relates to editing-side tooling is set out in
  [`positioning.md`](positioning.md).
