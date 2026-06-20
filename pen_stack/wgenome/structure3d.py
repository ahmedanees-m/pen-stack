"""WS-C3 - 3D structural-risk via AlphaGenome contact-map deltas.

A cassette insertion can rewire 3D contacts and bring a distal enhancer into contact with an oncogene
promoter (enhancer hijacking). We simulate the insertion with AlphaGenome's `predict_variant` (the cassette
is the alternate allele - an insertion - so the model applies it to its own reference and handles the
coordinate shift server-side; no local FASTA needed). We predict the reference and edited 1 Mb contact maps
and compute:

  * insulation change at the insertion site (diamond insulation score, ref vs edited);
  * aberrant contact gain between the insertion site and a target oncogene promoter bin.

To isolate the *regulatory* effect from the pure coordinate-shift artifact, every metric is reported for a
strong-enhancer insert AND a length-matched neutral insert; the strong-minus-neutral difference is the
signal. Output is a `structural_risk` score + flag with a confidence field.

GATE G-C: this ships as a FLAG WITH CONFIDENCE, never a hard pass/fail. No ground-truth dataset of
insertion-induced hijacking exists, so this is NOT validated as a predictor - only sanity-checked on 11 known
enhancer-hijacking oncogenes (TAL1/LMO1/LMO2/TLX3/BCL11B/MYB in T-ALL, MECOM-GATA2 in AML, MYCN in
neuroblastoma, GFI1B, MYC) where a strong-enhancer insert should raise aberrant
contacts above a matched neutral insert. Contacts are cell-type-specific (default GM12878, EFO:0002784 -
K562 has no AlphaGenome Hi-C track); insertion changes coordinates in ways the model was not trained on.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np

from pen_stack.wgenome.providers import SEQ_LEN_1MB, AlphaGenomeProvider

_ROOT = Path(__file__).resolve().parents[2]
_CACHE = _ROOT / "data" / "alphagenome_cache"
HIC_ONTOLOGY = "EFO:0002784" # GM12878 - canonical deep Hi-C; K562 has no AlphaGenome contact track
CONTACT_BINS = 512 # 1 Mb / 512 ~ 2048 bp per contact bin


def _ucsc_ref(chrom: str, pos: int, length: int = 1) -> str:
    """Reference bases [pos, pos+length) on hg38 via the UCSC REST API (cached on disk)."""
    key = f"ucsc_{chrom}_{pos}_{length}"
    f = _CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))["dna"].upper()
    u = (f"https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom={chrom};"
         f"start={pos};end={pos + length}")
    d = json.load(urllib.request.urlopen(u)) # noqa: S310
    _CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"dna": d["dna"]}), encoding="utf-8")
    return d["dna"].upper()


def strong_enhancer_insert(n: int = 1600) -> str:
    """Simulated strong enhancer: tiled clusters of active-enhancer TF motif cores (ETS/GATA/AP-1/RUNX)."""
    motif = "GGAAGTGATAAGTGACTCAGGAAGTGACCACA" # GGAA(ETS) / GATA / TGACTCA(AP-1) / TGTGGT(RUNX-rc)
    return (motif * (n // len(motif) + 1))[:n]


def neutral_insert(n: int = 1600) -> str:
    """Length-matched neutral insert: low-complexity AT-rich filler (poor regulatory potential)."""
    return ("ATATATTAATTATAAT" * (n // 16 + 1))[:n]


def _contact_matrices(provider: AlphaGenomeProvider, chrom: str, pos: int, insert: str,
                      ontology: str = HIC_ONTOLOGY):
    """Reference + edited (insertion) 1 Mb contact matrices via predict_variant."""
    from alphagenome.data import genome
    from alphagenome.models import dna_client
    anchor = _ucsc_ref(chrom, pos, 1)
    var = genome.Variant(chromosome=chrom, position=pos, reference_bases=anchor,
                         alternate_bases=anchor + insert)
    interval = var.reference_interval.resize(SEQ_LEN_1MB)
    out = provider._client().predict_variant( # noqa: SLF001
        interval=interval, variant=var,
        requested_outputs=[dna_client.OutputType.CONTACT_MAPS], ontology_terms=[ontology])
    ref = np.asarray(out.reference.contact_maps.values)
    alt = np.asarray(out.alternate.contact_maps.values)
    return ref[..., 0] if ref.ndim == 3 else ref, alt[..., 0] if alt.ndim == 3 else alt


def insulation_score(mat: np.ndarray, idx: int, w: int = 10) -> float:
    """Diamond insulation: mean contact in the w x w square straddling position `idx`."""
    n = mat.shape[0]
    a, b = max(0, idx - w), min(n, idx + w)
    if a >= idx or b <= idx:
        return float("nan")
    return float(mat[a:idx, idx:b].mean())


def _bin_of(offset_bp: int) -> int:
    """Contact-map bin index for a genomic offset (bp) from the 1 Mb interval centre."""
    return int(round(CONTACT_BINS / 2 + offset_bp / (SEQ_LEN_1MB / CONTACT_BINS)))


# WS-UQ / UQ4 - calibrated confidence and abstention for the qualitative 3D flag. No calibrated probability is
# claimed (Gate G-C). The only computable confidence signal is the MAGNITUDE of the strong-minus-neutral
# separation: when it is within +/-ABSTAIN_EPS the strong and neutral inserts are indistinguishable, so the
# flag ABSTAINS rather than emit a direction it cannot justify. Larger separations are a low-confidence
# qualitative flag, never a calibrated risk.
ABSTAIN_EPS = 0.01


def uq4_confidence(aberrant: float) -> dict:
    """Structured confidence/abstention for the 3D structural-risk flag (UQ4). Heuristic, not calibrated."""
    mag = abs(float(aberrant))
    if mag <= ABSTAIN_EPS:
        level, abstain = "abstain", True
    elif mag <= 0.05:
        level, abstain = "low", False
    else:
        level, abstain = "qualitative_flag", False
    return {"calibrated": False, "level": level, "abstain": abstain,
            "epistemic_status": "not-computable" if abstain else "grounded-extrapolating",
            "basis": f"strong-minus-neutral separation magnitude {mag:.4f} vs abstain_eps {ABSTAIN_EPS}",
            "scope": "qualitative flag with confidence (Gate G-C); no calibrated probability, no coverage "
                     "guarantee - no ground-truth enhancer-hijacking dataset exists to calibrate against"}


def structural_risk(chrom: str, site_pos: int, oncogene_pos: int, ontology: str = HIC_ONTOLOGY,
                    provider: AlphaGenomeProvider | None = None, offline: bool = False) -> dict:
    """Strong-enhancer vs neutral insertion at `site_pos`; aberrant contact gain toward `oncogene_pos`."""
    provider = provider or AlphaGenomeProvider(assembly="hg38")
    ins_strong, ins_neutral = strong_enhancer_insert(), neutral_insert()
    key_src = f"struct3d|{chrom}|{site_pos}|{oncogene_pos}|{ontology}|{hashlib.sha256((ins_strong+ins_neutral).encode()).hexdigest()[:8]}"
    key = hashlib.sha256(key_src.encode()).hexdigest()[:24]
    cf = _CACHE / f"{key}.json"
    if cf.exists():
        cached = json.loads(cf.read_text(encoding="utf-8"))
        if cached.get("available") and not isinstance(cached.get("confidence"), dict):
            # upgrade legacy string-confidence cache entries to the UQ4 structured form (no recompute)
            cached["confidence"] = uq4_confidence(
                cached.get("aberrant_contact_gain_strong_minus_neutral", 0.0))
        return cached
    if offline or not provider.available():
        return {"available": False, "reason": "offline or AlphaGenome key absent", "key": key}

    site_idx = CONTACT_BINS // 2
    tgt_idx = _bin_of(oncogene_pos - site_pos)
    res = {}
    for label, insert in (("strong_enhancer", ins_strong), ("neutral", ins_neutral)):
        ref, alt = _contact_matrices(provider, chrom, site_pos, insert, ontology)
        ins_ref, ins_alt = insulation_score(ref, site_idx), insulation_score(alt, site_idx)
        t = min(tgt_idx, CONTACT_BINS - 1)
        contact_ref = float(ref[site_idx, t]) if 0 <= t < CONTACT_BINS else float("nan")
        contact_alt = float(alt[site_idx, t]) if 0 <= t < CONTACT_BINS else float("nan")
        res[label] = {"insulation_change": round(ins_alt - ins_ref, 5),
                      "oncogene_contact_gain": round(contact_alt - contact_ref, 5)}
    gain_strong = res["strong_enhancer"]["oncogene_contact_gain"]
    gain_neutral = res["neutral"]["oncogene_contact_gain"]
    aberrant = gain_strong - gain_neutral
    out = {"available": True, "chrom": chrom, "site_pos": site_pos, "oncogene_pos": oncogene_pos,
           "ontology": ontology, "target_bin_offset": tgt_idx - site_idx,
           "per_insert": res, "aberrant_contact_gain_strong_minus_neutral": round(aberrant, 5),
           "structural_risk": round(float(max(0.0, aberrant)), 5),
           "flag": bool(aberrant > 0),
           "confidence": uq4_confidence(aberrant),
           "key": key}
    _CACHE.mkdir(parents=True, exist_ok=True)
    cf.write_text(json.dumps(out, default=str), encoding="utf-8")
    return out


# Known enhancer-hijacking oncogenes (hg38) for the qualitative sanity check. Insertion site placed ~120 kb
# from the oncogene promoter (within a 1 Mb window / typical TAD reach). Scaled in v3.1.1 from 4 to 11 loci;
# oncogene_pos for the added loci is the GENCODE TSS (data/curated/gene_coords.parquet) - no hand-transcribed
# coordinates. These are canonical enhancer-hijacking oncogenes from the leukaemia/neuroblastoma literature
# (e.g. TAL1/LMO1/LMO2/TLX3/BCL11B/MYB in T-ALL, MECOM-GATA2 in AML, MYCN in neuroblastoma).
def _hj(chrom: str, pos: int) -> dict:
    return {"chrom": chrom, "oncogene_pos": pos, "site_pos": pos - 120_000}


HIJACK_LOCI = {
    "TAL1": _hj("chr1", 47_209_257),
    "LMO2": _hj("chr11", 33_859_520),
    "GFI1B": _hj("chr9", 132_990_996),
    "MYC": _hj("chr8", 127_735_434),
    "MYCN": _hj("chr2", 15_940_550), # neuroblastoma
    "MECOM": _hj("chr3", 169_083_499), # AML 3q26 (GATA2 distal enhancer hijacking)
    "GATA2": _hj("chr3", 128_479_427), # AML inv(3)/t(3;3)
    "LMO1": _hj("chr11", 8_224_309), # T-ALL
    "BCL11B": _hj("chr14", 99_169_287), # T-ALL (t(5;14))
    "MYB": _hj("chr6", 135_181_308), # T-ALL
    "TLX3": _hj("chr5", 171_309_248), # T-ALL (HOX11L2, t(5;14) BCL11B enhancer)
}


def sanity(ontology: str = HIC_ONTOLOGY, offline: bool = False, out: str | Path | None = None) -> dict:
    """C3 sanity check across the known hijacking loci: strong-enhancer insert should raise aberrant
    contacts above a matched neutral insert at more loci than not (qualitative, not a validated predictor)."""
    provider = AlphaGenomeProvider(assembly="hg38")
    rows = {}
    for name, c in HIJACK_LOCI.items():
        r = structural_risk(c["chrom"], c["site_pos"], c["oncogene_pos"], ontology, provider, offline)
        rows[name] = r
    scored = [v["aberrant_contact_gain_strong_minus_neutral"] for v in rows.values() if v.get("available")]
    report = {"available": bool(scored), "ontology": ontology, "n_loci": len(rows),
              "n_strong_gt_neutral": int(sum(1 for s in scored if s > 0)),
              "per_locus": {k: (v.get("aberrant_contact_gain_strong_minus_neutral") if v.get("available")
                                else v.get("reason")) for k, v in rows.items()},
              "sanity_pass": bool(scored and sum(1 for s in scored if s > 0) > len(scored) / 2),
              "scope": "qualitative sanity check only; ships as a flag with confidence (Gate G-C), never "
                       "a hard pass/fail; contacts are cell-type-specific (GM12878)."}
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps({"loci": rows, "summary": report}, indent=2, default=str),
                             encoding="utf-8")
    return report


if __name__ == "__main__": # pragma: no cover
    print(json.dumps(sanity(out=_ROOT / "out" / "structure3d_sanity.json"), indent=2, default=str))
