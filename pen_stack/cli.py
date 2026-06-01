"""PEN-STACK unified CLI. Subcommands are wired up per-phase (atlas, score, writable, bridge, plan)."""
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


if __name__ == "__main__":
    main()
