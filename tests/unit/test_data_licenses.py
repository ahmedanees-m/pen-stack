"""WS-LIC (v6.6), the license gate: the SHIPPED artifact contains open data only.

Restricted sources (COSMIC, OncoKB) may be CITED, and may be pulled LOCALLY via the bring-your-own-license fetcher,
but must NOT be the source of any shipped DERIVED-DATA artifact, and no raw restricted gene-list may be committed.
This test fails the build if that invariant is broken.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[2]


def test_data_licenses_manifest_exists_and_names_cancermine():
    md = (_ROOT / "DATA_LICENSES.md").read_text(encoding="utf-8")
    assert "CancerMine" in md and "CC0" in md
    assert "OncoKB" in md and "COSMIC" in md # both documented as restricted / not-shipped
    assert "open data only" in md.lower()


def test_genotox_oracle_is_sourced_from_cancermine_not_cosmic_oncokb():
    """The one SHIPPED derived-data artifact built on the oncogene list: its provenance must be CancerMine (CC0),
    not COSMIC/OncoKB."""
    cfg = yaml.safe_load((_ROOT / "configs/genotoxicity_oracle.yaml").read_text(encoding="utf-8"))
    onco_src = str(cfg.get("inputs", {}).get("oncogenes", "")).lower()
    assert "cancermine" in onco_src
    assert "cosmic" not in onco_src and "oncokb" not in onco_src
    # the CancerMine DOI is in the provenance; the COSMIC-CGC methodology DOI is not asserted as the data source
    dois = " ".join(cfg.get("provenance_dois", []))
    assert "10.1038/s41592-019-0422-y" in dois # CancerMine


def test_no_restricted_gene_list_committed_to_the_repo():
    """No raw COSMIC/OncoKB gene-list file may be committed (only the user's local, gitignored copy)."""
    bad = []
    for p in list(_ROOT.glob("**/*.tsv")) + list(_ROOT.glob("**/*.csv")):
        if any(seg in str(p) for seg in (".git", "node_modules", "licensed_data", "site-packages")):
            continue
        try:
            head = p.read_text(encoding="utf-8", errors="ignore")[:600]
        except Exception: # noqa: BLE001
            continue
        # OncoKB export signature (the cancerGeneList.tsv) or a COSMIC CGC export header
        if ("OncoKB Annotated" in head) or ("MSK-IMPACT" in head) or ("ROLE_IN_CANCER" in head and "GENOME_START" in head):
            bad.append(str(p.relative_to(_ROOT)))
    assert not bad, f"restricted gene-list file(s) committed (must be local-only): {bad}"


def test_cancermine_loader_is_the_default_source():
    # read the source text (CI-safe: ingest_safety_annot imports pybedtools, which needs the bedtools binary)
    src = (_ROOT / "pen_stack/data/ingest_safety_annot.py").read_text(encoding="utf-8")
    assert "def load_cancermine(" in src
    assert 'source: str = "cancermine"' in src # CancerMine is the shipped default
    assert "10.1038/s41592-019-0422-y" in src # CancerMine DOI cited in the loader
