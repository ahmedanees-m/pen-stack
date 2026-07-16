#!/usr/bin/env python3
"""One-command reproduction of every PEN-STACK result that runs on the committed data and the demo atlas -
no external download, no API key. This is what `make repro` runs on a fresh clone; the genome-wide atlas
benchmarks that need the full Zenodo release are in `make repro-full`.

Each block is independent: a block that cannot run (a missing optional dependency, say) prints why and the
script continues, so a fresh clone always gets a useful report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hr(title: str) -> None:
    print("\n" + "=" * 88 + f"\n{title}\n" + "=" * 88)


def block(fn) -> bool:
    """Run one reproduction block. Returns True on success, False (and prints why) on failure, so the caller
    can exit non-zero: a reproduction harness that always exits 0 cannot signal a broken checkout."""
    try:
        fn()
        return True
    except Exception as e:  # noqa: BLE001 - collect the failure, report it, and fail the run at the end
        print(f"  [FAIL] {type(e).__name__}: {e}")
        return False


def demo_atlas() -> None:
    hr("1. Demo atlas: writable loci at the AAVS1 safe harbour (chr19 demo, no download)")
    import os
    os.environ.setdefault("PEN_ATLAS_DIR", str(ROOT / "data" / "demo"))
    from pen_stack.atlas import crosslink as cl
    cl.load_writability.cache_clear()
    df = cl.loci_for_gene("AAVS1", "k562").head(8)
    print(df[["chrom", "bin", "safety", "p_durable", "writability"]].to_string(index=False))
    print("  -> the deployed writability score at the canonical AAVS1 (PPP1R12C) safe harbour.")


def grounding() -> None:
    hr("2. Grounding evaluation (LLM on), replayed offline from the committed transcript cache")
    from pen_stack.validate.ungrounded_baseline import run_model
    G = json.load(open(ROOT / "benchmarks/grounding_llm_on/adversarial_goals.json"))
    plan = [(g["gene"], g["goal"]) for g in G["plan_goals"]]
    ung = [(g["gene"], g["goal"]) for g in G["ungroundable_goals"]]
    print(f"  probe: {len(plan)} planning goals + {len(ung)} ungroundable questions, LLM live (cached)")
    print(f"  {'model':<16}{'naive plan-fab':>16}{'coached plan-fab':>18}")
    for label in ("claude_haiku45", "nemotron", "qwen2.5_1.5b"):
        r = run_model(label, offline=True, goals=plan, ungroundable=ung)
        if not r["available"]:
            continue
        n = r["by_condition"]["naive"]["plan_goals"]["fabrication_rate"]
        c = r["by_condition"]["coached"]["plan_goals"]["fabrication_rate"]
        print(f"  {label:<16}{n:>16.1%}{c:>18.1%}")
    print("  grounded PEN-Agent: 0.0 under any prompt (copies every number from a validated tool call).")


def agentic() -> None:
    hr("3. Agentic baseline: the LLM drives the validated tools (committed audit result)")
    m = json.load(open(ROOT / "benchmarks/agentic_baseline/metrics.json"))
    for k, a in m["llm_agents"].items():
        print(f"  {a['model']:<36} drove {a['llm_driven_runs']}/{a['n_goals']} goals, "
              f"no-fabrication audit {'PASS' if a['no_fabrication_pass'] else 'FAIL'}")
    dg = m["deterministic_gate"]
    print(f"  deterministic gate (no LLM): {dg['grounded_tasks_matched']}/{dg['n_goals']} goals, "
          f"{'PASS' if dg['no_fabrication_pass'] else 'FAIL'}")


def headline_metrics() -> None:
    hr("4. Benchmark headline metrics (the primary result is recomputed from source; secondaries are echoed)")
    peh = json.load(open(ROOT / "benchmarks/position_effect_human/metrics.json"))
    fh = peh.get("fresh_sealed_heldout", {})
    print("  Expression-robustness head (human K562, sealed held-out chr3/8/12):")
    print(f"    shipped head Spearman rho = {fh.get('shipped_twin_full_rho')} "
          f"(independent variant {fh.get('independent_variant_rho')}); "
          f"best chromatin baseline {fh.get('best_baseline_rho')}")
    print("    ^ this primary headline is RE-DERIVED from the committed source table by `make repro-human` "
          "(scripts/p2_build_human_head.py), not merely read from this file.")
    null = peh.get("mouse_to_human_sealed_null", {})
    print(f"    cross-species null: shipped mouse axis rho = {null.get('shipped_mouse_axis_rho')} "
          f"vs LAD baseline {null.get('best_baseline_lad_rho')}")
    # The two secondary numbers below are ECHOED from their sealed, provenance-stamped metrics files: their
    # full recomputation needs data that is not committed to the clone (the genome-wide K562 atlas / the hg17
    # genome), so this block reports the sealed values rather than claiming to recompute them here.
    gt = json.load(open(ROOT / "benchmarks/genotox_panel/metrics.json"))
    ca = gt.get("companion_axis_discriminability_matched_controls", {})
    print(f"  Clinical genotoxicity panel ({gt.get('benchmark', '')}): feature-matched writability AUROC = "
          f"{ca.get('auroc_writability')} (95% CI {ca.get('auroc_writability_ci95')}) "
          f"vs safety-only {ca.get('auroc_safety_baseline')}")
    print("    [sealed metric; recomputation needs the genome-wide K562 atlas -> `make repro-full`]")
    ic = json.load(open(ROOT / "benchmarks/offtarget/integrase_chalberg/metrics.json"))
    ica = ic.get("metrics", {}).get("auroc", {})
    print(f"  Integrase off-target ({ic.get('benchmark', '')[:70]}): AUROC = {ica.get('model')} "
          f"(vs attP-similarity {ica.get('attp_sim_baseline')})")
    print("    [sealed pre-registered metric; recomputation needs the hg17 genome, see that benchmark's "
          "README.md]")
    print("  (full metrics + confidence intervals in each benchmarks/<name>/metrics.json)")


if __name__ == "__main__":
    print("PEN-STACK one-command reproduction (committed data + demo atlas; no download, no key)")
    results = {f.__name__: block(f) for f in (demo_atlas, grounding, agentic, headline_metrics)}
    print("\nFor the full genome-wide atlas benchmarks (position-effect leaderboard, GSH discrimination), "
          "run `make fetch` with ZENODO_DOI set, then `make repro-full`.")
    failed = [name for name, ok in results.items() if not ok]
    if failed:
        print(f"\nREPRODUCTION INCOMPLETE: {len(failed)}/{len(results)} block(s) failed on the committed "
              f"data: {', '.join(failed)}. A clean checkout should run every block; investigate before "
              f"trusting the results.")
        sys.exit(1)
    print(f"\nReproduction complete: all {len(results)} blocks ran on the committed data.")
    sys.exit(0)
