"""Computed innate-immune-sensing scorer for nucleic-acid cargo (v5.4, WS-INNATE).

Innate sensing of a delivered nucleic acid is a property of the CARGO SEQUENCE (and its form), computed here
directly from sequence - the third computed delivery-immunology signal (after v5.2 genotoxicity and v5.3 capsid
epitope load). It covers every cargo form the palette carries:

  * DNA (AAV / HDAd / HSV / electroporated plasmid) -> TLR9 / cGAS sensing of unmethylated CpG. The standard
    sequence statistic is the CpG observed/expected ratio (Gardiner-Garden & Frommer): vertebrate genomes are
    CpG-DEPLETED (O/E ~ 0.2) and tolerated, while non-depleted plasmid/viral DNA (O/E -> 1) is TLR9-stimulatory;
    CpG-DEPLETED vectors evade detection. innate_score = max(0, 1 - CpG_O/E).
  * mRNA (LNP-mRNA / electroporated mRNA) -> TLR7/8 (U-rich ssRNA) + RIG-I / MDA5 / PKR (dsRNA). Computed from
    uridine fraction + ViennaRNA base-pairing. This signal is PARTIAL and flagged `extrapolating`: the dominant
    innate-evasion lever for mRNA is NUCLEOSIDE MODIFICATION (m1-pseudouridine), which is NOT derivable from the
    nucleotide sequence (a manufacturing choice) - a stated known-limitation.
  * RNP / protein -> minimal, transient nucleic-acid exposure (no DNA; short-lived gRNA): score ~ high.

Answers through the v4.0 OracleResult contract (output_kind="baseline"). SCOPE: this is a sequence-intrinsic
motif-LOAD signal; the realized in-vivo innate RESPONSE magnitude in a patient is NOT modelled and stays a
known-unknown; DNA methylation state and RNA nucleoside modification are out of sequence scope.
"""
from __future__ import annotations

from pen_stack.oracles.schema import OracleResult, Provenance

_SCOPE_CARD = "innate_sensing"
_DNA = set("ACGT")
_RNA = set("ACGU")
# CpG-TLR9 (Krieg 1995 / Bauer 2001), CpG-depleted AAV evasion (Faust 2013), RNA nucleoside modification
# (Kariko 2005), 5'ppp dsRNA RIG-I (Hornung 2006).
PROVENANCE_DOIS = ["10.1038/374546a0", "10.1073/pnas.161293498", "10.1172/JCI68205",
                   "10.1016/j.immuni.2005.06.008", "10.1126/science.1132505"]


def _clean(seq: str) -> str:
    return "".join(c for c in (seq or "").upper() if c.isalpha())


def cpg_observed_expected(dna: str) -> dict:
    """CpG observed/expected ratio (Gardiner-Garden & Frommer): (n_CpG / (n_C * n_G)) * length. Vertebrate
    genome ~0.2 (depleted); non-depleted plasmid/viral DNA approaches 1; engineered CpG-free -> 0."""
    s = _clean(dna).replace("U", "T")
    L = len(s)
    nC, nG = s.count("C"), s.count("G")
    n_cpg = s.count("CG")
    oe = (n_cpg / (nC * nG) * L) if (nC and nG) else 0.0
    gc = (nC + nG) / L if L else 0.0
    return {"length": L, "cpg_count": n_cpg, "cpg_oe": round(oe, 4), "gc": round(gc, 4)}


def _dsrna_paired_fraction(rna: str) -> float | None:
    """Fraction of bases paired in the ViennaRNA MFE structure (dsRNA -> RIG-I/MDA5/PKR). None if ViennaRNA
    absent (graceful degradation, as in bridge/fold_qc.py)."""
    try:
        import RNA
    except Exception: # noqa: BLE001
        return None
    s = _clean(rna).replace("T", "U")
    if not s:
        return None
    struct, _ = RNA.fold_compound(s).mfe()
    paired = sum(1 for c in struct if c in "()")
    return round(paired / len(struct), 4) if struct else None


def _prov() -> Provenance:
    return Provenance(model="cargo_innate_sensing", version="1.0", source="adapter",
                      extra={"provenance_dois": PROVENANCE_DOIS})


def innate_sensing(seq: str, cargo_form: str) -> OracleResult:
    """Computed innate-sensing score for a cargo sequence + form, as an OracleResult (v4.0 contract).

    `cargo_form` in {DNA, mRNA, RNP}. Returns innate_score in [0,1] (1 = least innate-stimulatory). Abstains
    (available=False) on an empty sequence or an unrecognised/uncomputable form. Never fabricates."""
    s = _clean(seq)
    form = (cargo_form or "").strip()
    if not s:
        return OracleResult(oracle="genome", value=None, provenance=_prov(), scope_card=_SCOPE_CARD,
                            in_scope=False, available=False, output_kind="baseline",
                            note="no cargo sequence supplied")

    if form == "DNA":
        c = cpg_observed_expected(s)
        score = max(0.0, min(1.0, 1.0 - c["cpg_oe"]))
        return OracleResult(
            oracle="genome",
            value={"innate_score": round(score, 3), "pathway": "TLR9/cGAS (unmethylated CpG)",
                   "cpg_oe": c["cpg_oe"], "cpg_count": c["cpg_count"], "gc": c["gc"], "length": c["length"]},
            provenance=_prov(), native_uncertainty=None, scope_card=_SCOPE_CARD, in_scope=True,
            extrapolating=False, output_kind="baseline", available=True,
            note=(f"CpG O/E={c['cpg_oe']} ({c['cpg_count']} CpG, {c['length']} bp); innate_score=max(0,1-O/E). "
                  "Vertebrate genome O/E~0.2 (tolerated), non-depleted DNA ->1 (TLR9-stimulatory). DNA "
                  "methylation state and the realized in-vivo innate RESPONSE are known-unknowns (not modelled)."))

    if form == "mRNA":
        u_frac = s.replace("T", "U").count("U") / len(s)
        paired = _dsrna_paired_fraction(s)
        # partial sequence-only signal: U-richness (TLR7/8) + dsRNA pairing (RIG-I/PKR). The dominant evasion
        # lever (nucleoside modification, m1-pseudouridine) is NOT sequence-derivable -> flagged extrapolating.
        if paired is None:
            score = max(0.0, min(1.0, 1.0 - u_frac))
            note_ds = "ViennaRNA absent: dsRNA term omitted; score from U-fraction only."
        else:
            score = max(0.0, min(1.0, 1.0 - 0.5 * u_frac - 0.5 * paired))
            note_ds = f"dsRNA paired_fraction={paired} (RIG-I/MDA5/PKR)."
        return OracleResult(
            oracle="rna",
            value={"innate_score": round(score, 3), "pathway": "TLR7/8 (U-rich ssRNA) + RIG-I/MDA5/PKR (dsRNA)",
                   "u_fraction": round(u_frac, 4), "dsrna_paired_fraction": paired, "length": len(s)},
            provenance=_prov(), native_uncertainty=None, scope_card=_SCOPE_CARD, in_scope=True,
            extrapolating=True, output_kind="baseline", available=True,
            note=("PARTIAL sequence-only signal. " + note_ds + " The dominant mRNA innate-evasion lever - "
                  "NUCLEOSIDE MODIFICATION (m1-pseudouridine) - is NOT sequence-derivable and is out of scope; "
                  "the realized in-vivo innate response is a known-unknown."))

    if form == "RNP":
        return OracleResult(
            oracle="rna",
            value={"innate_score": 0.9, "pathway": "minimal (transient gRNA; no DNA)", "length": len(s)},
            provenance=_prov(), native_uncertainty=None, scope_card=_SCOPE_CARD, in_scope=True,
            extrapolating=True, output_kind="baseline", available=True,
            note=("RNP cargo: transient, no DNA -> minimal nucleic-acid innate sensing (synthetic gRNA may "
                  "trigger RIG-I via 5'-triphosphate; modification mitigates - not sequence-derivable). "
                  "Realized response is a known-unknown."))

    return OracleResult(oracle="genome", value=None, provenance=_prov(), scope_card=_SCOPE_CARD,
                        in_scope=False, available=False, output_kind="baseline",
                        note=f"unrecognised cargo_form {cargo_form!r} (expected DNA / mRNA / RNP)")


def computed_innate_score(seq: str, cargo_form: str) -> tuple[float | None, OracleResult]:
    """Convenience: (innate_score or None, full OracleResult). None when the scorer abstains. Never fabricates."""
    r = innate_sensing(seq, cargo_form)
    val = (r.value or {}).get("innate_score") if (r.available and r.value) else None
    return val, r
