"""Genome-wide off-target ENUMERATION — the CRISPOR/CHOPCHOP-like search step (PEN-OFFTGT v2, O-WS1).

Stage E used to only SCORE candidate sites a caller supplied. This module adds the missing half: given a guide +
enzyme, ENUMERATE every genomic site within the mismatch tolerance across GRCh38 — returning coordinates, strand,
matched sequence, and mismatch count — so the downstream scorer ranks a genome-wide candidate set (what a real
off-target tool does), not a hand-typed one.

**Where it runs.** A full GRCh38 scan is heavy, so enumeration executes ONLY where Cas-OFFinder + the genome are
present — the VM, via the `casoffinder:tools` Docker image (Bae, Park & Kim, Bioinformatics 2014,
10.1093/bioinformatics/btu048). A build-time script enumerates the canonical guides on the VM and commits the
resulting coordinates to `data/offtarget/enumerated_cache.parquet`. Everywhere else (the live app, CI, the laptop)
this module REPLAYS that cache for a cached guide, or ABSTAINS with an honest pointer for a novel one — the same
replay-or-abstain pattern the heavy structure oracles use. The enumerated coordinates are facts derivable from the
public GRCh38 assembly (no license restriction, unlike the CRISOT weights), so committing the cache is clean.
"""
from __future__ import annotations

import shutil
import subprocess
from functools import lru_cache

# Per-enzyme PAM + protospacer length. IUPAC PAMs are passed to Cas-OFFinder verbatim (it resolves R/V/etc.).
# pam_side: 3 = PAM 3' of the protospacer (Cas9); 5 = PAM 5' of the protospacer (Cas12a).
_ENZYME = {
    "SpCas9":   {"pam": "NGG",    "pam_side": 3, "guide_len": 20},
    "SaCas9":   {"pam": "NNGRRT", "pam_side": 3, "guide_len": 21},
    "AsCas12a": {"pam": "TTTV",   "pam_side": 5, "guide_len": 23},
    "LbCas12a": {"pam": "TTTV",   "pam_side": 5, "guide_len": 23},
}
_ALIAS = {"cas9": "SpCas9", "spcas9": "SpCas9", "nuclease": "SpCas9", "nickase": "SpCas9",
          "sacas9": "SaCas9", "ascas12a": "AsCas12a", "lbcas12a": "LbCas12a", "cas12a": "AsCas12a"}
DEFAULT_MAX_MISMATCH = 5
_CACHE_PATH = "data/offtarget/enumerated_cache.parquet"


def resolve_enzyme(name: str) -> str | None:
    """Map a free-text enzyme/family to a supported nuclease key, or None if unsupported."""
    n = (name or "").strip()
    if n in _ENZYME:
        return n
    return _ALIAS.get(n.lower())


def _strip_pam(guide: str, spec: dict) -> str:
    """Return just the protospacer (drop a PAM the caller may have appended/prepended, and any spaces)."""
    g = "".join(c for c in (guide or "").upper() if c in "ACGT")
    return g[:spec["guide_len"]] if spec["pam_side"] == 3 else g[-spec["guide_len"]:]


def build_casoffinder_input(guide: str, enzyme: str, genome_path: str, max_mismatch: int) -> str:
    """The Cas-OFFinder v2.4 input text: genome path, the pattern (protospacer Ns + PAM in IUPAC), and the query
    (the guide with N in the PAM positions) with the mismatch tolerance. Handles 3' (Cas9) and 5' (Cas12a) PAMs."""
    spec = _ENZYME[enzyme]
    g = _strip_pam(guide, spec)
    pam, gl = spec["pam"], spec["guide_len"]
    if spec["pam_side"] == 3:
        pattern = "N" * gl + pam
        query = g + "N" * len(pam)
    else:
        pattern = pam + "N" * gl
        query = "N" * len(pam) + g
    return f"{genome_path}\n{pattern}\n{query} {int(max_mismatch)}\n"


def parse_casoffinder_output(text: str, enzyme: str) -> list[dict]:
    """Parse Cas-OFFinder v2.4 (no-bulge) output into off-target records. The default output is 6 tab-separated
    columns: query-pattern, chromosome-header, 0-based position, matched-DNA (lowercase = mismatch), strand,
    mismatch-count. GRCh38's FASTA headers are verbose (``chr3  AC:...  AS:GRCh38``), so the contig name is the
    first whitespace token of the chromosome field. Skips bulge rows (v2.0 enumerates substitutions only)."""
    spec = _ENZYME[enzyme]
    gl, plen = spec["guide_len"], spec["guide_len"] + len(spec["pam"])
    out: list[dict] = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#") or line.lower().startswith(("crrna", "id", "bulge")):
            continue
        f = line.split("\t")
        if len(f) < 6:
            continue
        try:
            pos, n_mm = int(f[2]), int(f[5])
        except ValueError:
            continue
        strand, dna = f[4], f[3].upper()
        if strand not in ("+", "-") or "-" in dna:  # '-' => a bulge/gap row, skip
            continue
        # the query column (f[0]) encodes the guide; a batch run mixes guides, so tag each record with its guide
        q = "".join(c for c in f[0].upper() if c in "ACGT")
        guide = q[:gl] if spec["pam_side"] == 3 else q[-gl:]
        out.append({"guide": guide, "chrom": f[1].split()[0], "position": pos, "strand": strand,
                    "sequence": dna[:plen], "n_mismatch": n_mm})
    return out


def _casoffinder_bin() -> str | None:
    return shutil.which("cas-offinder")


def scan_local(guide: str, enzyme: str, genome_path: str, max_mismatch: int = DEFAULT_MAX_MISMATCH,
               device: str = "C", workdir: str | None = None) -> list[dict]:
    """Run Cas-OFFinder locally (VM / casoffinder:tools) and return the enumerated off-target records. Raises if
    the binary or genome is absent — callers gate on `casoffinder_available()`. Used by the VM cache-build script."""
    import os
    import tempfile
    binary = _casoffinder_bin()
    if not binary:
        raise RuntimeError("cas-offinder not on PATH (run inside casoffinder:tools on the VM)")
    wd = workdir or tempfile.mkdtemp(prefix="offtgt_")
    inp, outp = os.path.join(wd, "in.txt"), os.path.join(wd, "out.txt")
    with open(inp, "w", encoding="utf-8") as fh:
        fh.write(build_casoffinder_input(guide, enzyme, genome_path, max_mismatch))
    subprocess.run([binary, inp, device, outp], check=True, capture_output=True, text=True)
    with open(outp, encoding="utf-8") as fh:
        return parse_casoffinder_output(fh.read(), enzyme)


def casoffinder_available() -> bool:
    return _casoffinder_bin() is not None


@lru_cache(maxsize=1)
def _cache_df():
    """The committed genome-wide enumeration cache (enzyme, guide, chrom, position, strand, sequence, n_mismatch),
    or None when absent (bare wheel). Enumerated on the VM over GRCh38; coordinates are public-genome facts."""
    try:
        import pandas as pd

        from pen_stack._resources import resource
        return pd.read_parquet(resource(_CACHE_PATH))
    except Exception:  # noqa: BLE001
        return None


@lru_cache(maxsize=1)
def enumerated_guides() -> tuple:
    """The (enzyme, guide) pairs whose genome-wide enumeration is cached (so the live app behaves like a finder for
    them). Empty when no cache is present."""
    df = _cache_df()
    if df is None or df.empty:
        return ()
    return tuple(sorted({(str(r.enzyme), str(r.guide)) for r in df.itertuples()}))


def _replay_cache(guide: str, enzyme: str, max_mismatch: int) -> list[dict] | None:
    df = _cache_df()
    if df is None or df.empty:
        return None
    spec = _ENZYME[enzyme]
    g = _strip_pam(guide, spec)
    sub = df[(df["enzyme"] == enzyme) & (df["guide"] == g) & (df["n_mismatch"] <= int(max_mismatch))]
    if sub.empty:
        return None
    cols = ["chrom", "position", "strand", "sequence", "n_mismatch"]
    return sub.sort_values("n_mismatch")[cols].to_dict("records")


def enumerate_offtargets(guide: str, enzyme: str = "SpCas9", max_mismatch: int = DEFAULT_MAX_MISMATCH,
                         allow_scan: bool = False, genome_path: str | None = None) -> dict:
    """Genome-wide off-target enumeration for a guide. Returns a dict with the enumerated `sites` (coordinates +
    strand + sequence + mismatch count) and the `source` (cache | scan), or an honest abstention.

    The live app calls with ``allow_scan=False`` (never runs a genome scan in-request): it replays the committed
    cache for a cached guide, or abstains for a novel one. The VM cache-build script calls with ``allow_scan=True``
    inside ``casoffinder:tools`` to run the real scan. Never fabricates sites."""
    enz = resolve_enzyme(enzyme)
    if enz is None:
        return {"available": False, "abstain": True, "enzyme": enzyme,
                "note": f"enumeration supports {sorted(_ENZYME)}; {enzyme!r} is not a supported nuclease"}
    spec = _ENZYME[enz]
    g = _strip_pam(guide, spec)
    if len(g) < spec["guide_len"]:
        return {"available": False, "abstain": True, "enzyme": enz,
                "note": f"{enz} needs a {spec['guide_len']}-nt protospacer (got {len(g)})"}

    cached = _replay_cache(g, enz, max_mismatch)
    if cached is not None:
        return {"available": True, "abstain": False, "enzyme": enz, "guide": g, "pam": spec["pam"],
                "source": "cache", "max_mismatch": int(max_mismatch), "n_sites": len(cached), "sites": cached,
                "note": "genome-wide enumeration replayed from the committed GRCh38 Cas-OFFinder cache"}

    if allow_scan and casoffinder_available() and genome_path:
        sites = scan_local(g, enz, genome_path, max_mismatch)
        return {"available": True, "abstain": False, "enzyme": enz, "guide": g, "pam": spec["pam"],
                "source": "scan", "max_mismatch": int(max_mismatch), "n_sites": len(sites), "sites": sites,
                "note": "genome-wide Cas-OFFinder scan over GRCh38 (VM)"}

    return {"available": False, "abstain": True, "enzyme": enz, "guide": g, "pam": spec["pam"],
            "source": "none", "cached_guides": [gg for (ee, gg) in enumerated_guides() if ee == enz],
            "note": "genome-wide enumeration for a novel guide runs on the VM (casoffinder:tools over GRCh38); "
                    "this surface replays the committed cache or abstains. Cached guides are listed; a VM scan "
                    "is required to enumerate a new guide (no fabrication of sites)."}
