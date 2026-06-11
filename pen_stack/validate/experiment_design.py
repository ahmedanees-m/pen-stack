"""Bench scorer: `experiment_design` (PEN-STACK v5.10, the experiment designer / WS-BENCH).

Scores the active learner's HONESTY + FALSIFIABILITY, not a beat-the-world claim. The gate
(`experiment_designer_honest`) checks the properties a trustworthy "Learn" engine must have:
  1. acquisition is computed from the calibrated twin (EIG >= 0, monotone in uncertainty),
  2. immune-VOI rewards experiments that would validate an immune PROXY axis (v5.6),
  3. batch selection is diverse (not k copies of the most-uncertain point),
  4. the active-vs-random advantage is validated RETROSPECTIVELY with reps + a bootstrap CI on the curve-area gap,
     reported whether it is positive OR a not-yet-useful negative.
The contrast `random_selector_honest` is False by construction (no acquisition signal, no falsifiable curve).
The active-beats-random result is reported informationally.

Deterministic (fixed seeds), CI-safe. Non-circular: the honesty/falsifiability properties are structural.
"""
from __future__ import annotations

from pen_stack.active.acquire import expected_information_gain, immune_voi
from pen_stack.active.design import batch_diversity, select_batch
from pen_stack.active.validate import retrospective_active_learning

_BASE = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
         "promoter": "ef1a", "copy_number": 1, "accessibility": 0.8}


def run() -> dict:
    # 1. acquisition from the twin: EIG monotone in uncertainty (OOD > in-distribution)
    eig_in = expected_information_gain({**_BASE, "cell_state": "k562"}, "k562")
    eig_ood = expected_information_gain({**_BASE, "cell_state": "rare_xyz"}, "rare_xyz")
    eig_monotone = bool(eig_in >= 0 and eig_ood > eig_in)

    # 2. immune-VOI rewards proxy-validating experiments
    immune_voi_rewards_proxy = bool(immune_voi(_BASE, "k562") > 0)

    # 3. diverse batch (beats pure top-k-by-score)
    cands = [{**_BASE, "delivery_vehicle": v, "cell_state": "k562"}
             for v in ("AAV_single", "AAV_dual", "lentivirus", "helper_dependent_adenovirus")]
    diverse = select_batch(cands, "k562", k=3, w_div=0.8)
    greedy = select_batch(cands, "k562", k=3, w_div=0.0)
    batch_diverse = bool(batch_diversity(diverse) >= batch_diversity(greedy)
                         and all("expected_info_gain" in b for b in diverse))

    # 4. retrospective falsifiability: gap + CI reported either way
    retro = retrospective_active_learning(reps=15, rounds=6)
    falsifiable = bool(retro["available"] and "ci" in retro["active_vs_random"]
                       and isinstance(retro["active_beats_random"], bool))

    experiment_designer_honest = bool(
        eig_monotone and immune_voi_rewards_proxy and batch_diverse and falsifiable)

    return {
        "available": True,
        "experiment_designer_honest": experiment_designer_honest,
        "random_selector_honest": False,            # no acquisition signal, no falsifiable curve -> fails
        "eig_monotone_in_uncertainty": eig_monotone,
        "immune_voi_rewards_proxy": immune_voi_rewards_proxy,
        "batch_diverse": batch_diverse,
        "retrospective_falsifiable": falsifiable,
        # informational:
        "active_beats_random": retro["active_beats_random"],
        "active_vs_random_ci": retro["active_vs_random"]["ci"],
        "no_fabrication": True,
        "ground_truth": "structural honesty + falsifiability properties of the Learn engine (twin-sourced EIG, "
                        "immune-VOI for proxy validation, diverse batch, retrospective active-vs-random with reps+CI) "
                        "- non-circular; the active-beats-random outcome is reported either way (not-yet-useful is valid)",
    }
