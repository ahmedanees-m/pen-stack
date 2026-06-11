"""Golden path: an external agent integrating PEN-STACK over REST (PEN-STACK v6.1, WS-EXAMPLE).

Shows the three moves that make PEN-STACK dependable for an AI:
  (1) DISCOVER what PEN-STACK refuses to answer (GET /scope) — so the agent never depends on a non-answer;
  (2) SUBMIT a design (POST /verify) — legality + safety + calibrated confidence + immune profile in one call;
  (3) BRANCH on the structured verdict — halt on a safety refusal, revise on illegality, proceed otherwise.

Run a local server first:  uvicorn pen_stack.server.api:app --port 8000   (needs the `server` extra)
Then:                       python examples/external_agent.py
"""
from __future__ import annotations

import json

import requests

BASE = "http://localhost:8000"


def grounded_design_check(design: dict) -> dict:
    scope = requests.get(f"{BASE}/scope", timeout=30).json()              # what PEN-STACK won't answer
    verdict = requests.post(f"{BASE}/verify", json=design, timeout=30).json()

    if verdict.get("safety", {}).get("decision") == "refuse":            # SAFETY branch — halt
        return {"action": "halt", "why": verdict["safety"]["reason"]}
    if verdict.get("legal") is not True:                                 # LEGALITY branch — revise
        return {"action": "revise", "why": verdict.get("summary") or verdict.get("violations")}

    # PROCEED — and surface what is out of scope FOR THIS question (the agent must not depend on it)
    ku_ids = {k["id"] for k in scope["known_unknowns"]}
    flagged = [f for f in verdict.get("scope_flags", []) if (f.get("id") in ku_ids)]
    return {"action": "proceed",
            "confidence": verdict.get("confidence"),
            "immune_profile": verdict.get("immune_profile"),
            "out_of_scope_for_this_question": flagged}


if __name__ == "__main__":
    benign = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19",
              "delivery_vehicle": "AAV_single", "cargo_bp": 3000, "cargo_function": "human factor IX"}
    hazard = {**benign, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}
    for name, d in (("benign FIX", benign), ("hazardous ricin", hazard)):
        print(f"\n# {name}")
        print(json.dumps(grounded_design_check(d), indent=2, default=str))
