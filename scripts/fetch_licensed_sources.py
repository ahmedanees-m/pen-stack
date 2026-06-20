"""Bring-your-own-license fetcher (v6.6, WS-LIC), OPTIONAL local enrichment.

PEN-STACK ships open data only (CancerMine/DepMap/gnomAD/ClinGen/GENCODE). This script lets a REGISTERED academic
user pull license-restricted sources (COSMIC, OncoKB) into a gitignored `licensed_data/` under THEIR OWN license,
to enrich/validate the screen LOCALLY. The repo never contains that data; this only automates the user's own
licensed download (you still authenticate / accept the license yourself).

After fetching COSMIC, rebuild the safety features with the restricted source locally:
    python -m pen_stack.data.ingest_safety_annot --source cosmic --cosmic licensed_data/cosmic_cgc.tsv ...

Usage:
    python scripts/fetch_licensed_sources.py --source cosmic # prints instructions; never bypasses the license
    python scripts/fetch_licensed_sources.py --source oncokb
"""
from __future__ import annotations

import argparse
from pathlib import Path

_LICENSED_DIR = Path("licensed_data") # gitignored

_INSTRUCTIONS = {
    "cosmic": (
        "COSMIC Cancer Gene Census, free for academic use WITH registration; NO redistribution.\n"
        " 1. Register/login at https://cancer.sanger.ac.uk/cosmic/register\n"
        " 2. Download 'Cancer Gene Census' (GRCh38 TSV) under YOUR account.\n"
        f" 3. Save it to {_LICENSED_DIR}/cosmic_cgc.tsv (this dir is gitignored, never commit it).\n"
        " 4. Rebuild locally: python -m pen_stack.data.ingest_safety_annot --source cosmic "
        f"--cosmic {_LICENSED_DIR}/cosmic_cgc.tsv\n"
        " NOTE: the SHIPPED default is CancerMine (CC0); COSMIC is local-only enrichment under your own license."
    ),
    "oncokb": (
        "OncoKB, academic API license; NO ML training, NO redistribution. VALIDATION/benchmarking only, with\n"
        "written permission.\n"
        " 1. Register at https://www.oncokb.org/account/register and request API/academic access.\n"
        " 2. Email OncoKB describing your benchmarking use case to obtain written permission.\n"
        f" 3. Download the cancer gene list to {_LICENSED_DIR}/oncokb_cancerGeneList.tsv (gitignored).\n"
        " 4. Use it ONLY to validate/benchmark locus flags, never as training data, never committed."
    ),
}


def main() -> None:
    ap = argparse.ArgumentParser(description="BYO-license fetcher for COSMIC/OncoKB (local-only enrichment).")
    ap.add_argument("--source", choices=sorted(_INSTRUCTIONS), required=True)
    a = ap.parse_args()
    _LICENSED_DIR.mkdir(exist_ok=True)
    (_LICENSED_DIR / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8") # belt-and-braces
    print("=" * 78)
    print(f"Bring-your-own-license: {a.source.upper()} (PEN-STACK ships CancerMine/CC0 by default)")
    print("=" * 78)
    print(_INSTRUCTIONS[a.source])
    print("\nThis tool does NOT download restricted data for you, it documents your own licensed download.")


if __name__ == "__main__":
    main()
