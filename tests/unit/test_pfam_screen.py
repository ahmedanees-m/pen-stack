"""The local Pfam/HMMER sequence-domain screen wired into the Guardian.

Positive-control fixtures are built by REVERSE-TRANSLATING a public Pfam profile HMM's own consensus emission
-- a string statistically derived from the HMM's match-state probabilities, not any organism's actual toxin
sequence. This keeps the suite consistent with the registry's own "no hazard sequences committed" policy
while still exercising the real hmmscan path end-to-end (the consensus is, by construction, the argmax-
likelihood path through the profile, so it scores near the top of that profile's distribution).
"""
from __future__ import annotations

import pytest

pyhmmer = pytest.importorskip("pyhmmer")

from pen_stack.safety.gate import safety_gate  # noqa: E402
from pen_stack.safety.pfam_scan import _hmms, _strip_headers_and_whitespace, pfam_domain_screen, six_frame_translate  # noqa: E402

# reverse-translation table: one synthetic codon per residue. This is NOT how any real gene is encoded --
# it exists only to turn a profile's consensus (an amino-acid string) into a DNA string a user might paste
# into the Cargo sequence box, so the 6-frame-translate path can be exercised too.
_AA_TO_CODON = {
    'A': 'GCT', 'R': 'CGT', 'N': 'AAT', 'D': 'GAT', 'C': 'TGT', 'Q': 'CAA', 'E': 'GAA', 'G': 'GGT', 'H': 'CAT',
    'I': 'ATT', 'L': 'CTT', 'K': 'AAA', 'M': 'ATG', 'F': 'TTT', 'P': 'CCT', 'S': 'TCT', 'T': 'ACT', 'W': 'TGG',
    'Y': 'TAT', 'V': 'GTT', 'X': 'NNN',
}


def _acc(h) -> str:
    return h.accession.decode() if isinstance(h.accession, (bytes, bytearray)) else h.accession


def _synthetic_dna_for(accession_prefix: str) -> str:
    """A synthetic DNA string that will translate (frame 0) to the named Pfam profile's own consensus."""
    hmm = next(h for h in _hmms() if _acc(h).startswith(accession_prefix))
    consensus = hmm.consensus.upper()
    return "".join(_AA_TO_CODON.get(a, "NNN") for a in consensus)


# benign cargo fragments already used elsewhere in the app (Design Studio's EXAMPLE_CARGO_SEQ; a Factor IX
# fragment matching the Guardian's own benign preset) -- real, non-hazardous, and short.
_GFP_FRAGMENT = "ATGGTGAGCAAGGGCGAGGAGCTGTTCACCGGGGTGGTGCCCATCCTGGTCGAGCTGGACGGCGACGTAAACGGCCACAAGTTCAGCGTGTCCGGCGAGGGC"
_FACTOR_IX_FRAGMENT = ("GCCAATTCATTTCTAGAAGAAATGAAGAAAGGACACCTAGAAAGAGAATGTATGGAAGAAACATGCTCATATGAAGAATATTTCAGAAGAGACCCAGGTCC"
                       "CTATGTAGCTGATCAGTTGGAATG")


def test_six_frame_translate_recovers_the_forward_frame():
    dna = _synthetic_dna_for("PF00161")
    frames = six_frame_translate(dna)
    assert len(frames) == 6
    hmm = next(h for h in _hmms() if _acc(h).startswith("PF00161"))
    assert frames[0] == hmm.consensus.upper()


def test_pfam_screen_catches_a_curated_toxin_family_from_sequence_alone():
    """A raw DNA sequence for a curated toxin family (here: ricin/RIP, PF00161) must be caught even with NO
    declared cargo_function -- this is the exact gap the tester + user flagged."""
    dna = _synthetic_dna_for("PF00161")
    hits = pfam_domain_screen(dna)
    assert any(h.kind == "sequence_homology" for h in hits)
    assert any("ricin" in h.detail.lower() or "ribosome" in h.detail.lower() for h in hits)


def test_pfam_screen_catches_a_second_independent_family_not_just_ricin():
    """Not overfit to one family: botulinum/clostridial neurotoxin (PF01742) is caught too."""
    dna = _synthetic_dna_for("PF01742")
    hits = pfam_domain_screen(dna)
    assert any(h.kind == "sequence_homology" for h in hits)
    assert any("botulinum" in h.detail.lower() or "clostridial" in h.detail.lower() for h in hits)


def test_pfam_screen_stays_clear_on_real_benign_cargo_fragments():
    assert pfam_domain_screen(_GFP_FRAGMENT) == []
    assert pfam_domain_screen(_FACTOR_IX_FRAGMENT) == []


def test_pfam_screen_never_crashes_on_garbage_or_empty_input():
    assert pfam_domain_screen("") == []
    assert pfam_domain_screen(None) == []
    assert pfam_domain_screen("XYZXYZXYZ not dna or protein !!") == []
    assert pfam_domain_screen("AT") == []  # too short to translate


def test_safety_gate_refuses_a_sequence_only_submission_with_no_cargo_function():
    """End-to-end through the real Guardian entry point: cargo_seq alone (no cargo_function, no pfam_domains)
    for a high-severity curated family must REFUSE, and declared_signal must be True (a sequence WAS
    genuinely screened, this is not the empty-submission case)."""
    dna = _synthetic_dna_for("PF00161")
    v = safety_gate({"cargo_seq": dna}, actor="test")
    assert v.decision == "refuse", v.decision
    assert v.provenance["declared_signal"] is True
    assert any(h.kind == "sequence_homology" for h in v.hits)


def test_safety_gate_clears_a_benign_sequence_only_submission():
    v = safety_gate({"cargo_seq": _GFP_FRAGMENT}, actor="test")
    assert v.decision == "clear"
    assert v.provenance["declared_signal"] is True  # a real sequence was screened, just found clean
    assert "nothing was screened" not in v.reason.lower()


def test_fasta_header_is_stripped_before_the_nucleotide_vs_protein_decision():
    """Regression (tester follow-up finding): a sequence copy-pasted straight out of a real
    database (a ">accession description" header line + wrapped sequence lines) previously diluted the
    nucleotide fraction below the classification threshold, so the WHOLE header+sequence blob was scanned
    as one corrupted "protein" string and nothing matched. The header must be stripped first."""
    dna = _synthetic_dna_for("PF00161")
    fasta = f">sp|P02879|RICIN_RICCO Ricin A-chain\n{dna[:80]}\n{dna[80:160]}\n{dna[160:240]}\n"
    assert _strip_headers_and_whitespace(fasta) == dna[:240]
    hits = pfam_domain_screen(fasta)
    assert any(h.kind == "sequence_homology" for h in hits), "FASTA-formatted paste must still be screened"


def test_fasta_header_full_length_via_safety_gate():
    dna = _synthetic_dna_for("PF00161")
    lines = [dna[i:i + 60] for i in range(0, len(dna), 60)]
    fasta = ">query_cassette\n" + "\n".join(lines) + "\n"
    v = safety_gate({"cargo_seq": fasta}, actor="test")
    assert v.decision == "refuse", v.decision
    assert any(h.kind == "sequence_homology" for h in v.hits)


def test_fasta_formatted_benign_sequence_stays_clear():
    fasta = f">gfp fragment, example CDS\n{_GFP_FRAGMENT}\n"
    assert pfam_domain_screen(fasta) == []
