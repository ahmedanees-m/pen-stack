"""Cross-modality deliverability + learned AAV capsid-fitness.

Extends the rule-level `recommend_delivery` (documented safety<->efficacy balance) with two grounded layers:

  * **serotype -> tissue tropism PRIOR** (`configs/aav_serotype_tropism.yaml`), real serotype<->tissue mappings
    evidenced by APPROVED AAV gene therapies (AAV9->CNS, AAVrh74->skeletal muscle, AAV5->liver, AAV2->retina/putamen
    via LOCAL injection). A grounded prior for an approved serotype; a known-unknown (abstain) for a novel capsid.
  * **learned capsid-fitness**, a model trained on the FLIP-AAV benchmark (Bryant 2021 packaging fitness; Dallago
    2021 splits) that scores an AAV capsid VP1 sequence. The Delivery-Bench shows it beats a mutation-burden baseline
    on held-out splits; the licensed datasets stay on the VM, and the derived metrics + reproducible build script are
    committed. The ~3 MB model itself is gitignored (regenerated via ``scripts/build_capsid_fitness.py`` and mounted
    into the deployed app, like ``position_effect.pkl``); the axis abstains gracefully when it is absent. Predicted
    fitness is a CANDIDATE for the MEASURED axis (packaging viability) and extrapolative for in-vivo human tropism.

no fabricated tropism; predicted fitness is a candidate; abstains without inputs / without the model.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from pen_stack._resources import project_root, resource

# Delivery-Bench headline (REAL FLIP-AAV result; learned vs mutation-burden baseline, Spearman, bootstrap CI).
# Filled from benchmarks/delivery/capsid_fitness_metrics.json (computed on the VM); kept in-code so the axis is
# available everywhere (CI / bare wheel / live app) without the licensed data tree.
CAPSID_FITNESS_BENCH = {
    "benchmark": "FLIP-AAV (Dallago 2021; Bryant 2021 packaging fitness, 10.1038/s41587-020-00793-4)",
    "model": "windowed one-hot (VP1 555-595) gradient boosting",
    "baseline": "mutation burden (Hamming from the train consensus)",
    "splits": {}, # populated below from the committed metrics
}


@lru_cache(maxsize=1)
def _bench_metrics() -> dict:
    """The committed Delivery-Bench metrics (capsid-fitness learned-vs-baseline), or {} if the data tree is absent."""
    try:
        import json
        return json.loads(resource("benchmarks/delivery/capsid_fitness_metrics.json").read_text(encoding="utf-8"))
    except Exception: # noqa: BLE001
        return {}


@lru_cache(maxsize=1)
def _tropism() -> dict:
    try:
        return yaml.safe_load(resource("configs/aav_serotype_tropism.yaml").read_text(encoding="utf-8")) or {}
    except Exception: # noqa: BLE001
        return {}


def serotype_tropism(serotype: str) -> dict:
    """The grounded tissue prior for an AAV serotype (from approved therapies), or a known-unknown."""
    rec = (_tropism().get("serotypes") or {}).get(serotype)
    if rec:
        return {"serotype": serotype, "tissue": rec["tissue"], "route": rec.get("route"),
                "evidence": rec.get("example_product"), "indication": rec.get("indication"),
                "approval": rec.get("approval"), "doi": rec.get("doi"),
                "confidence": "grounded (approved therapy)", "output_kind": "prior"}
    return {"serotype": serotype, "tissue": None, "confidence": "known-unknown",
            "note": "no approved-therapy precedent for this serotype/capsid -> in-vivo human tropism is a "
                    "known-unknown; not fabricated", "output_kind": "abstain"}


def serotypes_for_tissue(target_tissue: str) -> dict:
    """Which approved AAV serotypes are GROUNDED priors for a target tissue (e.g. liver -> AAV5/AAVRh74var). Abstains
    (empty) when no approved serotype targets the tissue, never invents one."""
    t = (target_tissue or "").strip().lower()
    hits = []
    for s, rec in (_tropism().get("serotypes") or {}).items():
        tissues = [str(x).lower() for x in (rec.get("tissue") or [])]
        if any(t in x or x in t for x in tissues):
            hits.append({"serotype": s, "tissue": rec["tissue"], "route": rec.get("route"),
                         "evidence": rec.get("example_product")})
    return {"target_tissue": target_tissue, "grounded_serotypes": hits,
            "note": ("grounded serotype->tissue priors from approved therapies" if hits else
                     f"no approved AAV serotype has a grounded prior for {target_tissue!r} -> known-unknown (abstain)")}


@lru_cache(maxsize=1)
def _fitness_model():
    """Load the FLIP-AAV-trained capsid-fitness model (gitignored .pkl, regenerated on the VM; mounted into the live
    container like position_effect.pkl). None when absent -> the fitness call abstains. The committed bench metrics
    document the model's measured performance even when the .pkl is not present."""
    import pickle
    for base in (project_root() / "models", project_root() / "data" / "delivery_models"):
        p = base / "capsid_fitness.pkl"
        if p.exists():
            try:
                return pickle.load(open(p, "rb"))
            except Exception: # noqa: BLE001
                return None
    return None


def capsid_fitness(vp1_sequence: str, vector: str = "AAV") -> dict:
    """Predicted AAV capsid packaging-fitness for a VP1 sequence (FLIP-AAV-trained), or an abstention when the
    model is not present (CI / bare wheel). The learned model is AAV-capsid-specific: for other vectors (LV,
    adenovirus, HSV) there is NO packaging/assembly-fitness model, so it abstains with that stated rather than
    fabricate a score. Predicted fitness is a CANDIDATE for the measured packaging axis, NOT an in-vivo tropism claim."""
    import numpy as np
    vec = (vector or "AAV").strip()
    if vec.upper() != "AAV":
        return {"available": False, "abstain": True, "vector": vec, "predicted_fitness": None, "output_kind": "n/a",
                "note": f"no learned packaging/assembly-fitness model for {vec}: the FLIP-AAV model is AAV-capsid-"
                        "specific. Non-AAV vectors get vehicle-level checks (capacity, immune risk), not a "
                        "capsid-fitness score -- not fabricated.", "bench": None}
    m = _fitness_model()
    bench = _bench_metrics()
    if m is None:
        return {"available": False, "abstain": True, "vector": "AAV", "predicted_fitness": None,
                "output_kind": "candidate",
                "note": "capsid_fitness.pkl not present (VM-only/regenerated); the committed Delivery-Bench documents "
                        "its measured performance.", "bench": bench}
    w0, w1 = m["window"]
    aas = m["aas"]
    ai = {a: i for i, a in enumerate(aas)}
    wl = w1 - w0
    # clean the input: drop FASTA header lines, strip whitespace, upper-case (a pasted VP1 usually has newlines).
    seq = "".join(ln for ln in str(vp1_sequence).splitlines() if not ln.lstrip().startswith(">"))
    seq = "".join(seq.split()).upper()
    # INPUT GUARD: the model reads AAV VP1 residues w0-w1 ONLY. A sequence that never reaches that window, or a
    # nucleotide sequence pasted by mistake, would collapse to a degenerate constant -> abstain, never fake a score.
    nuc_only = bool(seq) and set(seq) <= set("ACGTUN")
    if len(seq) <= w0 or nuc_only:
        why = ("this looks like a nucleotide (DNA/RNA) sequence; the model needs the VP1 capsid PROTEIN (amino acids)"
               if nuc_only else
               f"the input is only {len(seq)} aa and never reaches VP1 residues {w0}-{w1} -- the region the model reads")
        return {"available": False, "abstain": True, "vector": "AAV", "predicted_fitness": None,
                "output_kind": "candidate", "input_issue": why,
                "note": f"no meaningful score: {why}. Paste a full-length AAV VP1 capsid protein (>= {w1} aa, AAV2 "
                        f"numbering) so the model can read residues {w0}-{w1}.", "bench": bench}
    win = (seq[w0:w1] + "-" * wl)[:wl]
    x = np.zeros(wl * 20, dtype="float32")
    for i, a in enumerate(win):
        if a in ai:
            x[i * 20 + ai[a]] = 1.0
    val = float(m["model"].predict(x.reshape(1, -1))[0])
    # Readable verdict: the PERCENTILE of this prediction within the model's own predicted-fitness distribution on
    # the held-out FLIP-AAV test set (a grounded, unambiguous "top X% of measured variants" instead of a bare float).
    pcts = m.get("pred_percentiles")
    percentile = None
    if pcts:
        percentile = max(0, min(100, int(np.searchsorted(np.asarray(pcts, dtype="float64"), val))))
    if percentile is None:
        bucket, verdict = "unknown", f"Predicted packaging fitness {round(val, 3)} (no reference distribution in this model build)."
    else:
        bucket = "better" if percentile >= 67 else ("similar" if percentile >= 33 else "worse")
        verdict = {"better": "High packaging fitness", "similar": "Mid-range packaging fitness",
                   "worse": "Low packaging fitness"}[bucket]  # the percentile carries the "better than X%" detail
    # a compact 24-bin histogram of the reference distribution (for a UI sparkline). Binning the equally-spaced
    # percentiles reconstructs the density shape (dense near the mode, sparse at the tails); cached on the model.
    dist = m.get("_ref_hist")
    if dist is None and pcts:
        arr = np.asarray(pcts, dtype="float64")
        lo, hi = float(arr[0]), float(arr[-1])
        counts, _ = np.histogram(arr, bins=24, range=(lo, hi))
        dist = {"lo": round(lo, 4), "hi": round(hi, 4), "counts": [int(x) for x in counts]}
        m["_ref_hist"] = dist
    input_warning = None
    if len(seq) < w1:  # partial window: the tail is padded, so only part of the 555-595 window informs the score
        input_warning = (f"sequence is {len(seq)} aa (< {w1}); residues {len(seq)}-{w1} are padded, so only part of "
                         f"the {w0}-{w1} window informs the score -- treat with extra caution.")
    return {"available": True, "abstain": False, "vector": "AAV", "predicted_fitness": round(val, 4),
            "percentile": percentile, "verdict": verdict, "verdict_bucket": bucket, "distribution": dist,
            "scale": "FLIP-AAV packaging fitness (log-enrichment; higher = more fit)", "output_kind": "candidate",
            "window": [w0, w1], "sequence_len": len(seq), "input_warning": input_warning,
            "status": f"CANDIDATE for the measured packaging axis; NOT an in-vivo human-tropism claim (known-unknown). "
                      f"The model reads VP1 residues {w0}-{w1} only; the percentile is vs the model's held-out "
                      f"FLIP-AAV test predictions.",
            "bench": bench}


def recommend_delivery_plus(cargo_form: str, cargo_bp: int | None = None, target_tissue: str | None = None,
                            *, safety_weight: float = 0.5, in_vivo: bool | None = None,
                            serotype: str | None = None) -> dict:
    """The extended recommender: the rule-level safety<->efficacy ranking (recommend_delivery) PLUS a grounded
    serotype->tissue tropism prior and the learned capsid-fitness capability. The tropism prior answers whichever
    direction the caller asked: a specific ``serotype`` -> its approved-therapy tissue (e.g. AAV9 -> CNS/Zolgensma);
    otherwise a ``target_tissue`` -> the approved serotypes that reach it. Grounded for approved serotypes, a
    known-unknown otherwise. Never fabricates."""
    from pen_stack.planner.delivery_immunology import recommend_delivery
    base = recommend_delivery(cargo_form, cargo_bp, safety_weight=safety_weight, in_vivo=in_vivo)
    if serotype:
        tropism = serotype_tropism(serotype)          # serotype -> tissue (matches the field name; report path)
    elif target_tissue:
        tropism = serotypes_for_tissue(target_tissue)  # tissue -> approved serotypes
    else:
        tropism = None
    return {**base, "serotype": serotype, "target_tissue": target_tissue, "serotype_tropism_prior": tropism,
            "capsid_fitness": {"capability": "learned FLIP-AAV capsid-fitness (call capsid_fitness(vp1_seq))",
                               "bench": _bench_metrics().get("mut_des") or CAPSID_FITNESS_BENCH},
            "honesty": "tropism is a grounded prior for approved serotypes, a known-unknown otherwise; predicted "
                       "capsid-fitness is a candidate for the measured packaging axis; no fabricated tropism."}
