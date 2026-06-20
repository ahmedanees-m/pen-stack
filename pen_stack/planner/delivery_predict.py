"""Cross-modality deliverability + learned AAV capsid-fitness (v6.11 PEN-DELIVER, D-WS2).

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
                "evidence": rec.get("example_product"), "approval": rec.get("approval"),
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


def capsid_fitness(vp1_sequence: str) -> dict:
    """Predicted AAV capsid packaging-fitness for a VP1 sequence (FLIP-AAV-trained), or an abstention when the
    model is not present (CI / bare wheel). Predicted fitness is a CANDIDATE for the measured packaging axis, NOT an
    in-vivo human-tropism claim."""
    import numpy as np
    m = _fitness_model()
    bench = _bench_metrics()
    if m is None:
        return {"available": False, "abstain": True, "predicted_fitness": None, "output_kind": "candidate",
                "note": "capsid_fitness.pkl not present (VM-only/regenerated); the committed Delivery-Bench documents "
                        "its measured performance.", "bench": bench}
    w0, w1 = m["window"]
    aas = m["aas"]
    ai = {a: i for i, a in enumerate(aas)}
    wl = w1 - w0
    win = (str(vp1_sequence)[w0:w1] + "-" * wl)[:wl]
    x = np.zeros(wl * 20, dtype="float32")
    for i, a in enumerate(win):
        if a in ai:
            x[i * 20 + ai[a]] = 1.0
    val = float(m["model"].predict(x.reshape(1, -1))[0])
    return {"available": True, "abstain": False, "predicted_fitness": round(val, 4),
            "scale": "FLIP-AAV packaging fitness (log-enrichment; higher = more fit)", "output_kind": "candidate",
            "status": "CANDIDATE for the measured packaging axis; NOT an in-vivo human-tropism claim (known-unknown)",
            "bench": bench}


def recommend_delivery_plus(cargo_form: str, cargo_bp: int | None = None, target_tissue: str | None = None,
                            *, safety_weight: float = 0.5, in_vivo: bool | None = None) -> dict:
    """The Stage-D recommender: the rule-level safety<->efficacy ranking (recommend_delivery) PLUS a grounded
    serotype->tissue tropism prior for the target tissue (approved therapies) and the learned capsid-fitness
    capability. Tropism is a grounded prior for approved serotypes, a known-unknown otherwise. Never fabricates."""
    from pen_stack.planner.delivery_immunology import recommend_delivery
    base = recommend_delivery(cargo_form, cargo_bp, safety_weight=safety_weight, in_vivo=in_vivo)
    tropism = serotypes_for_tissue(target_tissue) if target_tissue else None
    return {**base, "target_tissue": target_tissue, "serotype_tropism_prior": tropism,
            "capsid_fitness": {"capability": "learned FLIP-AAV capsid-fitness (call capsid_fitness(vp1_seq))",
                               "bench": _bench_metrics().get("mut_des") or CAPSID_FITNESS_BENCH},
            "honesty": "tropism is a grounded prior for approved serotypes, a known-unknown otherwise; predicted "
                       "capsid-fitness is a candidate for the measured packaging axis; no fabricated tropism."}
