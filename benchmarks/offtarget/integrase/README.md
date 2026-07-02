# PhiC31 pseudo-attP recall benchmark (O-G2) — SEALED

**Question:** does attP-sequence-similarity recover the documented human pseudo-attP above random genomic background?

**Data (all independently verified against NCBI/RCSB):**
- **Positives** — `phic31_pseudo.fasta`: human pseudo-attP ψA/ψC/ψD, GenBank **AF333429/AF333430/AF333431**
  (Thyagarajan 2001, *Mol Cell Biol* 21(12), PMID 11359900, DOI `10.1128/MCB.21.12.3926-3934.2001`; chr8/16/15).
- **Query** — the phage φC31 attP central 30 bp from **PDB 9U2T (attP60)**, the "PhiC31 integrase-attB-attP synaptic
  complex" structure; the canonical Groth-2000 34 bp attB is present in **PDB 9U2S (attB53)** (Groth 2000, PNAS,
  DOI `10.1073/pnas.090527097`).
- **Background** — 1000 GC/N-filtered, length-matched random GRCh38 windows per positive.

**Result (`phic31_recall_metrics.json`) — NEGATIVE, reported verbatim:** every documented pseudosite scores 14 mm /
30 bp (53.3% identity), which is exactly the **background median** (14 mm); 60.6% / 77.0% / 82.4% of random windows
are as-or-more attP-similar. Sequence identity to attP does **not** recover the documented pseudo-attP above
background — consistent with the field (φC31 pseudosite recognition depends on palindromic architecture, Chalberg
2006 DOI `10.1016/j.jmb.2005.11.098`, / a learned model, IntQuery). The integrase genome-wide pseudo-attP
**similarity ranking is therefore unvalidated**; the verified att and documented pseudosites remain grounded facts.

**Honest limits:** N=3 (the open GenBank subset; the full Chalberg 19-site set is paywalled); tests
sequence-identity only (no palindrome/learned model); deterministic (seed 20260701), pysam over GRCh38.

Run: `docker run --rm --entrypoint bash -v <genomes>:/genome -v $PWD:/work -w /work penstack:phase1.5 -lc 'python harness.py'`
