"""IS110 orthologue screening via UniProt + ESM-2 + DiscoverPredictor.

Note: NCBI Entrez eutils may be unreachable from some institutional networks.
UniProt REST API is used as the primary sequence source — it provides
IS110 family and serine recombinase protein sequences with comparable coverage.
"""
from __future__ import annotations
import time
import requests
from io import StringIO
from pathlib import Path
import pandas as pd
from pen_stack.discover.embeddings import ESM2Embedder
from pen_stack.discover.predictor import DiscoverPredictor

# UniProt queries for IS110/serine recombinase family
UNIPROT_QUERIES = [
    'protein_name:"IS110" AND length:[200 TO 800] AND reviewed:false',
    'protein_name:"transposase IS110" AND length:[200 TO 800]',
    'protein_name:"serine recombinase" AND length:[200 TO 800] AND reviewed:false',
]
UNIPROT_API = "https://rest.uniprot.org/uniprotkb/search"


def fetch_is110_sequences(n_max: int = 500) -> list:
    """Fetch IS110-related protein sequences from UniProt REST API.

    Uses multiple IS110/serine-recombinase queries and de-duplicates by accession.
    """
    from Bio import SeqIO

    all_seqs = {}  # accession -> dict

    for query in UNIPROT_QUERIES:
        fetched = 0
        cursor = None
        while fetched < n_max:
            params = {
                "query": query,
                "format": "fasta",
                "size": min(200, n_max - fetched),
            }
            if cursor:
                params["cursor"] = cursor

            try:
                r = requests.get(UNIPROT_API, params=params, timeout=30)
                if r.status_code != 200 or not r.text.strip():
                    break

                for rec in SeqIO.parse(StringIO(r.text), "fasta"):
                    acc = rec.id.split("|")[1] if "|" in rec.id else rec.id
                    seq = str(rec.seq).upper().replace("X", "").replace("*", "")
                    if 200 <= len(seq) <= 800 and acc not in all_seqs:
                        all_seqs[acc] = {
                            "ncbi_id": acc,
                            "description": rec.description[:100],
                            "sequence": seq,
                            "length_aa": len(seq),
                        }
                    fetched += 1

                # Check for pagination link
                link = r.headers.get("Link", "")
                if 'rel="next"' in link:
                    import re
                    m = re.search(r'cursor=([^&>]+)', link)
                    cursor = m.group(1) if m else None
                else:
                    break

            except Exception as e:
                print(f"  UniProt query error: {e}")
                break

        time.sleep(0.3)
        print(f"  Query: {query[:50]!r}... -> {len(all_seqs)} unique seqs so far")

    sequences = list(all_seqs.values())
    print(f"Total IS110-related sequences from UniProt: {len(sequences)}")
    return sequences[:n_max]


def screen_orthologues(
    sequences: list,
    output_path: Path = Path("data/discover_screen_results.parquet"),
) -> pd.DataFrame:
    """Screen IS110 orthologues for TrueWriter probability."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not sequences:
        print("No sequences to screen. Writing empty results.")
        df = pd.DataFrame(columns=["ncbi_id", "description", "length_aa",
                                    "tw_probability", "tw_uncertainty", "predicted_tier",
                                    "recommendation", "gate_1_prob", "gate_2_prob",
                                    "gate_3_prob", "low_confidence"])
        df.to_parquet(output_path, index=False)
        return df

    embedder = ESM2Embedder()
    predictor = DiscoverPredictor()
    predictor.load()

    results = []
    total = len(sequences)
    for i, s in enumerate(sequences):
        if i % 50 == 0:
            print(f"Screening {i}/{total}...")
        try:
            emb = embedder.embed(s["sequence"])
            pred = predictor.predict(emb, editor_id=s["ncbi_id"])
            results.append({
                "ncbi_id": s["ncbi_id"],
                "description": s["description"],
                "length_aa": s["length_aa"],
                "tw_probability": pred.tw_probability,
                "tw_uncertainty": pred.tw_uncertainty,
                "predicted_tier": pred.predicted_tier,
                "recommendation": pred.recommendation,
                "gate_1_prob": pred.gate_probabilities.get("gate_1_dsb", 0),
                "gate_2_prob": pred.gate_probabilities.get("gate_2_prog", 0),
                "gate_3_prob": pred.gate_probabilities.get("gate_3_cargo", 0),
                "low_confidence": pred.low_confidence,
            })
        except Exception as e:
            pass  # Skip sequences that fail embedding

    df = pd.DataFrame(results).sort_values("tw_probability", ascending=False)
    df.to_parquet(output_path, index=False)
    print(f"Screened {len(df)} sequences -> {output_path}")
    characterize = df[df.recommendation == "characterize"]
    print(f"Candidates for characterization: {len(characterize)}")
    if len(characterize) > 0:
        print(characterize[["ncbi_id", "tw_probability", "predicted_tier"]].head(10).to_string())
    return df
