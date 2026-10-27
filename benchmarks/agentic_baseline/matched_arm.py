"""The matched tool-driving arm: the same 40 goals as the ungrounded conditions, with full traces. Two things the published four-goal arm does not do:

  1. it runs on the same goal set as the prompt-only conditions, so the comparison is matched;
  2. it retains the complete prompts, model responses, tool calls and returned values per goal, so
     the grounded arm is replayable on the same footing as the cached prompt-only arms.

The reported endpoint is deliberately three-way rather than a single completion fraction. For a
system whose stated behaviour is to return an explicit known-unknown when a quantity is outside a
tool's scope, collapsing "the tool said unknown" into "the agent under-delivered" would score correct
behaviour as a failure. So each required field lands in exactly one of:

  grounded_value    a tool call produced a value for the field
  grounded_unknown  a tool covering the field was called and returned an abstention or known-unknown
  unaddressed       no tool call covering the field was made

Completion is then reported two ways: fields resolved through a tool (value + unknown), and fields
carrying an actual number (value only). Both are needed to read the fabrication result correctly.

Usage:
    python -I ../work/matched_arm.py --provider anthropic --limit 2 --out ../work/matched_pilot
    python -I ../work/matched_arm.py --provider anthropic --out ../work/matched_claude
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

# The repo must be first on the path: run from the repo root with the script living elsewhere and
# `pen_stack` otherwise resolves to whatever copy is installed or sits on the drive, which during a
# pilot silently scored a stale pre-squash tree instead of the working one.
sys.path.insert(0, os.getcwd())

GOALS_FILE = "benchmarks/grounding_llm_on/adversarial_goals.json"

# Per required field: where a VALUE for it may sit in a tool result, and where that tool records an
# ABSTENTION for that same quantity. Value paths are tried in order, so the exactly-named field wins
# over a derived or combined one: `writability.max_writability` is the writability, whereas
# `plan_write.score` is a combined objective and is a different quantity.
# Abstention must be tied to the specific quantity. A result-wide abstention flag would credit any
# field sourced from that tool as a known-unknown, including quantities the tool never computes.
FIELD_SOURCES = {
    "max_writability": {
        "value": [("writability", ("max_writability",)), ("writability", ("writability",))],
        "abstain": [("writability", ("found",), False)],
    },
    "safety_score": {
        "value": [("writability", ("safety",)), ("plan_write", ("safety",))],
        "abstain": [("writability", ("found",), False)],
    },
    "p_durable": {
        "value": [("writability", ("p_durable",)), ("plan_write", ("durability",)),
                  ("writer_axes", ("durability",))],
        "abstain": [("writability", ("found",), False)],
    },
    "predicted_offtarget_count": {
        "value": [("offtargets", ("n",)), ("offtargets", ("count",)),
                  ("plan_write", ("cargo", "offtargets", "n"))],
        "abstain": [("plan_write", ("cargo", "offtargets", "confidence", "abstain"), True),
                    ("plan_write", ("cargo", "offtargets", "confidence", "epistemic_status"),
                     "not-computable"),
                    ("offtargets", ("confidence", "abstain"), True)],
    },
    "structural_risk_score": {
        "value": [("structural_risk", ("structural_risk_score",)),
                  ("writer_axes", ("structural_risk",))],
        "abstain": [("structural_risk", ("abstain",), True),
                    ("structural_risk", ("epistemic_status",), "not-computable")],
    },
    "target_bin_coordinate": {
        "value": [("plan_write", ("site", "bin")), ("plan_write", ("site", "pos")),
                  ("writability", ("bin",))],
        "abstain": [],
    },
}
REQUIRED = list(FIELD_SOURCES)


def dig(obj, path):
    cur = obj
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def classify_fields(trace):
    """Return {field: (status, provenance)} over the required fields, from the trace alone."""
    out = {}
    called = {}
    for step in trace:
        called.setdefault(step["tool"], []).append(step["result"])

    for field, spec in FIELD_SOURCES.items():
        status, prov = "unaddressed", None
        for tool, path in spec["value"]:
            for res in called.get(tool, []):
                if not isinstance(res, dict) or "error" in res:
                    continue
                v = dig(res, path)
                if v is not None and not isinstance(v, (dict, list)):
                    status, prov = "grounded_value", f"{tool}:{'.'.join(path)}={v}"
                    break
            if status == "grounded_value":
                break
        if status == "unaddressed":
            for tool, path, marker in spec["abstain"]:
                for res in called.get(tool, []):
                    if not isinstance(res, dict) or "error" in res:
                        continue
                    if dig(res, path) == marker:
                        status = "grounded_unknown"
                        prov = f"{tool}:{'.'.join(path)}={marker}"
                        break
                if status != "unaddressed":
                    break
        out[field] = (status, prov)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, help="anthropic | ollama_small | nvidia")
    ap.add_argument("--limit", type=int, default=0, help="run only the first N goals (pilot)")
    ap.add_argument("--out", required=True, help="output directory for per-goal trace files")
    ap.add_argument("--max-steps", type=int, default=12)
    ap.add_argument("--api-base", default=None,
                    help="override the provider's api_base, e.g. a local Ollama on a non-default port. "
                         "Recorded in the summary so the run documents where it reached the model.")
    args = ap.parse_args()

    from pen_stack.agent.orchestrator import run_agent
    from pen_stack.rag.llm import load_llm_config
    from pen_stack.validate.agent_eval import no_fabrication

    cfg = dict(load_llm_config())
    cfg["provider"] = args.provider
    if args.api_base:
        provs = {k: dict(v) for k, v in (cfg.get("providers") or {}).items()}
        provs.setdefault(args.provider, {})["api_base"] = args.api_base
        cfg["providers"] = provs
    model_id = ((cfg.get("providers") or {}).get(args.provider) or {}).get("model")
    api_base = ((cfg.get("providers") or {}).get(args.provider) or {}).get("api_base")

    spec = json.load(open(GOALS_FILE, encoding="utf8"))
    goals = [(g["gene"], g["goal"]) for g in spec["plan_goals"]]
    if args.limit:
        goals = goals[:args.limit]

    os.makedirs(args.out, exist_ok=True)
    rows = []
    for i, (gene, goal) in enumerate(goals, 1):
        t0 = time.time()
        try:
            res = run_agent(goal, max_steps=args.max_steps, cfg=cfg)
            err = None
        except Exception as e:  # noqa: BLE001
            res, err = {"trace": [], "plan": "", "messages": []}, repr(e)
        trace = res.get("trace") or []
        audit = no_fabrication(res) if trace else {"passed": True, "mismatches": [],
                                                  "note": "no tool call, nothing to audit"}
        fields = classify_fields(trace)
        counts = {s: sum(1 for st, _ in fields.values() if st == s)
                  for s in ("grounded_value", "grounded_unknown", "unaddressed")}
        row = {
            "gene": gene, "goal": goal, "provider": args.provider,
            "llm_in_control": bool(res.get("llm")), "n_tool_calls": len(trace),
            "tools_called": sorted({s["tool"] for s in trace}),
            "no_fabrication_pass": bool(audit["passed"]),
            "audit_mismatches": audit.get("mismatches", []),
            "fields": {k: {"status": v[0], "provenance": v[1]} for k, v in fields.items()},
            "field_counts": counts,
            "resolved_through_tool": (counts["grounded_value"] + counts["grounded_unknown"]) / len(REQUIRED),
            "carrying_a_number": counts["grounded_value"] / len(REQUIRED),
            "seconds": round(time.time() - t0, 1),
            "error": err,
        }
        rows.append(row)
        # the full record, including prompts and model responses, one file per goal
        with open(os.path.join(args.out, f"{i:02d}_{gene}.json"), "w", encoding="utf8") as fh:
            json.dump({**row, "messages": res.get("messages"), "plan": res.get("plan"),
                       "trace": trace}, fh, indent=2, default=str)
        print(f"[{i:>2}/{len(goals)}] {gene:<10} calls={len(trace):<3} "
              f"audit={'PASS' if audit['passed'] else 'FAIL'} "
              f"value={counts['grounded_value']} unknown={counts['grounded_unknown']} "
              f"unaddressed={counts['unaddressed']} {row['seconds']}s"
              + (f"  ERROR {err}" if err else ""))
        sys.stdout.flush()

    n = len(rows)
    summary = {
        "provider": args.provider, "model": model_id, "api_base": api_base, "n_goals": n,
        "goals_with_tool_calls": sum(1 for r in rows if r["n_tool_calls"] > 0),
        "no_fabrication_pass_all": all(r["no_fabrication_pass"] for r in rows),
        "n_audit_failures": sum(1 for r in rows if not r["no_fabrication_pass"]),
        "mean_resolved_through_tool": round(sum(r["resolved_through_tool"] for r in rows) / n, 4) if n else None,
        "mean_carrying_a_number": round(sum(r["carrying_a_number"] for r in rows) / n, 4) if n else None,
        "field_totals": {s: sum(r["field_counts"][s] for r in rows)
                         for s in ("grounded_value", "grounded_unknown", "unaddressed")},
        "errors": [r["gene"] for r in rows if r["error"]],
        "rows": rows,
    }
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    print("\n" + json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
