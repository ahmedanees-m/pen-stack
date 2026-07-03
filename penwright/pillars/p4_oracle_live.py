"""P4 — live frontier-oracle flex: proving the agent's calls hit real foundation bio-models.

The winner pattern "requires the frontier model" means an agent whose numbers come from live Evo2 /
AlphaGenome forward passes, not a static cache — AND that can prove which is which. PEN-STACK's oracle mesh
already carries the machinery: a single OracleResult contract with a `provenance.source` field
(adapter | cache | hosted_api | local_gpu), an OOD gate (`in_scope` / `extrapolating`), the oracle's own
native uncertainty, and a candidate/claim guard. This module exercises that plumbing end to end and renders
it, so a demo can show, per oracle, "Evo2-40B LIVE" vs "cache replay" vs "deferred".

Honesty: on a machine with no keys and `PEN_STACK_ORACLE_NET` unset (CI / this sandbox), every hosted oracle
DEFERS or replays from the committed cache — reported as such. The point demonstrated here is that the
contract TAGS live vs cache correctly and gates OOD inputs; setting the flag + keys on the deployed VM turns
the same calls into real hosted Evo2 / AlphaGenome forward passes with `source="hosted_api"`. Nothing is
fabricated: a deferred oracle returns value None, never a made-up number.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _probe_calls() -> list[dict]:
    """Exercise the three genome oracles and capture the full provenance envelope of each result."""
    from pen_stack.oracles import genome
    probes = []

    # AlphaGenome variant effect — in-distribution
    r = genome.variant_effect("chr19:1010000 A>T", "chr19:1010000", in_distribution=True)
    probes.append(_envelope("AlphaGenome variant_effect (in-distribution)", r))
    # AlphaGenome variant effect — OOD (the gate must flip extrapolating/in_scope)
    r_ood = genome.variant_effect("chr19:1010000 A>T", "chr19:1010000", in_distribution=False)
    probes.append(_envelope("AlphaGenome variant_effect (out-of-distribution)", r_ood))
    # Evo2 generative DNA — a CANDIDATE (cannot enter a claim path)
    g = genome.generate_dna("ACGTACGTACGTACGT", n=16)
    probes.append(_envelope("Evo2 generate_dna (candidate)", g))
    # Evo2 zero-shot likelihood — a CLAIM-scope scalar
    s = genome.sequence_likelihood("ACGTACGTACGTACGTACGT")
    probes.append(_envelope("Evo2 sequence_likelihood (claim)", s))
    return probes


def _envelope(label: str, r) -> dict:
    return {
        "call": label,
        "oracle": r.oracle,
        "model": r.provenance.model,
        "version": r.provenance.version,
        "source": r.provenance.source,          # adapter | cache | hosted_api | local_gpu
        "available": r.available,
        "cached": r.cached,
        "value_is_none": r.value is None,
        "native_uncertainty": r.native_uncertainty,
        "output_kind": r.output_kind,            # claim | candidate | baseline
        "in_scope": r.in_scope,
        "extrapolating": r.extrapolating,        # the OOD gate
        "note": r.note,
    }


def _ood_gate_demo() -> dict:
    """Show the OOD gate flipping the scope flags between an in- and out-of-distribution call."""
    from pen_stack.oracles import genome
    ind = genome.variant_effect("chr7:5569177 A>G", "chr7:5569177", in_distribution=True)
    ood = genome.variant_effect("chrUn_rare:999 A>G", "chrUn_rare:999", in_distribution=False)
    return {
        "in_distribution": {"in_scope": ind.in_scope, "extrapolating": ind.extrapolating},
        "out_of_distribution": {"in_scope": ood.in_scope, "extrapolating": ood.extrapolating},
        "gate_flips": (ind.extrapolating is False and ood.extrapolating is True),
        "note": "OOD relative to the oracle's validity envelope is LABELLED (extrapolating=True / in_scope=False), "
                "never silently scored as if in-distribution.",
    }


def run(out_dir: str = "out/penwright") -> dict[str, Any]:
    """Exercise the oracle mesh, capture per-oracle live/cache/OOD provenance, and render a status figure.
    Returns a summary. Deterministic; makes no live network call unless PEN_STACK_ORACLE_NET=1 + keys are set."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from pen_stack.oracles import status
    os.makedirs(out_dir, exist_ok=True)

    st = status.oracle_status(probe=False)
    summ = status.summary()
    probes = _probe_calls()
    ood = _ood_gate_demo()
    net_live = os.getenv("PEN_STACK_ORACLE_NET") == "1"

    # frontier genome oracles we care about for the flex
    frontier = ["evo2", "alphagenome"]
    frontier_status = {name: {"execution": st[name]["execution"], "live": st[name]["live"],
                              "live_reason": st[name].get("live_reason"),
                              "latency_class": st[name].get("latency_class")}
                       for name in frontier if name in st}

    # ------------------------------------------------------------------ figure: oracle mesh live/cache/deferred
    names = list(st.keys())
    live = [1 if st[n]["live"] else 0 for n in names]
    hosted = [1 if st[n]["execution"] in ("hosted_api", "cloud_gpu", "local_gpu") else 0 for n in names]
    colors = ["#2f7d55" if lv else ("#c98a1a" if h else "#8a8a8a") for lv, h in zip(live, hosted)]
    fig, ax = plt.subplots(figsize=(11, 5))
    y = range(len(names))
    ax.barh(list(y), [1] * len(names), color=colors)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xticks([])
    ax.invert_yaxis()
    for i, n in enumerate(names):
        state = "LIVE" if st[n]["live"] else ("hosted (deferred/cache)" if hosted[i] else "in-process/baseline")
        ax.text(0.02, i, f"{state}", va="center", fontsize=8, color="white", fontweight="bold")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#2f7d55", label="live now"),
                       Patch(color="#c98a1a", label="hosted — deferred/cache here (live on VM w/ keys)"),
                       Patch(color="#8a8a8a", label="in-process / baseline")],
              loc="lower right", fontsize=8)
    ax.set_title("P4 — Oracle mesh: one OracleResult contract over the frontier bio-models\n"
                 "(source-tagged live vs cache; OOD-gated; candidate/claim-guarded)", fontsize=12)
    fig.tight_layout()
    fig_path = os.path.join(out_dir, "p4_oracle_mesh.png")
    fig.savefig(fig_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    metrics = {
        "pillar": "P4",
        "oracle_net_live_flag": net_live,
        "frontier_oracles": frontier_status,
        "live_now": summ["live"],
        "deferred": summ["deferred"],
        "probe_calls": probes,
        "ood_gate": ood,
        "provenance_sources_observed": sorted({p["source"] for p in probes}),
        "candidate_guard": "generate_dna returns output_kind='candidate' (as_claim() raises); it cannot enter a "
                           "claim path without writer-verification.",
        "no_fabrication": all(p["value_is_none"] for p in probes if not p["available"]),
        "wiring_completed_this_build": [
            "Evo2 sequence_likelihood: now cache-replayable + a guarded local forward-scoring path "
            "(source='local_gpu' when a live Evo2 backend scores; source='cache' on replay).",
        ],
        "how_to_go_live": "set PEN_STACK_ORACLE_NET=1 and provide NVIDIA_API_KEY (Evo2-40B) and "
                          "ALPHAGENOME_API_KEY + the alphagenome package; the same calls then return "
                          "source='hosted_api' with real forward-pass values.",
        "headline": ("The oracle mesh tags every result live vs cache (sources seen: {}), gates OOD inputs "
                     "(gate_flips={}), and guards generated DNA as a candidate — so a frontier-model call is "
                     "provably real when live and honestly deferred when not."
                     ).format(sorted({p["source"] for p in probes}), ood["gate_flips"]),
    }
    Path(os.path.join(out_dir, "p4_oracle_live.json")).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return {
        "pillar": "P4", "figure": fig_path, "metrics": os.path.join(out_dir, "p4_oracle_live.json"),
        "oracle_net_live": net_live, "live_oracles": summ["live"],
        "ood_gate_flips": ood["gate_flips"],
        "provenance_sources": sorted({p["source"] for p in probes}),
        "headline": metrics["headline"],
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2))
