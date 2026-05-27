"""CLI for PEN-COMPARE."""

from __future__ import annotations

import click

from pen_stack._version import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context) -> None:
    """PEN-COMPARE: Hierarchical Certification Framework for Non-Destructive Genome Editors."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("editor_a")
@click.argument("editor_b")
def compare(editor_a: str, editor_b: str) -> None:
    """Compare two genome editors side-by-side."""
    click.echo(f"Comparing {editor_a} vs {editor_b} ... (implementation pending Step 25)")


@main.command(name="list-writers")
def list_writers() -> None:
    """List all certified TRUE_WRITER editors."""
    click.echo("TRUE_WRITER listing ... (implementation pending Step 12)")


if __name__ == "__main__":
    main()
