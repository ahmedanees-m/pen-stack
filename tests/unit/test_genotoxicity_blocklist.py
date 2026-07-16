"""The reject-known-bad genotoxicity blocklist: documented clinical insertional-oncogenesis
loci are flagged unsafe by rule, closing the BMI1/SETBP1/MN1 false negatives of the soft safety model."""
from __future__ import annotations

import pandas as pd

from pen_stack.wgenome.genotoxic_blocklist import (
    BIN_BP,
    apply_genotoxic_blocklist,
    blocklist_config,
    blocklisted_bins,
    is_genotoxic_locus,
)

# The complete documented clinical set (2025 Leukemia review + primary trials). The three that the six-gene
# soft-model label missed -- and that scored SAFE before this overlay -- must all be present.
_DOCUMENTED = {"LMO2", "CCND2", "MECOM", "PRDM16", "HMGA2", "SETBP1", "BMI1", "MN1"}
_FORMER_FALSE_NEGATIVES = {"SETBP1", "BMI1", "MN1"}


def test_blocklist_covers_all_documented_loci():
    cfg = blocklist_config()
    listed = {r["gene"] for r in cfg["loci"]}
    assert _DOCUMENTED <= listed, f"missing documented loci: {_DOCUMENTED - listed}"
    genes_with_bins = {m["gene"] for m in blocklisted_bins().values()}
    assert _DOCUMENTED <= genes_with_bins, f"documented loci with no resolved bins: {_DOCUMENTED - genes_with_bins}"
    # every gene carries a trial citation (provenance, not a bare name)
    assert all(r.get("citation") for r in cfg["loci"])


def test_former_false_negatives_are_now_flagged():
    """BMI1/SETBP1/MN1 previously scored safe (BMI1 at the 99.9th writability percentile). They must now be
    flagged unsafe by the deterministic overlay."""
    from pen_stack.planner.optimize import gene_coords_path
    gc = pd.read_parquet(gene_coords_path()).set_index("gene")
    for gene in _FORMER_FALSE_NEGATIVES:
        mid = int((gc.loc[gene, "start"] + gc.loc[gene, "end"]) // 2)
        hit = is_genotoxic_locus(gc.loc[gene, "chrom"], mid)
        assert hit is not None and hit["gene"] == gene, f"{gene} not flagged as genotoxic"


def test_overlay_zeroes_safety_for_documented_and_spares_innocent():
    from pen_stack.planner.optimize import gene_coords_path
    gc = pd.read_parquet(gene_coords_path()).set_index("gene")
    bmi1 = gc.loc["BMI1"]
    df = pd.DataFrame({
        "chrom": [bmi1["chrom"], "chr19"],
        "bin": [int((bmi1["start"] + bmi1["end"]) // 2) // BIN_BP, 5000],
        "safety": [1.0, 0.9], "p_durable": [0.8, 0.8], "writability": [0.99, 0.85],
    })
    out = apply_genotoxic_blocklist(df)
    bl = out[out["genotoxic_blocklist"]]
    assert (bl["safety"] == 0.0).all() and (bl["writability"] < 0.9).all()
    assert out.loc[out["chrom"] == "chr19", "safety"].iloc[0] == 0.9  # innocent bin untouched


def test_overlay_is_noop_on_a_non_atlas_frame():
    df = pd.DataFrame({"gene": ["X"], "value": [1.0]})
    assert apply_genotoxic_blocklist(df).equals(df)
