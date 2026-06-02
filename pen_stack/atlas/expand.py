"""Expand the Writer Atlas across families (Phase 2, Step 2.1).

Grow the Phase-0 curated 8-family core into a comprehensive cross-family catalogue: ingest ortholog
sets at scale (the IS110/IS1111 superfamily, CAST, large serine integrases, Cas12a, TnpB/Fanzor) from
UniProt, place every entry on the WT-KB targeting axes by *inheriting* family-level metadata from the
Phase-0 ``wtkb.parquet`` (single source of truth — the classifier/scorer must not re-derive it), and
tag each row with an explicit ``confidence`` (measured / inferred / predicted) and provenance.

Heavy per-ortholog featurisation (ESM embeddings for mechanism classification at scale, Step 2.2) runs
in Docker on the GPU; this module only assembles the *catalogue* metadata (lightweight, network-bound).

Inputs : configs/atlas_families.yaml, pen_stack/atlas/wtkb.parquet, UniProt REST.
Outputs: pen_stack/atlas/atlas.parquet (one row per system), cached TSVs under data/external/atlas/.
"""
from __future__ import annotations

import time
import urllib.parse
import urllib.request
from io import StringIO
from pathlib import Path

import pandas as pd
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_CFG = _ROOT / "configs" / "atlas_families.yaml"
_WTKB = _ROOT / "pen_stack" / "atlas" / "wtkb.parquet"
_CACHE = _ROOT / "data" / "external" / "atlas"
_OUT = _ROOT / "pen_stack" / "atlas" / "atlas.parquet"

_UNIPROT_STREAM = "https://rest.uniprot.org/uniprotkb/stream"

# WT-KB family-level fields every atlas row inherits (so targeting metadata has ONE source).
_INHERIT = [
    "mechanism_bucket", "targeting_modality", "target_site_spec", "guide_architecture",
    "cargo_mechanism", "cargo_capacity_bp", "dsb_free", "reachability_tier",
    "reachability_constraints",
]


def load_config(path: str | Path = _CFG) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def fetch_uniprot(query: str, fields: str, cache: Path, timeout: int = 120,
                  retries: int = 3) -> pd.DataFrame:
    """Stream a UniProt query to TSV (cached). Returns the raw per-accession metadata frame."""
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return pd.read_csv(cache, sep="\t", dtype=str)
    params = {"query": query, "format": "tsv", "fields": fields}
    url = _UNIPROT_STREAM + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                text = r.read().decode("utf-8")
            df = pd.read_csv(StringIO(text), sep="\t", dtype=str)
            cache.write_text(text, encoding="utf-8")
            return df
        except Exception as e:  # noqa: BLE001 — network is best-effort; surfaced after retries
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"UniProt fetch failed for query {query!r}: {last}")


def _orthologs_for_family(fam_key: str, fam: dict, fields: str, wtkb_row: pd.Series,
                          cache_dir: Path) -> pd.DataFrame:
    """One ortholog table for a family, inheriting WT-KB targeting metadata by family."""
    cache = cache_dir / f"{fam_key}.tsv"
    raw = fetch_uniprot(fam["query"], fields, cache)
    cap = int(fam.get("cap", len(raw)))
    raw = raw.head(cap).copy()

    # UniProt TSV column names (from the requested fields)
    acc_col = "Entry"
    org_col = "Organism"
    len_col = "Length"
    df = pd.DataFrame({
        "representative_system": raw.get(acc_col),
        "uniprot": raw.get(acc_col),
        "organism": raw.get(org_col),
        "length_aa": pd.to_numeric(raw.get(len_col), errors="coerce"),
    })
    df["family"] = fam["wtkb_family"]
    df["pfam_signature"] = [list(fam["pfam_signature"])] * len(df)
    df["confidence"] = fam.get("default_confidence", "predicted")
    df["human_cell_activity"] = "not measured (sequence homolog)"
    df["key_dois"] = [[fam["discovery_doi"]]] * len(df)
    df["entry_kind"] = "ortholog"
    # inherit targeting metadata from the WT-KB family row (single source of truth)
    for col in _INHERIT:
        df[col] = wtkb_row.get(col)
    return df


def _curated_rows(cfg: dict, wtkb: pd.DataFrame) -> pd.DataFrame:
    """Named, characterised systems: the 8 WT-KB families themselves + extra reps from config."""
    rows = []
    # (a) the WT-KB curated core — measured/inferred, full targeting spec
    for _, w in wtkb.iterrows():
        rows.append({
            "representative_system": w["representative_system"],
            "uniprot": w.get("uniprot"),
            "organism": None,
            "length_aa": w.get("length_aa"),
            "family": w["family"],
            "pfam_signature": list(w["pfam_signature"]) if w.get("pfam_signature") is not None else [],
            "confidence": w.get("confidence", "measured"),
            "human_cell_activity": w.get("human_cell_activity"),
            "key_dois": list(w["key_dois"]) if w.get("key_dois") is not None else [],
            "entry_kind": "curated_core",
            **{c: w.get(c) for c in _INHERIT},
        })
    # (b) extra curated representatives (named systems w/o a clean single-Pfam query)
    wt_by_fam = wtkb.set_index("family")
    for rep in cfg.get("curated_representatives", []):
        fam = rep["family"]
        wrow = wt_by_fam.loc[fam] if fam in wt_by_fam.index else pd.Series(dtype=object)
        if isinstance(wrow, pd.DataFrame):
            wrow = wrow.iloc[0]
        rows.append({
            "representative_system": rep["representative_system"],
            "uniprot": rep.get("uniprot"),
            "organism": None,
            "length_aa": rep.get("length_aa") or (wrow.get("length_aa") if len(wrow) else None),
            "family": fam,
            "pfam_signature": list(wrow.get("pfam_signature")) if len(wrow) and wrow.get("pfam_signature") is not None else [],
            "confidence": rep.get("confidence", "inferred"),
            "human_cell_activity": rep.get("human_cell_activity"),
            "key_dois": list(rep.get("key_dois", [])),
            "entry_kind": "curated_rep",
            **{c: (wrow.get(c) if len(wrow) else None) for c in _INHERIT},
        })
    return pd.DataFrame(rows)


def confidence_tag(row: pd.Series) -> str:
    """measured (human-cell data) > inferred (characterised, non-human) > predicted (homolog only)."""
    c = row.get("confidence")
    if c in {"measured", "inferred", "predicted"}:
        return c
    hca = (row.get("human_cell_activity") or "").lower()
    if "human cell" in hca and "not measured" not in hca:
        return "measured"
    return "predicted"


def build_atlas(cfg_path: str | Path = _CFG, wtkb_path: str | Path = _WTKB,
                out: str | Path = _OUT, cache_dir: str | Path = _CACHE,
                offline_ok: bool = False) -> pd.DataFrame:
    cfg = load_config(cfg_path)
    fields = cfg["defaults"]["uniprot_fields"]
    wtkb = pd.read_parquet(wtkb_path)
    wt_by_fam = wtkb.drop_duplicates("family").set_index("family")
    cache_dir = Path(cache_dir)

    tables: list[pd.DataFrame] = [_curated_rows(cfg, wtkb)]
    for fam_key, fam in cfg["families"].items():
        wrow = wt_by_fam.loc[fam["wtkb_family"]] if fam["wtkb_family"] in wt_by_fam.index else pd.Series(dtype=object)
        try:
            tables.append(_orthologs_for_family(fam_key, fam, fields, wrow, cache_dir))
        except Exception as e:  # noqa: BLE001
            if offline_ok:
                print(f"[expand] skip {fam_key} (offline_ok): {e}")
                continue
            raise

    atlas = pd.concat(tables, ignore_index=True)
    # named curated rows win over a homolog row for the same accession. Dedup ONLY among rows that
    # carry a UniProt id — rows without one (seekRNA, PASTE, ShCAST, Bxb1, ISPpu10) are all distinct
    # systems and must never collapse together (pandas treats every NaN as equal under drop_duplicates).
    atlas["_pri"] = atlas["entry_kind"].map({"curated_core": 0, "curated_rep": 1, "ortholog": 2})
    has_acc = atlas["uniprot"].notna() & (atlas["uniprot"].astype(str).str.strip() != "")
    with_acc = (atlas[has_acc].sort_values("_pri")
                .drop_duplicates(subset=["uniprot"], keep="first"))
    atlas = pd.concat([with_acc, atlas[~has_acc]], ignore_index=True).drop(columns="_pri")
    atlas["confidence"] = atlas.apply(confidence_tag, axis=1)
    atlas = atlas.reset_index(drop=True)

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    atlas.to_parquet(out, index=False)
    return atlas


if __name__ == "__main__":  # pragma: no cover
    a = build_atlas()
    print(f"atlas rows: {len(a):,}")
    print(a.groupby(["family", "confidence"]).size())
