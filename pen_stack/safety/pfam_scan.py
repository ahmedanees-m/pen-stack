"""Local Pfam/HMMER domain screen over a raw cargo sequence.

Wires the sequence-homology slot the Guardian has always had (`HazardRegistry`'s `external_hook`), using
PUBLIC Pfam profile HMMs for the SAME curated toxin families already listed in
`configs/safety/hazard_registry.yaml`. No hazard sequences are bundled -- only statistical family models (the
same class of public artifact the registry's own accessions already reference; a profile HMM is built from
many aligned public sequences, it is not any one organism's sequence). A DNA/RNA cargo_seq is translated in
all 6 reading frames (protein cargo is scanned directly) and scored against the bundled HMM file using each
profile's own Pfam-recommended gathering (GA) cutoff -- the same threshold real Pfam annotation pipelines use
to decide genuine family membership.

Scope: this closes the "raw sequence, no declared function" gap for the SAME curated family list the
function screen already covers (see hazard_registry.yaml's `toxin_functions`). It is not a substitute for a
full external homology screener (e.g. IBBIS Common Mechanism / SecureDNA) over a much larger reference set --
an integrator wanting that coverage can still override via `HazardRegistry.load(external_hook=...)`.
"""
from __future__ import annotations

from functools import lru_cache

from pen_stack._resources import resource
from pen_stack.safety.screen import ScreenHit

_HMM_REL = "configs/safety/pfam_hmms/toxin_domains.hmm"

_CODON = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L', 'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M', 'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S', 'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T', 'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*', 'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K', 'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W', 'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R', 'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
}
_COMPLEMENT = str.maketrans("ACGTUacgtu", "TGCAAtgcaa")
_NUCLEOTIDE = set("ACGTUN")


def _strip_headers_and_whitespace(text: str) -> str:
    """Drop FASTA/GenBank-style header and comment lines (">...", ";...") and all whitespace, so a sequence
    copy-pasted straight out of UniProt/NCBI/Ensembl -- header line and all -- is screened on the actual
    sequence, not a header+sequence blob whose nucleotide fraction the header dilutes below any threshold."""
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith((">", ";"))]
    return "".join("".join(lines).split())


def _looks_like_nucleotide(seq: str) -> bool:
    """A sequence is treated as DNA/RNA if it is overwhelmingly A/C/G/T/U/N; otherwise it is scanned as
    protein directly (the Cargo sequence box accepts either, per its own hint text: "A/C/G/T or A/C/G/U").
    Called AFTER header/whitespace stripping, so a FASTA header's non-sequence characters never skew this."""
    s = seq.upper()
    if not s:
        return True
    nt = sum(1 for c in s if c in _NUCLEOTIDE)
    return nt / len(s) >= 0.9


def _translate_frame(dna: str) -> str:
    return "".join(_CODON.get(dna[i:i + 3], "X") for i in range(0, len(dna) - 2, 3))


def six_frame_translate(seq: str) -> list[str]:
    """DNA/RNA -> the 6 reading-frame protein translations (3 forward, 3 reverse-complement)."""
    s = "".join(c for c in seq.upper().replace("U", "T") if c in "ACGT")
    if len(s) < 3:
        return []
    rc = s.translate(_COMPLEMENT)[::-1]
    return [_translate_frame(strand[o:]) for strand in (s, rc) for o in range(3)]


@lru_cache(maxsize=1)
def _hmms():
    import pyhmmer
    with pyhmmer.plan7.HMMFile(str(resource(_HMM_REL))) as hf:
        return list(hf)


@lru_cache(maxsize=1)
def _default_toxin_functions() -> list[dict]:
    """`toxin_functions` straight from the registry YAML, so the standard 1-arg hook signature
    (`Callable[[str], list[ScreenHit]]`) still resolves accession -> name/severity/control_ref without the
    caller having to thread the registry through."""
    import yaml
    raw = yaml.safe_load(resource("configs/safety/hazard_registry.yaml").read_text(encoding="utf-8"))
    return raw.get("toxin_functions", [])


def _acc(x) -> str:
    v = x.decode() if isinstance(x, (bytes, bytearray)) else (x or "")
    return v.split(".")[0]  # strip the Pfam version suffix (PF00161.25 -> PF00161)


# bound worst-case scan latency on a pathological paste; real cassettes are well under this (the largest
# vehicle capacity in configs/delivery_vehicles.yaml is ~8kb).
_MAX_SCAN_LEN = 50_000


def pfam_domain_screen(seq: str | None, toxin_functions: list[dict] | None = None) -> list[ScreenHit]:
    """The Guardian's `external_hook`: scores a raw cargo sequence against the bundled Pfam profile HMMs for
    the curated toxin families (public accessions matching `hazard_registry.yaml`'s own list), using each
    profile's Pfam gathering (GA) cutoff. Returns [] on any failure (pyhmmer absent, bad input) -- the safety
    gate must never crash; a missing sequence screen is a documented gap, not a broken app."""
    if not seq or not str(seq).strip():
        return []
    try:
        import pyhmmer
        from pyhmmer.easel import Alphabet, DigitalSequence
    except Exception:  # noqa: BLE001 - pyhmmer not installed in this environment
        return []

    text = _strip_headers_and_whitespace(str(seq))[:_MAX_SCAN_LEN]
    if not text:
        return []
    if _looks_like_nucleotide(text):
        proteins = six_frame_translate(text)
    else:
        # protein branch: keep only standard + ambiguity amino-acid letters, so a stray annotation
        # character never breaks the digital-alphabet encoding step below.
        proteins = ["".join(c for c in text.upper() if c in "ACDEFGHIKLMNPQRSTVWYXBZJUO")]
    proteins = [p for p in proteins if len(p) >= 15]
    if not proteins:
        return []

    alphabet = Alphabet.amino()
    try:
        queries = [DigitalSequence(alphabet, name=f"frame_{i}".encode(), sequence=alphabet.encode(p))
                   for i, p in enumerate(proteins)]
        hmms = _hmms()
        results = list(pyhmmer.hmmer.hmmscan(queries, hmms, bit_cutoffs="gathering"))
    except Exception:  # noqa: BLE001 - a malformed sequence must never break the gate
        return []

    # entry lookup by Pfam accession (no version suffix), reusing the registry's OWN toxin_functions list
    # for name/severity/control_ref so this hook never duplicates or drifts from the curated registry.
    entries = toxin_functions if toxin_functions is not None else _default_toxin_functions()
    by_pfam: dict[str, dict] = {}
    for entry in entries:
        for p in entry.get("pfam", []):
            by_pfam.setdefault(p, entry)

    seen: set[str] = set()
    hits: list[ScreenHit] = []
    for tophits in results:
        for hit in tophits:
            acc = _acc(hit.accession)
            entry = by_pfam.get(acc)
            if not entry or entry["id"] in seen:
                continue
            seen.add(entry["id"])
            hits.append(ScreenHit(
                kind="sequence_homology", detail=entry["name"], severity=entry.get("severity", "medium"),
                provenance={"registry_version": None, "signature_id": entry.get("id"),
                            "control_ref": entry.get("control_ref"),
                            "source": "pfam_hmmscan (local, gathering-threshold)"},
                evidence={"pfam_accession": acc, "bit_score": round(float(hit.score), 1)}))
    return hits
