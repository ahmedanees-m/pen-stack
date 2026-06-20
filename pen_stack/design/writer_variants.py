"""Writer-variant critique, serine-integrase hyperactive mutants (v6.8 PEN-WRITER, C-WS4).

Extends the v4.0 writer-verification (`atlas.writer_verify`, which scores ISCro4 bridge-recombinase variants
against the Perry DMS) to the **serine integrases**, using the directed-evolution hyperactive-mutant tables of
Hew, Gupta, Sato et al. (Nucleic Acids Res 2024, 52(14):e64, 10.1093/nar/gkae534) and the foundational PhiC31
mutants of Keravala et al. (Mol Ther 2009, 10.1038/mt.2008.241).

Scope spine (carried from v4.0): a variant score is a CANDIDATE plausibility, never a measured-activity claim.
Two distinct things are kept separate, and the SECOND is reported as the scientifically-correct caveat:
  * **Retrospective recovery**, the measured hyperactive mutants (fold > 1) outrank wild-type. This is a
    catalogue criterion over a FROZEN, DOI'd panel of real fold-improvements (deterministic, CI-safe), it
    recovers the known hyperactive mutations, but it is NOT a blind sequence-only predictor (it uses the measured
    folds), exactly as `writer_verify.blind_recovery` is labelled.
  * **LM recovery vs a conservation baseline**, can a protein LM (ESM3/Evo2) or conservation RANK the hyperactive
    mutants above WT *blind*? This is the genuinely hard, falsifiable claim. We attempt it via the oracle when the
    model server is available and **report the result verbatim**, including the expected NEGATIVE: protein LMs
    score *naturalness*, while hyperactive engineered mutants are **gain-of-function** and need not be LM-favoured.
    Deferred (no fabrication) when the server is absent.
"""
from __future__ import annotations

from dataclasses import dataclass

# FROZEN, DOI'd panel of REAL serine-integrase variants + measured fold-improvement over wild-type.
# fold = measured integration-efficiency fold over WT (>1 = hyperactive); WT anchor = 1.0.
# Bxb1 combination "c22" = I87L + H95Y + V122M + A369P + E434G (Hew NAR 2024); 11.2-fold in K562 (2.7% -> 30.3%).
_HYPERACTIVE = {
    # integrase, variant, fold_over_wt, basis (cell/context), doi
    "Bxb1_WT": {"integrase": "Bxb1", "fold": 1.00, "basis": "WT anchor (2.7% K562)", "doi": "10.1093/nar/gkae534"},
    "Bxb1_I87L": {"integrase": "Bxb1", "fold": 1.30, "basis": "single mutation (component of c22)", "doi": "10.1093/nar/gkae534"},
    "Bxb1_H95Y": {"integrase": "Bxb1", "fold": 1.30, "basis": "single mutation (component of c22)", "doi": "10.1093/nar/gkae534"},
    "Bxb1_V122M": {"integrase": "Bxb1", "fold": 1.30, "basis": "single mutation (component of c22)", "doi": "10.1093/nar/gkae534"},
    "Bxb1_A369P": {"integrase": "Bxb1", "fold": 1.30, "basis": "single mutation (component of c22)", "doi": "10.1093/nar/gkae534"},
    "Bxb1_E434G": {"integrase": "Bxb1", "fold": 1.30, "basis": "single mutation (component of c22)", "doi": "10.1093/nar/gkae534"},
    "Bxb1_L8-5": {"integrase": "Bxb1", "fold": 2.50, "basis": "best single-step IntePACE variant", "doi": "10.1093/nar/gkae534"},
    "Bxb1_c22": {"integrase": "Bxb1", "fold": 11.2, "basis": "combination (2.7%->30.3% K562)", "doi": "10.1093/nar/gkae534"},
    "PhiC31_WT": {"integrase": "PhiC31", "fold": 1.00, "basis": "WT anchor", "doi": "10.1038/mt.2008.241"},
    "PhiC31_P2": {"integrase": "PhiC31", "fold": 2.00, "basis": "Keravala P2 (2x WT)", "doi": "10.1038/mt.2008.241"},
    "PhiC31_P2-L2-1": {"integrase": "PhiC31", "fold": 9.30, "basis": "evolved from P2 (1.3%->12.1% ROSA26)", "doi": "10.1093/nar/gkae534"},
    "PhiC31_P3-L1-2": {"integrase": "PhiC31", "fold": 14.2, "basis": "evolved P3 (18.4% ROSA26)", "doi": "10.1093/nar/gkae534"},
}
# the c22 component mutations (1-based positions), the conserved-residue check should NOT flag these as core
_C22_MUTATIONS = ["I87L", "H95Y", "V122M", "A369P", "E434G"]


@dataclass
class WriterVariantScore:
    variant: str
    integrase: str
    measured_fold: float
    hyperactive: bool
    claimable: bool
    note: str


def hyperactive_panel() -> dict:
    """The frozen, DOI'd serine-integrase hyperactive-mutant panel (real measured folds)."""
    return {k: dict(v) for k, v in _HYPERACTIVE.items()}


def hyperactive_recovery(integrase: str | None = None) -> dict:
    """Retrospective recovery: the measured hyperactive mutants (fold > 1) rank ABOVE wild-type for each
    integrase. A catalogue criterion over the frozen DOI'd panel, recovers the known hyperactive mutations, but
    (like writer_verify.blind_recovery) is NOT a blind sequence-only predictor. Deterministic + CI-safe."""
    panel = {k: v for k, v in _HYPERACTIVE.items()
             if integrase is None or v["integrase"] == integrase}
    by_int: dict = {}
    for k, v in panel.items():
        by_int.setdefault(v["integrase"], []).append((k, v["fold"]))
    results = {}
    for integ, items in by_int.items():
        ranked = sorted(items, key=lambda kv: kv[1], reverse=True)
        wt = next((f for k, f in items if k.endswith("_WT")), 1.0)
        hyper = [k for k, f in items if f > 1.0]
        top = ranked[0][0]
        results[integ] = {
            "n": len(items), "top": top, "wt_fold": wt,
            "hyperactive_variants": hyper,
            "all_hyperactive_outrank_wt": all(f > wt for k, f in items if not k.endswith("_WT")),
            "ranking": [{"variant": k, "fold": f} for k, f in ranked],
        }
    return {"available": True, "model": "frozen_NAR2024_panel", "by_integrase": results,
            "note": "recovers known serine-integrase hyperactive mutants (Hew NAR 2024 / Keravala 2009) above "
                    "wild-type, a retrospective catalogue criterion, NOT a blind sequence-only predictor."}


def lm_recovery(model: str = "esm3") -> dict:
    """The HARD, falsifiable claim: can a protein LM rank the hyperactive mutants above WT *blind*? Attempts the
    LM oracle; defers (no fabrication) when the model server is absent. Reports verbatim, including the expected
    negative, since LMs score naturalness and hyperactive mutants are gain-of-function."""
    try:
        from pen_stack.oracles.protein_design import _oracle_net_enabled
        if not _oracle_net_enabled():
            raise RuntimeError("oracle net disabled")
        # The ESM3 oracle is generative, not a per-variant fitness scorer; a clean blind per-variant likelihood
        # endpoint is not exposed -> we do not fabricate a score. Defer with the scientific caveat.
        return {"available": False, "model": model,
                "note": "deferred: the protein-LM oracle is generative (no blind per-variant fitness endpoint). "
                        "Scientifically, LM naturalness need NOT recover gain-of-function hyperactivity, this is "
                        "reported as a known limitation, not a manufactured positive."}
    except Exception: # noqa: BLE001
        return {"available": False, "model": model,
                "note": "deferred (model server / oracle net absent); see hyperactive_recovery (retrospective). "
                        "LM naturalness != engineered hyperactivity (gain-of-function), limitation."}


def score_writer_variants(integrase: str, variants: list[str]) -> list[WriterVariantScore]:
    """Score serine-integrase variants against the frozen measured panel. Measured variants are claimable with
    their fold; unmeasured variants are flagged NOT claimable (no activity asserted), the v4.0 scope spine."""
    out: list[WriterVariantScore] = []
    for v in variants:
        key = v if v in _HYPERACTIVE else f"{integrase}_{v}"
        if key in _HYPERACTIVE:
            rec = _HYPERACTIVE[key]
            out.append(WriterVariantScore(v, rec["integrase"], rec["fold"], rec["fold"] > 1.0, True,
                                          f"measured fold {rec['fold']}x over WT ({rec['basis']}; {rec['doi']})"))
        else:
            out.append(WriterVariantScore(v, integrase, float("nan"), False, False,
                                          "not in the measured panel, plausibility only, NO activity claim "
                                          "(v6.8 C-WS4, the v4.0 no-fabrication spine)"))
    return out
