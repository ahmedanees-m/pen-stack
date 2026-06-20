"""CD4 / MHC-II epitope-load axis for the writer enzyme AND the capsid (v6.9 PEN-IMMUNE, G-WS1).

The dominant immunogenicity driver for a protein therapeutic is **MHC-II / CD4 help -> anti-drug antibodies
(ADA)**, exactly what the v5.x immune profile omitted (it did CD8/MHC-I via MHCflurry only). And the **editor
protein itself is immunogenic** (Cas9 elicits MHC-II-presented CD4 responses, Simhadri et al., Nat Commun 2021,
10.1038/s41467-021-25414-9; bridge recombinases / serine integrases are bacterial/phage), yet Stage G scored
only the capsid. v6.9 adds an MHC-II epitope-load axis over the **writer** as a distinct antigen.

PRODUCTION method (v6.9.1/6.9.2): the **real, licensed NetMHCIIpan-4.0** eluted-ligand %Rank over a frequent HLA-II
panel (residue-coverage metric), run on the VM with only the derived fractions cached (`configs/mhc_epitope_oracle.yaml`);
`mhc2_epitope_load(seq, name)` returns the real value for a cached antigen and otherwise **abstains** (no production
proxy). A population-level proxy, never a patient-HLA-specific magnitude (a known-unknown). Whether the epitopes
drive ADA depends on self-tolerance (foreign vs self), handled in `ada_risk`.

OFFLINE-ONLY fallback (`mhc2_proxy_estimate`, NOT the production axis): a documented, dependency-free PROMISCUOUS-
binder density, MHC-II presents a 9-mer core in an open groove whose **P1 pocket** is the dominant hydrophobic
anchor (M/F/Y/W/L/I/V; Stern & Wiley, Nature 1994) with secondary pockets at P4/P6/P9 (Southwood 1998). Provided for
offline triage where NetMHCIIpan cannot be run; the production axis uses the real tool and abstains otherwise.
"""
from __future__ import annotations

from functools import lru_cache

from pen_stack._resources import resource

_AA = set("ACDEFGHIKLMNPQRSTVWY")
P1_ANCHOR = set("MFYWLIV") # large hydrophobic, the dominant MHC-II P1 anchor (Stern & Wiley 1994)
_FAVORABLE = set("AVLIMFYWSTNQGC") # favorable at secondary pockets (hydrophobic / small / polar-uncharged)
_DISFAVORED = set("DEKRP") # charged / proline disfavored at anchor positions
MHC2_DOIS = ["10.1038/35030019", "10.1038/s41467-021-25414-9"] # Stern&Wiley groove; Cas9 MHC-II (Simhadri 2021)


def _clean(seq: str) -> str:
    return "".join(c for c in str(seq).upper() if c in _AA)


def _core_is_binder(core: str) -> tuple[bool, float]:
    """A 9-mer core is a promiscuous-binder candidate iff P1 (pos0) is a strong hydrophobic anchor AND >=2 of the
    secondary pockets P4/P6/P9 are favorable with no disfavored residue at an anchor position."""
    if core[0] not in P1_ANCHOR:
        return False, 0.0
    sec = sum(1 for p in (3, 5, 8) if core[p] in _FAVORABLE)
    pen = sum(1 for p in (0, 3, 5, 8) if core[p] in _DISFAVORED)
    score = 1.0 + 0.5 * sec - 0.5 * pen
    return (sec >= 2 and pen == 0), round(score, 3)


def mhc2_binder_cores(seq: str) -> list[tuple[int, str, float]]:
    """All promiscuous-binder 9-mer cores in the sequence: (start_index, core, score)."""
    s = _clean(seq)
    out = []
    for i in range(len(s) - 8):
        ok, sc = _core_is_binder(s[i:i + 9])
        if ok:
            out.append((i, s[i:i + 9], sc))
    return out


@lru_cache(maxsize=1)
def _real_cache() -> dict:
    """The REAL NetMHCIIpan-4.0 EL %Rank epitope-load cache (configs/mhc_epitope_oracle.yaml), computed over a
    frequent HLA-II panel on the VM. Only the derived fractions are shipped (the licensed binary is never
    distributed). Empty dict if the cache is absent (then the documented proxy is used)."""
    try:
        import yaml
        return yaml.safe_load(resource("configs/mhc_epitope_oracle.yaml").read_text(encoding="utf-8")) or {}
    except Exception: # noqa: BLE001
        return {}


def real_mhc2_load(name: str) -> dict | None:
    """The real NetMHCIIpan-4.0 epitope load for a bundled antigen by name, or None when not cached."""
    rec = (_real_cache().get("mhc2") or {}).get(name)
    if not rec:
        return None
    panel = (_real_cache().get("method") or {}).get("hla2_panel", [])
    return {"epitope_density": rec["epitope_fraction_strong"], "mhc2_immune_score": rec["immune_score"],
            "n_covered": rec.get("n_covered"), "length": rec.get("length"),
            "method": f"NetMHCIIpan-4.0 EL %Rank<=2, {rec.get('metric', 'residue coverage')}, frequent HLA-II "
                      f"panel ({len(panel)} alleles): {', '.join(panel)}",
            "status": "population-level (frequent-HLA panel; NetMHCIIpan-4.0 eluted-ligand), coverage-gated "
                      "(abstains for uncached antigens, NOT a distributional OOD gate); NOT a patient-HLA-specific "
                      "magnitude (known-unknown)", "backend": "netmhciipan_cache"}


def mhc2_epitope_load(seq: str, name: str | None = None) -> dict:
    """MHC-II epitope load, the REAL NetMHCIIpan-4.0 cache when the antigen `name` is cached; otherwise ABSTAINS
    (no proxy: an uncached sequence is a known-unknown, not a guessed number). To ground a new sequence,
    add it to configs/writer_sequences.fasta and re-run scripts/p1_build_mhc.py on the VM. Score convention:
    1 = least presentable (matches the MHC-I axis)."""
    if name:
        real = real_mhc2_load(name)
        if real:
            return real
    return {"epitope_density": None, "mhc2_immune_score": None, "backend": "abstain",
            "method": "NetMHCIIpan-4.0 (real)", "available": False,
            "status": "NetMHCIIpan-4.0 not run for this sequence, NO proxy (abstains, known-unknown). Run "
                      "scripts/p1_build_mhc.py over its FASTA on the VM to ground it."}


def mhc2_proxy_estimate(seq: str) -> dict:
    """OFFLINE-ONLY estimate (NOT used by the profile): a documented promiscuous-binder density (P1 hydrophobic
    anchor + P4/P6/P9 pockets; Stern & Wiley 1994; Southwood 1998). Provided for offline triage where NetMHCIIpan
    cannot be run; the production axis uses the real tool and abstains otherwise."""
    s = _clean(seq)
    n_cores = max(0, len(s) - 8)
    binders = mhc2_binder_cores(s)
    density = (len(binders) / n_cores) if n_cores else 0.0
    return {"epitope_density": round(density, 4), "mhc2_immune_score": round(1.0 - min(density, 1.0), 4),
            "n_promiscuous_binders": len(binders), "backend": "proxy_offline_only",
            "method": "DOCUMENTED PROXY, offline triage only, NOT the production axis (which uses NetMHCIIpan-4.0)"}


# ---- bundled writer / control sequences (real UniProt, configs/writer_sequences.fasta) --------
@lru_cache(maxsize=1)
def writer_sequences() -> dict:
    """Parse the bundled writer/control FASTA -> {name: {seq, origin, family, accession}}."""
    txt = resource("configs/writer_sequences.fasta").read_text(encoding="utf-8")
    out: dict = {}
    name = seq = origin = family = acc = None

    def _flush():
        if name:
            out[name] = {"seq": seq, "origin": origin, "family": family, "accession": acc}
    for line in txt.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith(">"):
            _flush()
            head = line[1:].strip()
            tok = head.split()
            name, acc = (tok[0].split("|") + [None])[:2]
            kv = dict(p.split("=", 1) for p in tok[1:] if "=" in p)
            origin, family, seq = kv.get("origin"), kv.get("family"), ""
        else:
            seq = (seq or "") + line.strip()
    _flush()
    return out


def writer_family_to_sequence(writer_family: str) -> dict | None:
    """Map a design's writer family (e.g. 'bridge_IS110', 'serine_integrase', 'Cas9') to a bundled writer
    sequence record, or None when no representative sequence is bundled (then the axis abstains)."""
    fam = (writer_family or "").lower()
    seqs = writer_sequences()
    for name, rec in seqs.items():
        f = (rec.get("family") or "").lower()
        if rec.get("origin") == "self":
            continue
        if fam and (fam in f or f in fam or fam in name.lower()):
            return {"name": name, **rec}
    if "cas9" in fam or "nuclease" in fam:
        return {"name": "SpCas9", **seqs.get("SpCas9", {})} if "SpCas9" in seqs else None
    return None
