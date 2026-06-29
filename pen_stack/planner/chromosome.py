"""Chromosome validation, gene/chromosome concordance, and chromosome-context advisories (v7.1.5).

The `chrom` field on a design was previously a free-text pass-through with no validation and no downstream
effect. This module makes it meaningful WITHOUT fabricating a score: the engine's per-locus safety / durability /
accessibility / off-target numbers are indexed by the GENE's resolved genomic coordinates via the writability
atlas (`planner.optimize.gene_region`), not by a free-text chromosome string - a bare "chrX" with no position
cannot index a specific locus value. So the honest, grounded use of the field is:

  * `canonical_chromosome` - validate / normalise to a standard human chromosome (chr1-chr22, chrX, chrY, chrM);
  * `gene_chromosome` - the gene's canonical chromosome from the gene-coordinate table;
  * `chromosome_concordance` - flag when the entered chromosome does not match the named gene's real location
    (the "BRCA1 is on chr17, not chr1" case), making explicit that scoring uses the gene's canonical locus;
  * `chromosome_context` - chromosome-driven advisories that ARE grounded in biology: chrM is not addressable by
    nuclear genome-writing tools (mtDNA needs DdCBE/TALED - out of scope), chrY is male-specific with ampliconic
    repeats, chrX is hemizygous in 46,XY vs X-inactivated in 46,XX.
"""
from __future__ import annotations

import re

STANDARD_CHROMOSOMES = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM"]


def canonical_chromosome(chrom: str | None) -> str | None:
    """Normalise a chromosome string to canonical UCSC form (chr1..chr22, chrX, chrY, chrM), or None if it is not
    a standard human chromosome. Accepts 'chrX'/'X'/'x', 'chr1'/'1', 'chrM'/'chrMT'/'MT', '23'->X, '24'->Y."""
    if chrom is None:
        return None
    c = re.sub(r"\s+", "", str(chrom)).lower()
    if not c:
        return None
    if c.startswith("chr"):
        c = c[3:]
    c = {"mt": "m", "23": "x", "24": "y", "25": "m"}.get(c, c)
    if c in {"x", "y", "m"}:
        return "chr" + c.upper()
    if c.isdigit() and 1 <= int(c) <= 22:
        return "chr" + c
    return None


def gene_chromosome(gene: str | None) -> str | None:
    """The canonical chromosome of a gene (or safe-harbour locus nickname), from the gene-coordinate table; None
    if the gene is unknown."""
    if not gene:
        return None
    try:
        from pen_stack.planner.optimize import gene_region
        reg = gene_region(gene)
    except Exception:  # noqa: BLE001 - coords table absent (bare checkout) -> cannot resolve, do not fabricate
        return None
    return canonical_chromosome(reg[0]) if reg else None


def chromosome_concordance(gene: str | None, chrom: str | None) -> dict:
    """Validate the entered chromosome and check it against the named gene's canonical location.

    status is one of:
      * 'invalid'  - the entered string is not a standard human chromosome;
      * 'mismatch' - valid, but does not match the gene's canonical chromosome (the silent-mismatch case);
      * 'match'    - matches the gene's canonical chromosome;
      * 'unverifiable' - valid chromosome but the gene's location is unknown (cannot confirm);
      * 'none'     - no chromosome supplied.
    """
    entered = canonical_chromosome(chrom)
    gchrom = gene_chromosome(gene)
    out = {"entered_raw": chrom, "entered": entered, "valid": entered is not None,
           "gene": gene, "gene_chrom": gchrom}
    if chrom in (None, "") or str(chrom).strip() == "":
        out["status"] = "none"
        out["message"] = None
    elif entered is None:
        out["status"] = "invalid"
        out["message"] = (f"'{chrom}' is not a standard human chromosome. Use chr1-chr22, chrX, chrY, or chrM.")
    elif gchrom and entered != gchrom:
        out["status"] = "mismatch"
        out["message"] = (f"{gene} is on {gchrom}, not {entered}. Locus scoring uses {gene}'s canonical location "
                          f"({gchrom}); the entered chromosome does not move the locus.")
    elif gchrom and entered == gchrom:
        out["status"] = "match"
        out["message"] = f"{entered} matches the canonical location of {gene}."
    else:
        out["status"] = "unverifiable"
        out["message"] = (f"{entered} is a valid chromosome, but {gene or 'the gene'} is not in the coordinate "
                          "table, so the gene/chromosome match cannot be confirmed.")
    return out


def chromosome_context(chrom: str | None) -> dict | None:
    """A grounded, chromosome-driven advisory (or None for an autosome). These are real biological constraints
    the chromosome identity alone implies; magnitudes remain locus/subject-dependent (not predicted here)."""
    c = canonical_chromosome(chrom)
    if c == "chrM":
        return {"chrom": "chrM", "severity": "high",
                "note": ("the mitochondrial genome is NOT addressable by nuclear genome-writing tools "
                         "(integrases / recombinases / nuclear-targeted Cas9); mtDNA editing requires "
                         "mitochondrially-targeted base editors (DdCBE / TALED) - out of scope for this tool.")}
    if c == "chrY":
        return {"chrom": "chrY", "severity": "medium",
                "note": ("the Y chromosome is male-specific (absent in 46,XX) and rich in ampliconic / palindromic "
                         "repeats, so confirm the target is single-copy before trusting a unique-site assumption.")}
    if c == "chrX":
        return {"chrom": "chrX", "severity": "low",
                "note": ("the X chromosome is hemizygous in 46,XY (one copy) but subject to X-inactivation in "
                         "46,XX (mosaic expression); dosage and durability are sex- and locus-dependent.")}
    return None
