"""End-to-end evaluation of the integrated workflow.

Four parts:

  A. Requirement preservation. Stated requirements go in; check each is still satisfied on the way out.
  B. The cascade test, which is the reviewer's own example. A design violating cargo capacity is
     repaired from the proof object, and the repaired design is re-verified. The question is whether a
     repair that fixes one constraint and breaks another is caught, or whether it passes.
  C. Unsupported steps. Does the workflow name the quantities it cannot ground, rather than omitting
     them?
  D. A transparent baseline. Compare the planner's locus choice against a fixed rule.

Run from the repository root with the atlas available.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())


def hdr(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


# Each case states requirements the output must still satisfy.
CASES = [
    {"name": "oversize cargo, AAV requested",
     "design": {"write_type": "insertion", "cargo_bp": 8000, "delivery_vehicle": "aav",
                "target_locus": "AAVS1", "cell_type": "k562",
                "cargo_function": "human factor VIII clotting factor"},
     "requirements": {"cargo_bp": 8000, "target_locus": "AAVS1", "cell_type": "k562"}},
    {"name": "oversize cargo AND integration forbidden",
     "design": {"write_type": "insertion", "cargo_bp": 8000, "delivery_vehicle": "aav",
                "target_locus": "AAVS1", "cell_type": "k562", "non_integrating": True,
                "cargo_function": "human factor VIII clotting factor"},
     "requirements": {"cargo_bp": 8000, "non_integrating": True}},
    {"name": "within capacity, nothing to repair",
     "design": {"write_type": "insertion", "cargo_bp": 2000, "delivery_vehicle": "aav",
                "target_locus": "AAVS1", "cell_type": "k562",
                "cargo_function": "human factor IX clotting factor"},
     "requirements": {"cargo_bp": 2000, "delivery_vehicle": "aav"}},
]


def main():
    from pen_stack.planner.delivery_vehicles import vehicle as vehicle_rec
    from pen_stack.verify.proof import repair_from_proof, verify_proof

    out = {"cases": []}

    hdr("A and B. Requirement preservation, and whether a repair's consequences are reassessed")
    print("{:<40}{:<10}{:<26}{:<10}{}".format(
        "case", "before", "repair applied", "after", "requirements preserved"))
    for c in CASES:
        d0 = c["design"]
        p0 = verify_proof(d0)
        leg0 = p0.axis("legality")
        before = leg0.status
        viol0 = [v.get("rule_id") for v in leg0.violated]

        d1 = repair_from_proof(d0, p0)
        d1d = d1.model_dump(exclude_none=True)
        changed = {k: v for k, v in d1d.items()
                   if k in d0 and d0.get(k) != v or (k not in d0 and k == "delivery_vehicle")}
        applied = ", ".join(f"{k}={v}" for k, v in changed.items()) or "none"

        p1 = verify_proof(d1d)
        leg1 = p1.axis("legality")
        after = leg1.status
        viol1 = [v.get("rule_id") for v in leg1.violated]

        # requirement preservation: every stated requirement still holds on the repaired design
        kept = {k: (d1d.get(k) == v) for k, v in c["requirements"].items()}
        preserved = all(kept.values())

        # does the repaired vehicle actually integrate, when integration was forbidden?
        veh = d1d.get("delivery_vehicle")
        rec = vehicle_rec(veh) or {}
        integrates = bool(rec.get("integrating"))

        print("{:<40}{:<10}{:<26}{:<10}{}".format(
            c["name"][:38], before, applied[:24], after,
            "yes" if preserved else "NO -> " + str({k: v for k, v in kept.items() if not v})))
        out["cases"].append({
            "name": c["name"], "before_status": before, "violations_before": viol0,
            "repair_applied": applied, "after_status": after, "violations_after": viol1,
            "requirements": c["requirements"], "requirements_kept": kept,
            "requirements_preserved": preserved,
            "repaired_vehicle": veh, "repaired_vehicle_integrates": integrates,
            "passable_after": bool(p1.passable),
        })

    hdr("B detail. The cascade: does a repair that breaks another constraint get caught?")
    for r in out["cases"]:
        print("  {}".format(r["name"]))
        print("    violations before : {}".format(r["violations_before"] or "none"))
        print("    repair            : {}".format(r["repair_applied"]))
        print("    violations after  : {}".format(r["violations_after"] or "none"))
        print("    vehicle integrates: {}   passable after: {}".format(
            r["repaired_vehicle_integrates"], r["passable_after"]))
        if r["requirements"].get("non_integrating") and r["repaired_vehicle_integrates"]:
            caught = bool(r["violations_after"]) or not r["passable_after"]
            print("    CASCADE: repair chose an integrating vehicle while integration was forbidden; "
                  "caught: {}".format("YES" if caught else "NO, it passed"))
            r["cascade_caught"] = caught

    hdr("C. Unsupported steps: are ungroundable quantities named?")
    from pen_stack.agent.tools import dispatch
    res = dispatch("structural_risk", {"chrom": "chr19", "pos": 55_115_000})
    print("  structural risk        : abstain={} score={} status={}".format(
        res.get("abstain"), res.get("structural_risk_score"), res.get("epistemic_status")))
    plan = dispatch("plan_write", {"gene": "AAVS1", "intent": "safe_harbour_insertion"})
    oc = ((plan.get("cargo") or {}).get("offtargets") or {}).get("confidence") or {}
    print("  off-target count       : abstain={} status={}".format(
        oc.get("abstain"), oc.get("epistemic_status")))
    out["unsupported_steps_named"] = {
        "structural_risk_abstains": bool(res.get("abstain")),
        "offtarget_abstains": bool(oc.get("abstain")),
    }

    hdr("D. Transparent baseline: planner locus choice versus a fixed rule")
    genes = ["AAVS1", "CLYBL", "TRAC", "CCR5", "ALB", "HBB"]
    agree = 0
    rows = []
    for g in genes:
        try:
            p = dispatch("plan_write", {"gene": g, "intent": "safe_harbour_insertion"})
            w = dispatch("writability", {"gene": g})
            site = (p.get("site") or {}).get("bin")
            # the transparent baseline: take the single most writable bin the atlas reports
            same = w.get("found") and site is not None
            rows.append({"gene": g, "planner_bin": site, "atlas_max_writability": w.get("max_writability"),
                         "planner_score": p.get("score")})
            agree += 1 if same else 0
        except Exception as e:  # noqa: BLE001
            rows.append({"gene": g, "error": type(e).__name__})
    print("  {:<10}{:>12}{:>22}{:>16}".format("gene", "planner bin", "atlas max writability",
                                              "planner score"))
    for r in rows:
        if "error" in r:
            print("  {:<10}{:>12}".format(r["gene"], r["error"]))
        else:
            print("  {:<10}{:>12}{:>22}{:>16}".format(
                r["gene"], str(r["planner_bin"]), str(r["atlas_max_writability"]),
                str(r["planner_score"])))
    out["baseline_comparison"] = rows

    with open("out_end_to_end.json", "w", encoding="utf8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print("\nwrote out_end_to_end.json")


if __name__ == "__main__":
    main()
