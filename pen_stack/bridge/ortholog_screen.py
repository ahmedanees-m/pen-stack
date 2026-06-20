"""72-system bridge-recombinase ortholog characterisation (Phase 1.5, Step 1.5.4 secondary).

EXPLORATORY, descriptive only. The Perry 2025 Table S1 lists 72 bridge-recombinase orthologs with their
recombinase sequence, bRNA, donor and target, but it does NOT include a per-system human-cell activity
value, so a supervised ortholog-activity *predictor* cannot be trained from the public tables. Instead we
provide a descriptive characterisation: sequence-feature summaries and a similarity ranking to the
one experimentally-validated standout (ISCro4). This is a *feature* (a way to organise the 72 systems),
not a method, and must not be read as an activity prediction.

N = 72 (small). Do not lean on this; it is a secondary, exploratory result with an explicit caveat.
"""
from __future__ import annotations

from collections import Counter

import pandas as pd

_AA = "ACDEFGHIKLMNPQRSTVWY"


def _kmer_vec(seq: str, k: int = 2) -> Counter:
    seq = "".join(c for c in str(seq).upper() if c in _AA)
    return Counter(seq[i:i + k] for i in range(len(seq) - k + 1))


def _cosine(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    return float(dot / (na * nb)) if na and nb else 0.0


def characterise(reference: str = "ISCro4") -> pd.DataFrame:
    """Describe the 72 orthologs: length + 2-mer cosine similarity to the reference (ISCro4). Empty if S1 absent."""
    from pen_stack.bridge.ingest import load_screen
    s1 = load_screen()
    if s1.empty:
        return pd.DataFrame()
    s1 = s1.dropna(subset=["Recombinase_Sequence"]).copy()
    s1["length_aa"] = s1["Recombinase_Sequence"].str.len()
    ref_rows = s1[s1["Name"].astype(str) == reference]
    if ref_rows.empty:
        return s1[["Name", "length_aa"]].assign(similarity_to_ref=float("nan"), reference=reference)
    ref_vec = _kmer_vec(ref_rows.iloc[0]["Recombinase_Sequence"])
    s1["similarity_to_ref"] = s1["Recombinase_Sequence"].apply(lambda x: _cosine(_kmer_vec(x), ref_vec))
    s1["reference"] = reference
    return (s1[["Name", "length_aa", "similarity_to_ref", "reference"]]
            .sort_values("similarity_to_ref", ascending=False).reset_index(drop=True))


def summary(reference: str = "ISCro4") -> dict:
    df = characterise(reference)
    if df.empty:
        return {"available": False, "note": "Perry 2025 Table S1 not present"}
    return {
        "available": True,
        "exploratory": True,
        "n_systems": int(len(df)),
        "reference": reference,
        "length_range_aa": [int(df["length_aa"].min()), int(df["length_aa"].max())],
        "median_length_aa": int(df["length_aa"].median()),
        "most_similar_to_ref": df[df["Name"].astype(str) != reference].head(5)[
            ["Name", "similarity_to_ref"]].round(3).to_dict("records"),
        "caveat": "DESCRIPTIVE ONLY. Table S1 has no per-system activity label, so this is NOT an activity "
                  "predictor; it is a sequence-similarity organisation of the 72 systems relative to the one "
                  "validated standout (ISCro4). N=72 (small). Do not interpret similarity as predicted activity.",
    }


if __name__ == "__main__": # pragma: no cover
    import json
    print(json.dumps(summary(), indent=2, default=str))
