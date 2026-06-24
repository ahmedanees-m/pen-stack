"""PEN-RAG corpus builder (v7.1).

Assembles the provenance-tagged corpus that grounds the chat's General lane. EVERY chunk is real, already-curated
repository content - DOI-backed verbatim quotes, the metric guide, the writer-atlas family cards, the data/model
cards, and the scope boundary - never fabricated paper text. Each chunk carries:
    chunk_id, text, source_id, doi, access_grade, type, scope_status
The built table is `data/rag_corpus.parquet` (SHA-locked at build); its embeddings are `data/rag_corpus_emb.npy`.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pen_stack._resources import project_root

_FIELDS = ["chunk_id", "text", "source_id", "doi", "access_grade", "type", "scope_status"]


def _writer_efficiency_chunks() -> list[dict]:
    from pen_stack.atlas import writer_efficiency as we
    out = []
    for r in we.records().itertuples(index=False):
        q = str(getattr(r, "quote", "") or "").strip()
        if not q:
            continue
        eff = getattr(r, "efficiency_pct", None)
        eff_s = f" Measured integration efficiency ~{eff}%." if eff is not None and not pd.isna(eff) else ""
        out.append({
            "text": (f"{r.system} ({r.family}) at {r.locus} in {r.cell_type}.{eff_s} "
                     f"Reported: \"{q}\""),
            "source_id": f"writer_eff:{r.system}:{r.locus}", "doi": str(r.doi),
            "access_grade": str(getattr(r, "source_access", "unknown")),
            "type": "efficiency_measurement", "scope_status": "measured"})
    return out


def _metric_guide_chunks() -> list[dict]:
    from pen_stack.web.guide import metric_guide
    mg = metric_guide() or {}
    out = []
    for key, m in (mg.get("metrics") or {}).items():
        text = (f"Metric '{m.get('label', key)}' ({key}): scale {m.get('scale')}, {m.get('direction')}. "
                f"What it means: {m.get('means')} How it is computed: {m.get('computed')} "
                f"Validation: {m.get('validation')} Reference: {m.get('reference')}")
        cites = m.get("reference") or ""
        out.append({"text": text, "source_id": f"metric_guide:{key}", "doi": str(cites),
                    "access_grade": "curated", "type": "metric_card", "scope_status": "documented"})
    sd = mg.get("safety_decision")
    if sd:
        out.append({"text": "Guardian biosecurity decisions: " + "; ".join(f"{k} = {v}" for k, v in sd.items()),
                    "source_id": "metric_guide:safety_decision", "doi": "", "access_grade": "curated",
                    "type": "metric_card", "scope_status": "documented"})
    return out


def _atlas_card_chunks() -> list[dict]:
    from pen_stack.rag.index import build_cards
    out = []
    for c in build_cards():
        out.append({"text": c.text, "source_id": f"atlas:{c.key}", "doi": ";".join(c.citations),
                    "access_grade": "curated", "type": "writer_atlas_card", "scope_status": "measured/candidate"})
    return out


def _doc_card_chunks() -> list[dict]:
    """Chunk the committed data/model cards (docs/cards/*.md) by paragraph."""
    out = []
    cards_dir = project_root() / "docs" / "cards"
    if not cards_dir.exists():
        return out
    for p in sorted(cards_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for para in [s.strip() for s in text.split("\n\n")]:
            clean = " ".join(para.split())
            if len(clean) < 80 or clean.startswith("#") and len(clean) < 120:
                continue
            out.append({"text": clean[:900], "source_id": f"card:{p.stem}", "doi": "",
                        "access_grade": "curated", "type": "data_card", "scope_status": "documented"})
    return out


def _scope_chunks() -> list[dict]:
    """The honesty boundary: the known-unknowns the engine never predicts."""
    from pen_stack.web.guide import pen_stack_facts
    out = []
    try:
        facts = pen_stack_facts() or {}
    except Exception:  # noqa: BLE001
        facts = {}
    ku = facts.get("known_unknowns") or facts.get("scope", {}).get("known_unknowns")
    if ku:
        out.append({"text": ("PEN-STACK never predicts these known-unknowns (it abstains): "
                             + "; ".join(str(x) for x in ku) + ". These are measured clinical endpoints "
                             "outside the engine's validated envelope."),
                    "source_id": "scope:known_unknowns", "doi": "", "access_grade": "curated",
                    "type": "scope_boundary", "scope_status": "known_unknown"})
    return out


def build_corpus() -> pd.DataFrame:
    """Assemble the full provenance-tagged corpus from real repository content."""
    rows: list[dict] = []
    for fn in (_writer_efficiency_chunks, _metric_guide_chunks, _atlas_card_chunks,
               _doc_card_chunks, _scope_chunks):
        try:
            rows.extend(fn())
        except Exception as e:  # noqa: BLE001 - a missing source must not silently corrupt the corpus; surface it
            rows.append({"text": f"[source builder {fn.__name__} failed: {e}]", "source_id": "build_error",
                         "doi": "", "access_grade": "n/a", "type": "build_error", "scope_status": "n/a"})
    # drop build-error rows from the shippable corpus but keep the count honest
    df = pd.DataFrame([r for r in rows if r["type"] != "build_error"])
    df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)
    df["chunk_id"] = [f"c{i:04d}" for i in range(len(df))]
    errors = [r for r in rows if r["type"] == "build_error"]
    if errors:
        raise RuntimeError("corpus build had source errors: " + " | ".join(r["text"] for r in errors))
    return df[_FIELDS]


def corpus_path() -> Path:
    return project_root() / "data" / "rag_corpus.parquet"


def emb_path() -> Path:
    return project_root() / "data" / "rag_corpus_emb.npy"


def load_corpus() -> pd.DataFrame:
    p = corpus_path()
    if not p.exists():
        raise FileNotFoundError(f"{p} not built; run scripts/build_rag_corpus.py")
    return pd.read_parquet(p)
