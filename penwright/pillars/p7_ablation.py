"""Pillar P7 - agent vs raw-LLM ablation: grounding, not prompting, removes fabrication.

The grounded PENWRIGHT agent copies every tool-only numeric field from a validated tool result, so it
fabricates 0.0 of them *by construction*. This pillar contrasts that against the SAME open models run with
NO tools (from `pen_stack.validate.ungrounded_baseline`, replayed OFFLINE from cached transcripts): asked the
identical planning goals, they invent concrete values they cannot possibly know. We render the contrast as a
bar chart + a metrics JSON so the architectural claim is legible at a glance.

Honesty note: the raw models in the cache are open models (qwen2.5_7b, nemotron) - NOT Claude. They are
reported under their real names.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.validate import ungrounded_baseline as _ub

# The tool-only numeric fields scored - a concrete answer for any of these without a tool is fabrication.
_FIELDS = list(_ub._QUANT_FIELDS)


def _raw_rates(models: list[dict]) -> dict[str, dict[str, float]]:
    """Pull each raw model's plan-goal fabrication rate per prompt condition (omit conditions that are absent)."""
    out: dict[str, dict[str, float]] = {}
    for m in models:
        if not m.get("available"):
            continue
        conds: dict[str, float] = {}
        for cond, c in (m.get("by_condition") or {}).items():
            rate = (c.get("plan_goals") or {}).get("fabrication_rate")
            if rate is not None:
                conds[cond] = float(rate)
        if conds:
            out[m["model"]] = conds
    return out


def _plot(out_png: Path, grounded: float, raw: dict[str, dict[str, float]]) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001 - matplotlib optional
        return False

    labels = ["PENWRIGHT\n(grounded)"]
    values = [grounded]
    colors = ["#2e7d32"]  # grounded bar - distinct green
    palette = {"naive": "#c62828", "coached": "#ef6c00"}  # raw bars - warm
    for model, conds in raw.items():
        for cond in ("naive", "coached"):
            if cond in conds:
                labels.append(f"{model}\n({cond})")
                values.append(conds[cond])
                colors.append(palette.get(cond, "#8e24aa"))

    fig, ax = plt.subplots(figsize=(1.6 + 1.15 * len(labels), 4.6))
    bars = ax.bar(range(len(labels)), values, color=colors, width=0.66, edgecolor="white", linewidth=0.8)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Fabrication rate on tool-only fields")
    ax.set_title("Grounding, not prompting, removes fabrication", fontweight="bold", pad=12)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}",
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)
    return True


def run(out_dir: str = "out/penwright") -> dict:
    """Score P7 offline from cached transcripts, render the figure + metrics JSON, return a summary dict."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "p7_ablation.png"
    json_path = out / "p7_ablation.json"

    res = _ub.run(offline=True)
    grounded = float(res["grounded_agent_fabrication_rate"])
    raw = _raw_rates(res["ungrounded_models"])
    n_cached = sum(1 for _ in (_ub._CACHE.glob("*.json"))) if _ub._CACHE.exists() else 0

    figure_ok = _plot(fig_path, grounded, raw)

    naive_rates = [c["naive"] for c in raw.values() if "naive" in c]
    headline = (
        f"With tools the grounded agent fabricates {grounded:.2f} of tool-only fields by construction; "
        f"the same models with no tools fabricate up to {max(naive_rates):.2f} under a naive prompt "
        f"- grounding, not prompting, removes fabrication." if naive_rates else
        f"Grounded agent fabricates {grounded:.2f} of tool-only fields; no raw-model transcripts cached."
    )

    metrics = {
        "pillar": "P7",
        "title": "Agent vs raw-LLM ablation - grounding, not prompting, removes fabrication",
        "grounded_agent_fabrication_rate": grounded,
        "grounded_note": res.get("grounded_note"),
        "raw_fabrication_rates": raw,
        "separates_agents": res.get("separates_agents"),
        "finding": res.get("finding"),
        "headline": headline,
        "figure": str(fig_path),
        "figure_written": figure_ok,
        "provenance": {
            "source": "pen_stack.validate.ungrounded_baseline.run",
            "offline": True,
            "n_cached_transcripts": n_cached,
            "cache_dir": str(_ub._CACHE),
            "raw_models": list(raw.keys()),
            "raw_models_note": ("the raw ungrounded models are OPEN models (qwen2.5_7b, nemotron) run with no "
                                "tools - they are NOT Claude and are reported under their real names."),
            "tool_only_fields_scored": _FIELDS,
            "n_fields_scored": len(_FIELDS),
            "conditions": "naive (no anti-fabrication coaching) and coached (told to refuse), where cached.",
        },
    }
    json_path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")

    return {
        "pillar": "P7",
        "figure": str(fig_path),
        "metrics": str(json_path),
        "grounded_fabrication_rate": grounded,
        "raw_fabrication_rates": raw,
        "headline": headline,
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run(), indent=2, default=str))
