"""Grounded document index for the PEN-STACK RAG (Phase 2, Step 2.8).

Builds a cited corpus of fact cards from the curated atlas + WT-KB (each card carries its source DOIs),
so retrieval-grounded answers always have a citation. If PaperQA + an LLM are available they can index a
literature corpus on top; the keyword retriever here is the dependency-light default that guarantees the
"every factual claim is cited" contract without any model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

_ATLAS = Path(__file__).resolve().parents[1] / "atlas" / "atlas.parquet"


@dataclass
class Card:
    key: str
    text: str
    citations: list[str] = field(default_factory=list)


def build_cards(atlas_parquet: str | Path = _ATLAS) -> list[Card]:
    """One fact card per writer family, summarising its measured targeting + readiness, with DOIs."""
    df = pd.read_parquet(atlas_parquet)
    cards: list[Card] = []
    for fam, sub in df.groupby("family"):
        core = sub[sub["entry_kind"].isin(["curated_core", "curated_rep"])]
        rep = core.iloc[0] if len(core) else sub.iloc[0]
        dois: list[str] = []
        for d in core["key_dois"] if len(core) else sub["key_dois"]:
            dois.extend(str(x) for x in list(d) if str(x).strip())
        text = (f"Writer family {fam}: representative {rep['representative_system']}; "
                f"mechanism {rep.get('mechanism_bucket')}; targeting {rep.get('targeting_modality')}; "
                f"reachability {rep.get('reachability_tier')}; deliverability {rep.get('deliv_class')}; "
                f"cargo {rep.get('cargo_capacity_bp')} bp; human-cell activity: "
                f"{rep.get('human_cell_activity')}. {len(sub):,} systems catalogued.")
        cards.append(Card(key=fam, text=text, citations=sorted(set(dois))))
    return cards


def retrieve(question: str, cards: list[Card], k: int = 3) -> list[Card]:
    """Keyword overlap retriever (lower-cased token Jaccard). Deterministic, no model needed."""
    q = set(_tok(question))
    scored = [(len(q & set(_tok(c.text + " " + c.key))), c) for c in cards]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for n, c in scored if n > 0][:k]


def _tok(s: str) -> list[str]:
    return [w for w in "".join(ch.lower() if ch.isalnum() else " " for ch in s).split() if len(w) > 2]
