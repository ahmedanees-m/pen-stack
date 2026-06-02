"""pen-bridge CLI (Phase 1.5, Step 1.5.5) — the first public instrument of PEN-STACK.

    pen-bridge design --target <14nt> --donor <14nt> [--scaffold ISCro4_enhanced] [--ct k562]

Designs the bridge RNA (wrapped Arc designer) and reports off-target + fold/cross-loop QC.
"""
from __future__ import annotations

import json

import click


@click.group()
def main():
    """pen-bridge — bridge-recombinase design + off-target/QC (PEN-STACK)."""


@main.command()
@click.option("--target", "-t", required=True, help="14 nt target core (DNA).")
@click.option("--donor", "-d", required=True, help="14 nt donor core (DNA).")
@click.option("--scaffold", "-s", default="ISCro4_enhanced",
              type=click.Choice(["IS621", "ISCro4_WT", "ISCro4_enhanced"]))
@click.option("--ct", default=None, help="Overlay Phase-1 safety for this cell type (k562/hepg2/hspc).")
@click.option("--no-scan", is_flag=True, help="Skip the genome-wide off-target scan (QC only).")
@click.option("--chroms", default=None, help="Comma-separated chroms to scan (default chr1..22,X).")
def design(target, donor, scaffold, ct, no_scan, chroms):
    """Design a bridge RNA and assess off-target + fold/cross-loop QC."""
    from pen_stack.bridge.pipeline import design_and_assess
    chrom_list = chroms.split(",") if chroms else None
    res = design_and_assess(target, donor, scaffold, chroms=chrom_list, ct=ct, scan=not no_scan)
    brna, off, qc = res["brna"], res["offtargets"], res["qc"]
    click.echo(f"Bridge RNA ({scaffold}): target={brna['target']} donor={brna['donor']}")
    if brna.get("available"):
        click.echo(f"  bridge_sequence: {brna['bridge_sequence'][:80]}… ({len(brna['bridge_sequence'])} nt)")
    else:
        click.echo(f"  (designer: {brna['note']})")
    click.echo(f"QC: cross-loop {qc['cross_loop']}  pass={qc['pass']}")
    if "fold" in qc and qc["fold"].get("available"):
        click.echo(f"    fold MFE: {qc['fold']['mfe']}")
    if off.get("scanned"):
        click.echo(f"Off-target: {off['n_candidates']} candidate pseudosites "
                   f"({off['n_exact']} exact); top by risk:")
        t = off["table"]
        cols = [c for c in ["chrom", "pos", "site", "n_mm", "risk", "safety"] if c in t.columns]
        click.echo(t.head(10)[cols].to_string(index=False))
    else:
        click.echo(f"Off-target: {off.get('note', 'not scanned')}")
    click.echo(res["disclaimer"])


@main.command()
def profile():
    """Show the position-weight off-target profile (and its provenance)."""
    from pen_stack.bridge.ingest import load_profile_config
    cfg = load_profile_config()
    click.echo(json.dumps({"core_length": cfg["core_length"],
                           "central_core_positions": cfg["central_core_positions"],
                           "max_mismatches": cfg["max_mismatches"],
                           "protective_weight": cfg["protective_weight"],
                           "provenance": cfg["provenance"]}, indent=2))


if __name__ == "__main__":
    main()
