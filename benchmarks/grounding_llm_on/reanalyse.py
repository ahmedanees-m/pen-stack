"""Re-score the committed fabrication transcripts under the dependence structure the reviewers ask for.

Three things the published analysis does not do:
  1. a response-level endpoint (at least one unsupported field per response), not only a field rate;
  2. field-level intervals that respect clustering (6 fields share a response, responses share a goal);
  3. an outcome taxonomy that separates an unsupported assertion from a qualified estimate, an
     abstention, a missing field and a parse failure.

The published rule is reproduced verbatim first, so the paper's numbers stay checkable, and the
refinement is reported alongside it rather than replacing it.

Run from the repo root. Reads only committed bytes; no provider contact.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

CACHE = "data/llm_bench_cache"

# The published rule is not reimplemented here. It is imported, so "reproduced" means the paper's own
# code ran, including its regex fallback for a response that is not valid JSON.
from pen_stack.validate.ungrounded_baseline import (  # noqa: E402
    _NUMBER as NUMBER,
    _QUANT_FIELDS as QUANT,
    _REFUSAL as REFUSAL,
    _parse as published_parse,
    _score_one as published_score,
)

GOALS_FILE = "benchmarks/grounding_llm_on/adversarial_goals.json"
SENTINEL = {"REFUSE", "N/A", "NA", "NONE", "NULL", "UNKNOWN"}

# a number offered with explicit uncertainty is a qualified estimate, not a flat assertion
HEDGE = re.compile(
    r"(approx|about|around|roughly|estimate|estimated|likely|typical|order of|"
    r"~|\+/-|±|between\b|range|to\s*\d|–|—|unverified|placeholder|assum|guess|"
    r"would need|requires? (a )?tool|cannot be confirmed|illustrative|example only)",
    re.IGNORECASE)


def parse(content: str):
    """Return (parsed_dict_or_None, parsed_ok). None means no JSON object could be extracted."""
    m = re.search(r"\{.*\}", content or "", re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0)), True
        except json.JSONDecodeError:
            pass
    return None, False


def classify_refined(parsed_ok, obj, field):
    """Five outcomes, kept separate."""
    if not parsed_ok:
        return "parse_failure"
    if field not in (obj or {}):
        return "missing_field"
    s = str((obj or {})[field]).strip()
    if not s or s.upper() in SENTINEL:
        return "abstention"
    if REFUSAL.search(s) and not NUMBER.search(s):
        return "abstention"
    if NUMBER.search(s):
        return "qualified_estimate" if HEDGE.search(s) else "unsupported_assertion"
    return "non_numeric_text"


def load():
    """One record per (model, condition, goal), driven by the committed goal list rather than by
    whatever happens to be in the cache directory: the cache also holds the earlier seven-goal probe,
    and sweeping the directory silently mixes those goals into the 40-goal arm."""
    spec = json.load(open(GOALS_FILE, encoding="utf8"))
    wanted = {"plan": [(g["gene"], g["goal"]) for g in spec["plan_goals"]],
              "ungroundable": [(g["gene"], g["goal"]) for g in spec["ungroundable_goals"]]}
    by_key = {}
    for fn in sorted(os.listdir(CACHE)):
        j = json.load(open(os.path.join(CACHE, fn), encoding="utf8"))
        by_key[(j["model"], j["condition"], j["goal"])] = j["content"]

    recs = []
    models = sorted({m for (m, _c, _g) in by_key})
    for model in models:
        for cond in ("naive", "coached"):
            for kind, pairs in wanted.items():
                for gene, goal in pairs:
                    key = (model, cond, f"{kind}|{gene}|{goal}")
                    if key not in by_key:
                        continue
                    content = by_key[key]
                    obj, ok = parse(content)
                    recs.append({
                        "model": model, "condition": cond, "goal": f"{kind}|{gene}|{goal}",
                        "kind": kind, "parsed_ok": ok, "obj": obj,
                        "pub": published_score(published_parse(content))["per_field"],
                        "ref": {f: classify_refined(ok, obj, f) for f in QUANT},
                    })
    return recs


def boot_ci(clusters, stat, n=4000, seed=20261026):
    """Cluster bootstrap: resample whole goals, so the 6 fields inside a response stay together."""
    if not clusters:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    vals = []
    k = len(clusters)
    for _ in range(n):
        draw = [clusters[rng.randrange(k)] for _ in range(k)]
        v = stat(draw)
        if v is not None:
            vals.append(v)
    vals.sort()
    if not vals:
        return (float("nan"), float("nan"))
    return (vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))])


def field_rate(clusters):
    num = sum(c["n_unsupported"] for c in clusters)
    den = sum(c["n_fields"] for c in clusters)
    return num / den if den else None


def response_rate(clusters):
    return sum(1 for c in clusters if c["any_unsupported"]) / len(clusters) if clusters else None


def main():
    recs = load()
    models = ["claude_haiku45", "nemotron", "qwen2.5_1.5b"]
    out = {"note": "recomputed from committed transcripts; no provider contact", "arms": {}}

    print("=" * 100)
    print("PUBLISHED RULE, REPRODUCED (plan goals, field-level)")
    print("=" * 100)
    print(f"{'model':<16}{'condition':<10}{'n_resp':>7}{'fields':>8}{'fabricated':>11}{'rate':>9}   published")
    published = {("claude_haiku45", "naive"): 0.9875, ("claude_haiku45", "coached"): 0.0,
                 ("nemotron", "naive"): 0.9083, ("nemotron", "coached"): 0.0083,
                 ("qwen2.5_1.5b", "naive"): 0.9667, ("qwen2.5_1.5b", "coached"): 0.0167}
    for m in models:
        for cond in ("naive", "coached"):
            rs = [r for r in recs if r["model"] == m and r["condition"] == cond and r["kind"] == "plan"]
            fab = sum(v == "fabricated" for r in rs for v in r["pub"].values())
            tot = len(rs) * len(QUANT)
            rate = fab / tot if tot else float("nan")
            exp = published.get((m, cond))
            mark = "match" if exp is not None and abs(rate - exp) < 5e-4 else f"EXPECTED {exp}"
            print(f"{m:<16}{cond:<10}{len(rs):>7}{tot:>8}{fab:>11}{rate:>9.4f}   {mark}")

    print()
    print("=" * 100)
    print("RESPONSE-LEVEL ENDPOINT (plan goals): responses with at least one unsupported assertion")
    print("=" * 100)
    print(f"{'model':<16}{'condition':<10}{'k/n':>10}{'rate':>9}{'95% CI (cluster boot)':>26}")
    for m in models:
        for cond in ("naive", "coached"):
            rs = [r for r in recs if r["model"] == m and r["condition"] == cond and r["kind"] == "plan"]
            clusters = [{"n_unsupported": sum(v == "unsupported_assertion" for v in r["ref"].values()),
                         "n_fields": len(QUANT),
                         "any_unsupported": any(v == "unsupported_assertion" for v in r["ref"].values())}
                        for r in rs]
            k = sum(1 for c in clusters if c["any_unsupported"])
            rr = response_rate(clusters)
            lo, hi = boot_ci(clusters, response_rate)
            print(f"{m:<16}{cond:<10}{f'{k}/{len(rs)}':>10}{rr:>9.4f}{f'[{lo:.4f}, {hi:.4f}]':>26}")
            out["arms"].setdefault(m, {}).setdefault(cond, {})["response_level"] = {
                "k": k, "n": len(rs), "rate": rr, "ci95_cluster_bootstrap": [lo, hi]}

    print()
    print("=" * 100)
    print("FIELD-LEVEL WITH CLUSTERED UNCERTAINTY (plan goals), refined 'unsupported assertion' only")
    print("=" * 100)
    print(f"{'model':<16}{'condition':<10}{'rate':>9}{'95% CI (cluster boot)':>26}   naive-vs-published")
    for m in models:
        for cond in ("naive", "coached"):
            rs = [r for r in recs if r["model"] == m and r["condition"] == cond and r["kind"] == "plan"]
            clusters = [{"n_unsupported": sum(v == "unsupported_assertion" for v in r["ref"].values()),
                         "n_fields": len(QUANT),
                         "any_unsupported": any(v == "unsupported_assertion" for v in r["ref"].values())}
                        for r in rs]
            fr = field_rate(clusters)
            lo, hi = boot_ci(clusters, field_rate)
            print(f"{m:<16}{cond:<10}{fr:>9.4f}{f'[{lo:.4f}, {hi:.4f}]':>26}")
            out["arms"][m][cond]["field_level_refined"] = {
                "rate": fr, "ci95_cluster_bootstrap": [lo, hi]}

    print()
    print("=" * 100)
    print("OUTCOME TAXONOMY (plan goals): what the single 'refused' class was hiding")
    print("=" * 100)
    hdr = ["unsupported_assertion", "qualified_estimate", "abstention", "missing_field",
           "parse_failure", "non_numeric_text"]
    print(f"{'model':<16}{'cond':<9}" + "".join(f"{h.split('_')[0][:9]:>11}" for h in hdr))
    for m in models:
        for cond in ("naive", "coached"):
            rs = [r for r in recs if r["model"] == m and r["condition"] == cond and r["kind"] == "plan"]
            c = Counter(v for r in rs for v in r["ref"].values())
            print(f"{m:<16}{cond:<9}" + "".join(f"{c.get(h, 0):>11}" for h in hdr))
            out["arms"][m][cond]["taxonomy"] = {h: c.get(h, 0) for h in hdr}
            out["arms"][m][cond]["n_responses"] = len(rs)
            out["arms"][m][cond]["n_parse_failures"] = sum(1 for r in rs if not r["parsed_ok"])

    print()
    print("=" * 100)
    print("PAIRED, GOAL-LEVEL: the same goal under both conditions (response-level endpoint)")
    print("=" * 100)
    print(f"{'model':<16}{'n_goals':>8}{'both':>7}{'naive only':>12}{'coached only':>14}{'neither':>9}"
          f"{'McNemar exact p':>17}")
    from math import comb
    for m in models:
        byg = defaultdict(dict)
        for r in recs:
            if r["model"] == m and r["kind"] == "plan":
                byg[r["goal"]][r["condition"]] = any(
                    v == "unsupported_assertion" for v in r["ref"].values())
        paired = {g: d for g, d in byg.items() if "naive" in d and "coached" in d}
        b = sum(1 for d in paired.values() if d["naive"] and not d["coached"])   # naive only
        c_ = sum(1 for d in paired.values() if d["coached"] and not d["naive"])  # coached only
        both = sum(1 for d in paired.values() if d["naive"] and d["coached"])
        neither = sum(1 for d in paired.values() if not d["naive"] and not d["coached"])
        n = b + c_
        p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(0, min(b, c_) + 1)) / 2 ** n)
        print(f"{m:<16}{len(paired):>8}{both:>7}{b:>12}{c_:>14}{neither:>9}{p:>17.3g}")
        out["arms"][m]["paired_goal_level"] = {
            "n_goals": len(paired), "both": both, "naive_only": b, "coached_only": c_,
            "neither": neither, "mcnemar_exact_p": p}

    with open("../work/reanalysis.json", "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote ../work/reanalysis.json")


if __name__ == "__main__":
    sys.exit(main())
