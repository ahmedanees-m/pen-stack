"""PASTE / (ee)PASSIGE off-target composition (PEN-OFFTGT v2, O-WS6) — NEW.

PASTE installs a landing-site attB with a prime editor (a Cas9 **nickase** + reverse transcriptase directed by a
pegRNA), then a serine **integrase** (Bxb1) inserts the cargo at the installed attB. Its off-target profile is
therefore the COMPOSITION of two mechanisms, each with its own status:
  * the Cas9-nickase off-targets of the pegRNA spacer  -> the validated nuclease finder (O-WS2), and
  * the integrase pseudo-attP sites of the installed att -> the semi-validated integrase scan (O-WS3).

Returns BOTH candidate sets, labelled by component, and recommends BOTH a nuclease assay and an integrase assay.
Never fabricates; each component carries its own truthful status.
"""
from __future__ import annotations

from pen_stack.wgenome.offtarget_integrase import nominate_integrase
from pen_stack.wgenome.offtarget_nuclease import find_nuclease_offtargets


def nominate_paste(guide: str | None = None, integrase: str = "Bxb1", max_mismatch: int = 5,
                   assay: str = "guideseq", cell_type: str = "k562", top: int = 20) -> dict:
    """Compose the nuclease (pegRNA-directed Cas9 nickase) and integrase (installed attB) off-target components.
    Returns both candidate sets with their own statuses + the dual confirm-assay recommendation. Abstains per
    component when its input/cache is unavailable (never fabricates)."""
    nuclease = (find_nuclease_offtargets(guide, "SpCas9", max_mismatch=max_mismatch, assay=assay,
                                         cell_type=cell_type, top=top)
                if guide else {"available": False, "abstain": True, "status": "validated",
                               "note": "provide the pegRNA spacer (guide) for the Cas9-nickase off-target scan"})
    integ = nominate_integrase(integrase, top=top)
    statuses = {"nuclease_component": nuclease.get("status", "validated"),
                "integrase_component": integ.get("status", "mechanism_based_unvalidated")}
    return {"family": "paste", "available": True, "abstain": False, "status": "composite",
            "component_statuses": statuses,
            "nuclease_component": nuclease,   # Cas9-nickase off-targets (pegRNA-directed) — validated finder
            "integrase_component": integ,     # installed-attB pseudo-attP — semi-validated scan
            "confirm_assay": {"nuclease": ["GUIDE-seq", "CHANGE-seq"], "integrase": ["Cryptic-seq", "HIDE-seq"],
                              "note": "PASTE requires BOTH a nuclease off-target assay (for the nickase) AND an "
                                      "integrase off-target assay (for the installed att)."},
            "method": ("compose the validated nuclease finder (nickase, pegRNA spacer) with the semi-validated "
                       "integrase pseudo-attP scan (installed att); return both candidate sets by component"),
            "honesty": "two component candidate sets, each with its own status; NOT a clearance. Confirm with "
                       "both a nuclease assay and an integrase assay.",
            "nomination_is_not_clearance": True}
