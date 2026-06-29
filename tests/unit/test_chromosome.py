"""Chromosome validation + gene/chromosome concordance + chromosome-context advisories (v7.1.5). CI-safe."""
from __future__ import annotations

import pytest

from pen_stack.planner.chromosome import (
    canonical_chromosome,
    chromosome_concordance,
    chromosome_context,
)


@pytest.mark.parametrize("raw,expect", [
    ("chrX", "chrX"), ("X", "chrX"), ("x", "chrX"), ("chr1", "chr1"), ("1", "chr1"), ("22", "chr22"),
    ("chrM", "chrM"), ("chrMT", "chrM"), ("MT", "chrM"), ("23", "chrX"), ("24", "chrY"), ("chrY", "chrY"),
    ("chrZZZ", None), ("chr99", None), ("chr0", None), ("", None), (None, None), ("banana", None),
])
def test_canonical_chromosome(raw, expect):
    assert canonical_chromosome(raw) == expect


def test_invalid_chromosome_is_flagged():
    r = chromosome_concordance("BRCA1", "chrZZZ")
    assert r["status"] == "invalid" and not r["valid"]


def test_gene_chromosome_mismatch_is_flagged():
    # BRCA1 is on chr17; entering chr1 must be flagged a mismatch naming the real chromosome.
    r = chromosome_concordance("BRCA1", "chr1")
    if r["gene_chrom"] is None:
        pytest.skip("gene coordinate table absent (bare checkout); concordance unverifiable")
    assert r["status"] == "mismatch" and r["gene_chrom"] == "chr17" and "chr17" in r["message"]


def test_gene_chromosome_match_is_clean():
    r = chromosome_concordance("F9", "chrX")
    if r["gene_chrom"] is None:
        pytest.skip("gene coordinate table absent")
    assert r["status"] == "match" and r["gene_chrom"] == "chrX"


def test_unknown_gene_is_unverifiable_not_a_false_match():
    r = chromosome_concordance("NOTAREALGENE123", "chr5")
    assert r["status"] == "unverifiable" and r["gene_chrom"] is None


def test_chromosome_context_grounded_advisories():
    assert chromosome_context("chrM")["severity"] == "high" and "mitochond" in chromosome_context("chrM")["note"]
    assert chromosome_context("chrY")["chrom"] == "chrY"
    assert chromosome_context("chrX")["chrom"] == "chrX"
    assert chromosome_context("chr7") is None  # autosome: no special advisory
