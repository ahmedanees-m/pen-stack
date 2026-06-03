"""Human-readable Write Planner report (Phase 3, Step 3.4)."""
from __future__ import annotations


def render_plan(p: dict) -> str:
    s = p["site"]
    lines = [
        f"Write plan for {p['gene']}  (intent: {p['intent']})",
        f"  Site        : {s['chrom']}:{s['pos']:,}  (bin {s['bin']}, on_target={p['on_target']})",
        f"  Writer      : {p['writer']}  [reachability {p['reachability_tier']}]",
        f"  Scores      : safety {p['safety']} | durability {p['durability']} | "
        f"writer-activity {p['writer_activity']} | score {p['score']}",
        f"  Cargo       : payload {p['cargo']['payload_bp']} bp -> assembled {p['cargo']['assembled_bp']} bp "
        f"(size_ok={p['cargo']['size_ok']}, codon-optimised, insulated)",
        f"  Delivery    : {p['delivery']['delivery']}  ({p['delivery']['rationale']})",
    ]
    if "offtargets" in p["cargo"]:
        lines.append(f"  Off-target  : {p['cargo']['offtargets'].get('status', p['cargo']['offtargets'])}")
    lines.append(f"  Note        : {p['disclaimer']}")
    return "\n".join(lines)


def render_plans(plans: list[dict]) -> str:
    if not plans:
        return "No plan found (gene not in the atlas, or no reachable site)."
    return f"\n{'='*72}\n".join(f"[rank {i+1}]\n{render_plan(p)}" for i, p in enumerate(plans))
