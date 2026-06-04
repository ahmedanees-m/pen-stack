# Dissemination log (WS-H3)

A benchmark with no users has no impact, so dissemination is tracked as first-class work. This log records
the plan and the running state; adoption metrics are updated as they accrue.

## Channels

- **Preprints.** Post M1, M2, M3 to bioRxiv / arXiv as each completes. M2 is framed explicitly as the
  writing-side benchmark complementing editing-side tooling (`docs/positioning.md`). Drafts in `manuscripts/`.
- **Code + benchmark release.** PyPI (`pip install pen-stack`), a tagged GitHub release per milestone, a
  clean Docker image, the MCP server documented for agent developers (`docs/MCP.md`), and a five-minute
  quickstart (`docs/quickstart.md`).
- **Leaderboard.** Public `benchmarks/genome_writing_bench/LEADERBOARD.md`; open call for submissions
  (`benchmarks/genome_writing_bench/SUBMISSIONS.md`); the no-fabrication gate is mandatory for agents.
- **Communities.** Announce to the agentic-bio and genome-engineering research communities; engage relevant
  venues' datasets/benchmarks tracks; invite external LLM-agent baselines onto the board.

## Adoption metrics (to track)

| Metric | Source | State |
|---|---|---|
| GitHub stars / forks | repo | tracked from release |
| PyPI installs | PyPI stats | from first release |
| Leaderboard submissions | PRs titled `bench-submission:` | open |
| Citations | Google Scholar / Semantic Scholar | from preprints |
| Connected-repo reuse | the five prior repos + downstream | ongoing |

## Release checklist (per milestone)

1. All workstream tests green; CI green; single contributor; pre-registration SHA-locked.
2. `CHANGELOG.md` entry; version bumped; README + badges updated.
3. Tagged GitHub release; Zenodo deposit (data) with DOI.
4. Preprint posted; `docs/positioning.md` updated; this log updated.
5. Leaderboard refreshed; submission guide linked from the announcement.
