"""Triage Europe PMC hits into candidate writer-system rows (Phase 2, Step 2.7).

Grounded extraction: pull candidate fields (family, organism cue, human-cell evidence) from a hit's
title/abstract using documented keyword cues, **always** carrying the source citation (Europe PMC id +
DOI). An optional LLM pass (Ollama/Qwen via litellm) can enrich the abstract extraction, but it never
invents a citation and never auto-edits the atlas — its output is just another candidate for the queue.

The rule-based path is the reliable default (works offline, fully reproducible, satisfies the back-test).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

_CFG = Path(__file__).resolve().parents[2] / "configs" / "monitor_queries.yaml"


def _load_cues(path: str | Path = _CFG) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def classify_family(text: str, cfg: dict) -> tuple[str | None, list[str]]:
    """Best-guess writer family from keyword cues; returns (family, matched_cues)."""
    t = text.lower()
    best, best_hits = None, []
    for fam, cues in cfg.get("family_cues", {}).items():
        hits = [c for c in cues if c in t]
        if len(hits) > len(best_hits):
            best, best_hits = fam, hits
    return best, best_hits


def has_human_cell_evidence(text: str, cfg: dict) -> bool:
    t = text.lower()
    return any(cue in t for cue in cfg.get("human_cell_cues", []))


_ORG_RE = re.compile(r"\b([A-Z][a-z]+ [a-z]{3,})\b")  # coarse "Genus species" cue


def triage_hit(hit: dict, default_family: str | None = None, cfg: dict | None = None) -> dict:
    """Return a candidate row for the curation queue. Always carries a citation; never auto-edits."""
    cfg = cfg or _load_cues()
    title = hit.get("title", "") or ""
    abstract = hit.get("abstractText", "") or ""
    text = f"{title}. {abstract}"
    fam, cues = classify_family(text, cfg)
    org = _ORG_RE.search(abstract)
    return {
        "candidate_family": fam or default_family,
        "matched_cues": ";".join(cues),
        "organism_cue": org.group(1) if org else None,
        "human_cell_evidence": has_human_cell_evidence(text, cfg),
        "title": title[:300],
        "source_id": hit.get("id"),
        "source_db": hit.get("source"),
        "doi": hit.get("doi"),
        "pub_date": hit.get("firstPublicationDate"),
        "confidence": "inferred",       # candidate — stays inferred until a human reviews/measures
        "status": "pending_review",     # NEVER auto-accepted into the atlas
    }
