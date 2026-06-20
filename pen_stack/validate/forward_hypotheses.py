"""Forward hypotheses + grounded ranking (Phase 3, Step 3.6).

So the paper is not purely retrospective: run the Planner on additional therapeutic goals, register its
top *novel* (site, writer, construct) proposals date-stamped, then triage them with a literature-grounded
pairwise ranking (a Robin-style pattern, made cited + guard-railed). The numeric predictions always come
from the validated models; the LLM only orders *plausibility given the cited literature*.

Graceful: the cited mini-reviews come from the RAG (works without an LLM); pairwise ordering uses the LLM
if reachable, else falls back to the Planner's own score (documented).

Outputs: out/forward_hypotheses.csv, out/hypothesis_reviews/<gene>.txt.
"""
from __future__ import annotations

import datetime as _dt
import itertools
from pathlib import Path

import pandas as pd

from pen_stack.planner.optimize import EditIntent
from pen_stack.planner.pipeline import plan_write

_OUT = Path(__file__).resolve().parents[2] / "out"
_REVIEWS = _OUT / "hypothesis_reviews"

# Forward therapeutic goals (not in the retrospective benchmark panel) - the Planner proposes the site.
FORWARD_GOALS = [
    {"name": "F8_haemophiliaA", "gene": "F8", "intent": EditIntent.HIGH_DURABILITY, "ct": "hepg2", "cargo_bp": 4400},
    {"name": "SERPINA1_AAT", "gene": "SERPINA1", "intent": EditIntent.HIGH_DURABILITY, "ct": "hepg2", "cargo_bp": 1400},
    {"name": "CISH_TIL", "gene": "CISH", "intent": EditIntent.KNOCK_IN_DISRUPT, "ct": "k562", "cargo_bp": 2000},
    {"name": "HBA1_thal", "gene": "HBA1", "intent": EditIntent.REG_EXCISION, "ct": "k562", "cargo_bp": 1000},
]


def register_hypotheses(goals=FORWARD_GOALS, out_csv: str | Path | None = None) -> pd.DataFrame:
    date = _dt.date.today().isoformat()
    rows = []
    for g in goals:
        plans = plan_write(g["gene"], g["intent"], g["cargo_bp"], g["ct"], k=1)
        if not plans:
            continue
        p = plans[0]
        rows.append({
            "name": g["name"], "gene": g["gene"], "intent": p["intent"], "ct": g["ct"],
            "proposed_chrom": p["site"]["chrom"], "proposed_pos": p["site"]["pos"],
            "writer": p["writer"], "safety": p["safety"], "durability": p["durability"],
            "score": p["score"], "delivery": p["delivery"]["delivery"],
            "registered_date": date, "status": "novel_prediction",
        })
    df = pd.DataFrame(rows)
    out = Path(out_csv) if out_csv else _OUT / "forward_hypotheses.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return df


def cited_reviews(hyps: pd.DataFrame) -> dict:
    """One grounded, cited mini-review per hypothesis (from the RAG - numbers stay tool-derived)."""
    from pen_stack.rag.qa import answer
    _REVIEWS.mkdir(parents=True, exist_ok=True)
    reviews = {}
    for _, h in hyps.iterrows():
        q = f"feasibility and precedent for a {h['intent']} write at {h['gene']} using {h['writer']}"
        a = answer(q)
        text = a["answer"] + "\n\nCitations: " + ", ".join(a["citations"])
        (_REVIEWS / f"{h['name']}.txt").write_text(text, encoding="utf-8")
        reviews[h["name"]] = {"review": a["answer"], "citations": a["citations"]}
    return reviews


def grounded_pairwise_rank(hyps: pd.DataFrame, reviews: dict, use_llm: bool = False) -> list[str]:
    """Rank hypotheses by pairwise comparison over the cited reviews (LLM if available, else by score)."""
    names = list(hyps["name"])
    if not use_llm:
        return list(hyps.sort_values("score", ascending=False)["name"])
    from pen_stack.rag.llm import available, phrase
    if not available():
        return list(hyps.sort_values("score", ascending=False)["name"])
    wins = dict.fromkeys(names, 0)
    for a, b in itertools.combinations(names, 2):
        prompt = (f"Two genome-writing hypotheses. A ({a}): {reviews[a]['review'][:300]}. "
                  f"B ({b}): {reviews[b]['review'][:300]}. Which is more feasible given precedent? "
                  f"Answer only 'A' or 'B'.")
        verdict = (phrase(prompt) or "").strip().upper()
        wins[a if verdict.startswith("A") else b] += 1
    return sorted(names, key=lambda n: wins[n], reverse=True)


def run(use_llm: bool = False) -> dict:
    hyps = register_hypotheses()
    reviews = cited_reviews(hyps) if not hyps.empty else {}
    ranking = grounded_pairwise_rank(hyps, reviews, use_llm=use_llm) if not hyps.empty else []
    return {"n": len(hyps), "ranking": ranking,
            "hypotheses": hyps.to_dict("records"), "reviews_dir": str(_REVIEWS)}


if __name__ == "__main__": # pragma: no cover
    import json
    r = run()
    print(json.dumps({"n": r["n"], "ranking": r["ranking"]}, indent=2))
    for h in r["hypotheses"]:
        print(f" {h['name']:18s} {h['gene']:9s} {h['proposed_chrom']}:{h['proposed_pos']:>10,} "
              f"{h['writer']:14s} score={h['score']}")
