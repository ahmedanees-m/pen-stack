"""PEN-STACK unified CLI (subcommands wired per-phase: atlas, score, writable, crosslink, monitor).

One entry point — ``pen-stack`` — over the whole stack. Heavy data (the Phase-1 writability atlas) is
loaded lazily and degrades gracefully when absent, so ``info`` / ``atlas`` work from a clean install.
"""
from __future__ import annotations

import click

from pen_stack import __version__


@click.group()
@click.version_option(__version__, prog_name="pen-stack")
def main():
    """PEN-STACK — open infrastructure for genome writing."""


@main.command()
def info():
    """Show stack status and module map."""
    click.echo(f"PEN-STACK v{__version__}")
    click.echo("Pillar B (flagship): wgenome  — Writable Genome (safety x durability x reachability)")
    click.echo("Pillar A (companion): atlas, mech, score — Writer Atlas + WT-KB")
    click.echo("Engine: planner — Write Planner (inverse design)")
    click.echo("Beachhead: bridge — bridge-recombinase off-target engine")
    click.echo("Services: monitor, rag, agent, ui, server")


@main.command()
@click.option("--family", default=None, help="Filter to one writer family.")
@click.option("--coverage", is_flag=True, help="Show per-family coverage + confidence breakdown.")
@click.option("--limit", default=10, help="Max rows to print.")
def atlas(family, coverage, limit):
    """Query the Writer Atlas."""
    import pandas as pd

    from pen_stack.atlas.crosslink import _ATLAS
    df = pd.read_parquet(_ATLAS)
    if coverage:
        cov = (df.groupby("family")
                 .agg(n=("representative_system", "size"),
                      measured=("confidence", lambda s: (s == "measured").sum()),
                      tier=("reachability_tier", "first"))
                 .reset_index())
        click.echo(cov.to_string(index=False))
        click.echo(f"\nTOTAL systems: {len(df):,} across {df['family'].nunique()} families")
        return
    if family:
        df = df[df["family"] == family]
    cols = [c for c in ["representative_system", "family", "confidence", "deliv_class",
                        "readiness", "reachability_tier"] if c in df.columns]
    click.echo(df[cols].head(limit).to_string(index=False))


@main.command()
@click.option("--gene", required=True, help="Target gene symbol.")
@click.option("--ct", default="k562", help="Cell type (k562/hepg2/hspc).")
@click.option("--top", default=10, help="Top writable bins to show.")
def writable(gene, ct, top):
    """Rank writable loci overlapping a gene."""
    from pen_stack.atlas.crosslink import loci_for_gene
    try:
        g = loci_for_gene(gene, ct)
    except FileNotFoundError as e:
        raise click.ClickException(f"Phase-1 writability atlas not available: {e}") from e
    if g.empty:
        click.echo(f"No writable bins found for {gene} in {ct}.")
        return
    click.echo(g[["chrom", "bin", "safety", "p_durable", "writability"]].head(top).to_string(index=False))


@main.command()
@click.option("--family", help="Writer family -> ranked reachable loci.")
@click.option("--chrom", help="Locus chrom (with --bin) -> reachable writers.")
@click.option("--bin", "bin_idx", type=int, help="Locus 1kb bin index.")
@click.option("--ct", default="k562")
@click.option("--top", default=10)
def crosslink(family, chrom, bin_idx, ct, top):
    """Writer<->locus cross-link queries."""
    from pen_stack.atlas import crosslink as cl
    try:
        if family:
            click.echo(cl.loci_for_writer(family, ct, top=top).to_string(index=False))
        elif chrom and bin_idx is not None:
            click.echo(cl.writers_for_locus(chrom, bin_idx, ct).head(top).to_string(index=False))
        else:
            raise click.UsageError("provide --family OR (--chrom and --bin)")
    except FileNotFoundError as e:
        raise click.ClickException(f"Phase-1 writability atlas not available: {e}") from e


@main.command()
@click.option("--gene", required=True, help="Target gene symbol.")
@click.option("--intent", required=True,
              type=click.Choice(["safe_harbour_insertion", "knock_in_with_disruption",
                                 "high_durability_insertion", "regulatory_excision", "repeat_excision"]))
@click.option("--cargo-bp", default=2000, help="Payload size (bp).")
@click.option("--ct", default="k562", help="Cell type (k562/hepg2/hspc).")
@click.option("--k", default=3, help="Number of ranked plans.")
def plan(gene, intent, cargo_bp, ct, k):
    """Write Planner: goal + edit_intent -> ranked, traceable plans."""
    from pen_stack.planner.optimize import EditIntent
    from pen_stack.planner.pipeline import plan_write
    from pen_stack.planner.report import render_plans
    try:
        plans = plan_write(gene, EditIntent(intent), cargo_bp, ct, k=k)
    except FileNotFoundError as e:
        raise click.ClickException(f"Phase-1 writability atlas not available: {e}") from e
    click.echo(render_plans(plans))


@main.command()
@click.option("--since", default="2026-01-01", help="Earliest publication date (YYYY-MM-DD).")
@click.option("--back-test", is_flag=True, help="Run the ISPpu10 back-test window.")
def monitor(since, back_test):
    """Run PEN-MONITOR (Europe PMC living-database scan -> curation queue)."""
    from pen_stack.monitor.run import run_monitor
    res = run_monitor(since=since, back_test=back_test)
    click.echo(f"PEN-MONITOR: {res['n_hits']} hits, {res['n_candidates']} candidates -> {res['queue']}")
    if res.get("isppu10_found") is not None:
        click.echo(f"ISPpu10 back-test: {'FOUND' if res['isppu10_found'] else 'not found'}")


if __name__ == "__main__":
    main()
