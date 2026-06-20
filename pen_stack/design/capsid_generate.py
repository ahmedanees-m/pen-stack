"""Verify-gated generative AAV capsid candidates (v6.11 PEN-DELIVER, D-WS3).

Proposes engineered AAV capsid variants in the mutagenized VP1 region, scores them with the learned FLIP-AAV
capsid-fitness model, and keeps only candidates above a fitness threshold, the verifier-as-discriminator pattern
(v5.8): GENERATE proposes, the fitness model + biosecurity context DISPOSE. Every survivor is a CANDIDATE,
never asserted to assemble or to have any in-vivo tropism. Abstains when the fitness model is not present (no
fabricated capsids).

a generated capsid's predicted fitness is for the MEASURED packaging axis only; assembly, in-vivo tropism,
and immunogenicity are not claimed (the latter routes through Stage G). This is a design proposer, not a validation.
"""
from __future__ import annotations

_AAS = "ACDEFGHIKLMNPQRSTVWY"


def _mutate(seq: str, region: tuple[int, int], n_mut: int, rng) -> str:
    s = list(seq)
    lo, hi = region
    positions = rng.sample(range(lo, min(hi, len(s))), min(n_mut, max(0, min(hi, len(s)) - lo)))
    for p in positions:
        s[p] = _AAS[rng.randrange(len(_AAS))]
    return "".join(s)


def generate_capsid_candidates(wt_vp1: str, n: int = 200, max_mut: int = 4, fitness_threshold: float | None = None,
                               seed: int = 7, top: int = 20) -> dict:
    """Propose AAV capsid variants (random substitutions in the VP1 555-595 mutagenized window), score with the
    learned capsid-fitness model, and return the top survivors above ``fitness_threshold`` (defaults to the WT's
    predicted fitness). Candidates are flagged; abstains when the fitness model is absent, never fabricates."""
    import random
    from pen_stack.planner.delivery_predict import capsid_fitness
    wt = capsid_fitness(wt_vp1)
    if not wt.get("available"):
        return {"available": False, "abstain": True, "candidates": [], "output_kind": "candidate",
                "note": "capsid-fitness model not present -> cannot score generated capsids; no fabrication.",
                "bench": wt.get("bench")}
    rng = random.Random(seed)
    thr = fitness_threshold if fitness_threshold is not None else wt["predicted_fitness"]
    region = (555, 595)
    seen = set()
    scored = []
    for _ in range(max(1, n)):
        nm = rng.randint(1, max_mut)
        cand = _mutate(wt_vp1, region, nm, rng)
        if cand == wt_vp1 or cand in seen:
            continue
        seen.add(cand)
        f = capsid_fitness(cand)["predicted_fitness"]
        scored.append({"vp1_window": cand[region[0]:region[1]], "predicted_fitness": f,
                       "n_mut_in_region": sum(1 for a, b in zip(cand[region[0]:region[1]],
                                                                wt_vp1[region[0]:region[1]]) if a != b),
                       "passes_threshold": bool(f >= thr), "output_kind": "candidate"})
    survivors = sorted([c for c in scored if c["passes_threshold"]],
                       key=lambda c: c["predicted_fitness"], reverse=True)[:top]
    return {"available": True, "abstain": False, "wt_predicted_fitness": wt["predicted_fitness"],
            "fitness_threshold": round(float(thr), 4), "n_proposed": len(scored), "n_survivors": len(survivors),
            "candidates": survivors, "output_kind": "candidate",
            "verifier": "learned FLIP-AAV capsid-fitness (verifier-as-discriminator, v5.8); fitness >= WT kept",
            "honesty": "CANDIDATES, predicted packaging fitness only; assembly, in-vivo tropism, and "
                       "immunogenicity are NOT claimed (immunogenicity routes through Stage G). A design proposer, "
                       "not a validation. Run a biosecurity/verify() gate before any synthesis."}
