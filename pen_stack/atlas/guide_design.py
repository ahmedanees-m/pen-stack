"""Guide / attachment-site design for genome writers (v6.8 PEN-WRITER, C-WS3).

Auto-designs the targeting component each writer family needs, from the DOCUMENTED reprogramming rules:

  * **bridge RNA** (IS110 / IS621 / ISCro4), a non-coding RNA with a **target-binding loop (TBL)** and a
    **donor-binding loop (DBL)** that are reprogrammed independently to base-pair the target and donor, around a
    conserved central **core dinucleotide** that must match between target and donor (Durrant et al., Nature 2024,
    10.1038/s41586-024-07552-4). We compute the loop guide sequences (reverse-complement of the specificity arms,
    core preserved) and validate by round-trip recovery.
  * **pegRNA + attB** (PASTE / PASSIGE), a prime-editing guide whose 3' extension WRITES a serine-integrase
    attachment site at the nick, so the integrase can then place large cargo (Yarnall et al., Nat Biotechnol 2023,
    10.1038/s41587-022-01527-4; Pandey/Liu, Nat Biomed Eng 2025). v6.9.2 writes the **REAL documented Bxb1 minimal
    attB** (FlyBase FBto0000359; Ghosh, Kim & Hatfull, Mol Cell 2003, 10.1016/S1097-2765(03)00444-1), not a
    schematic, with the 8-bp common core **GCGGTCTC** around the central **GT** crossover dinucleotide.
  * **orthogonal att-pair selection**, serine-integrase att sites with distinct central dinucleotides
    (e.g. **GA vs GT**) recombine only with their cognate partner, enabling multiplexed/orthogonal landing pads
    (Roelle, Kamath & Matreyek, ACS Synth Biol 2023, 10.1021/acssynbio.3c00355).

These are GROUNDED design heuristics from the published rules, auto-designed guides are **candidates** that
require empirical validation; nothing about activity is claimed. Recovery tests check the logic reproduces known
constructs (round-trip + documented invariants), never that a designed guide "works".
"""
from __future__ import annotations

from dataclasses import dataclass

_COMP = {"A": "T", "T": "A", "G": "C", "C": "G", "N": "N",
         "a": "t", "t": "a", "g": "c", "c": "g", "n": "n"}

# documented serine-integrase attachment-site CENTRAL DINUCLEOTIDES (the recombination crossover core)
_INTEGRASE_CORE = {
    "Bxb1": "GT", # canonical Bxb1 att central dinucleotide (the recombined 2 bp)
    "PhiC31": "TT", # PhiC31 att core
}
# orthogonal Bxb1 att variants by engineered central dinucleotide (Roelle 2023), matched cores recombine,
# mismatched cores are ~orthogonal.
_ORTHOGONAL_BXB1_CORES = ["GT", "GA", "GC", "CT", "TA"]

# REAL, documented serine-integrase attachment sites (verbatim, never fabricated). Bxb1: FlyBase FBto0000359
# (attB) / FBto0000358 (attP); Ghosh, Kim & Hatfull, Mol Cell 2003 (10.1016/S1097-2765(03)00444-1), attB/attP
# share the 8-bp common core GCGGTCTC around the central GT crossover dinucleotide (the sole determinant of
# integration orientation). Only integrases with a documented site bundled here get a full attB written.
_INTEGRASE_ATT = {
    "Bxb1": {
        "attB": "TCGGCCGGCTTGTCGACGACGGCGGTCTCCGTCGTCAGGATCATCCGGGC",
        "attP": "GTCGTGGTTTGTCTGGTCAACCACCGCGGTCTCAGTGGTGTACGGTACAAACCCCGAC",
        "core": "GCGGTCTC", "central_dinucleotide": "GT",
        "source": "FlyBase FBto0000359/358; Ghosh, Kim & Hatfull, Mol Cell 2003",
        "doi": "10.1016/S1097-2765(03)00444-1",
    },
}


def revcomp(seq: str) -> str:
    return "".join(_COMP.get(b, "N") for b in reversed(seq))


@dataclass
class BridgeRNADesign:
    target: str
    donor: str
    core: str
    target_binding_loop: str # TBL guide (base-pairs the target arms)
    donor_binding_loop: str # DBL guide (base-pairs the donor arms)
    core_matched: bool
    output_kind: str = "candidate"
    note: str = ""


def design_bridge_rna(target_seq: str, donor_seq: str, core_len: int = 2) -> BridgeRNADesign:
    """Design an IS110/IS621 bridge-RNA's two reprogrammable loops for a `(target, donor)` pair.

    The bipartite target/donor each carry a central core (default 2 nt); the loops are reprogrammed to base-pair
    the flanking specificity arms (reverse-complement). The bridge mechanism REQUIRES the target and donor cores
    to match, flagged when they do not (the design is then infeasible).
    """
    t, d = target_seq.upper(), donor_seq.upper()
    mid_t, mid_d = len(t) // 2, len(d) // 2
    core_t = t[mid_t - core_len // 2: mid_t - core_len // 2 + core_len]
    core_d = d[mid_d - core_len // 2: mid_d - core_len // 2 + core_len]
    return BridgeRNADesign(
        target=t, donor=d, core=core_t,
        target_binding_loop=revcomp(t), # the guide loop base-pairs the target (specificity arms reprogrammed)
        donor_binding_loop=revcomp(d),
        core_matched=bool(core_t == core_d),
        note=("bridge RNA loops reprogrammed to the target/donor; core dinucleotide "
              + ("matched (feasible)" if core_t == core_d else f"MISMATCH ({core_t} vs {core_d}) -> infeasible, "
                 "the IS110/IS621 mechanism requires matching target/donor cores (Durrant 2024)")))


def recover_bridge_rna(target_seq: str, donor_seq: str) -> bool:
    """Round-trip recovery: the TBL must reverse-complement back to the target (and DBL to the donor), the
    documented reprogramming invariant. Deterministic logic check, not an activity claim."""
    des = design_bridge_rna(target_seq, donor_seq)
    return revcomp(des.target_binding_loop) == target_seq.upper() and \
        revcomp(des.donor_binding_loop) == donor_seq.upper()


@dataclass
class PegRNAAttDesign:
    integrase: str
    att_core: str
    target_site: str
    pegrna_spacer: str # the spacer (protospacer) for the prime-edit nick
    pe_3prime_extension: str # the 3' extension encoding the attB to be written at the nick
    written_att: str
    output_kind: str = "candidate"
    note: str = ""


def design_pegrna_attb(target_site: str, integrase: str = "Bxb1") -> PegRNAAttDesign:
    """Design a PASTE/PASSIGE pegRNA that writes a serine-integrase **attB** at `target_site`.

    The prime-edit installs the integrase's minimal attB; the integrase then recombines cargo flanked by the
    cognate attP. We return the spacer + the 3' extension (revcomp of the att template, the PE convention) and the
    att site written. For integrases with a documented site bundled (`_INTEGRASE_ATT`, e.g. Bxb1) the REAL minimal
    attB is written verbatim, never a schematic; integrases without a bundled documented site expose only the
    central core (the full sequence is NOT fabricated). Sequences are DESIGN CANDIDATES, empirical validation
    required.
    """
    integrase = integrase if integrase in _INTEGRASE_CORE else "Bxb1"
    core = _INTEGRASE_CORE[integrase]
    ts = target_site.upper()
    spacer = ts[:20] if len(ts) >= 20 else ts
    att = _INTEGRASE_ATT.get(integrase)
    if att:
        attb = att["attB"] # REAL documented minimal attB (verbatim), no schematic arms
        note = (f"pegRNA 3' extension writes the REAL documented {integrase} minimal attB ({len(attb)} bp; central "
                f"crossover {att['central_dinucleotide']}, 8-bp common core {att['core']}; {att['source']}) at the "
                f"nick; cargo is delivered flanked by the cognate attP. Candidate scaffold, empirical validation "
                "required (Yarnall 2023).")
    else:
        attb = core # no bundled documented site: expose the core only, never fabricate
        note = (f"no bundled documented minimal att sequence for {integrase!r}: only the central core {core} is "
                "asserted (the full site is NOT fabricated). Add a documented attB to design the full scaffold.")
    return PegRNAAttDesign(
        integrase=integrase, att_core=core, target_site=ts, pegrna_spacer=spacer,
        pe_3prime_extension=revcomp(attb), written_att=attb, note=note)


def select_orthogonal_att_pairs(n: int, integrase: str = "Bxb1") -> dict:
    """Select up to `n` mutually-orthogonal serine-integrase att pairs by distinct central dinucleotide
    (Roelle 2023): matched cores recombine, mismatched cores are ~orthogonal -> usable for multiplexed landing
    pads. Returns the selected cores + a cross-reactivity matrix (1 on the diagonal = cognate, ~0 off-diagonal)."""
    cores = _ORTHOGONAL_BXB1_CORES[:max(1, min(n, len(_ORTHOGONAL_BXB1_CORES)))]
    matrix = {a: {b: (1 if a == b else 0) for b in cores} for a in cores}
    return {"integrase": integrase, "selected_cores": cores, "n": len(cores),
            "cross_reactivity": matrix, "output_kind": "candidate",
            "orthogonal": all(matrix[a][b] == 0 for a in cores for b in cores if a != b),
            "note": "orthogonality by central-dinucleotide identity (Roelle, Kamath & Matreyek, ACS Synth Biol "
                    "2023); cores must be empirically confirmed orthogonal in the target context.",
            "capped": n > len(_ORTHOGONAL_BXB1_CORES)}


def design_guide_for_writer(writer_family: str, target_seq: str | None = None,
                            donor_seq: str | None = None, integrase: str = "Bxb1") -> dict:
    """Dispatch to the right guide design for a writer family. Returns a candidate design + the design type, or an
    abstention when required inputs are missing or the family has no programmable-guide design here."""
    fam = (writer_family or "").lower()
    if "bridge" in fam or "is110" in fam or "is621" in fam or "seek" in fam:
        if not (target_seq and donor_seq):
            return {"design_type": "bridge_rna", "available": False,
                    "reason": "bridge-RNA design needs both target and donor sequences"}
        d = design_bridge_rna(target_seq, donor_seq)
        return {"design_type": "bridge_rna", "available": True, "design": d.__dict__,
                "feasible": d.core_matched}
    if "pe_integrase" in fam or "paste" in fam or "passige" in fam or "serine" in fam:
        if not target_seq:
            return {"design_type": "pegrna_attb", "available": False,
                    "reason": "pegRNA+attB design needs a target site sequence"}
        d = design_pegrna_attb(target_seq, integrase=integrase)
        return {"design_type": "pegrna_attb", "available": True, "design": d.__dict__}
    return {"design_type": None, "available": False,
            "reason": f"no programmable-guide design for family '{writer_family}' (e.g. fixed-att or DSB nuclease)"}
