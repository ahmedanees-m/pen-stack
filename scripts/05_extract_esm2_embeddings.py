"""Extract ESM-2 650M embeddings for all pen-score v0.1.3 curated editors.

Corrections vs execution plan:
- pen_score.data.loader.load_editor_universe() returns list[EditorEntry], no .sequence
- EditorEntry.canonical_accession used to fetch sequence from UniProt REST API
- Editors with placeholder accessions (REQUIRES_STEP7, NO_UNIPROT) are skipped
"""
import sys, time, requests, warnings
warnings.filterwarnings("ignore")
import pandas as pd
import numpy as np
from pathlib import Path

# Add pen-stack to path (for running inside Docker with mounted volume)
sys.path.insert(0, "/workspace/pen-stack")

from pen_stack.discover.embeddings import ESM2Embedder
from pen_score.data.loader import load_editor_universe

OUTPUT_PATH = Path("data/esm2_embeddings.parquet")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

SKIP_ACCESSIONS = {"REQUIRES_STEP7", "NO_UNIPROT", "", None}


def fetch_uniprot_sequence(accession, retries=3):
    """Fetch protein sequence from UniProt REST API."""
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.fasta"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                lines = r.text.strip().split("\n")
                seq = "".join(l for l in lines if not l.startswith(">"))
                return seq if seq else None
            elif r.status_code == 404:
                print(f"  UniProt 404: {accession}")
                return None
        except Exception as e:
            print(f"  Retry {attempt+1} for {accession}: {e}")
            time.sleep(1)
    return None


# Load editor universe
editors = load_editor_universe()  # list[EditorEntry]
print(f"Editor universe: {len(editors)} editors total")

valid = [(e.id, e.canonical_accession) for e in editors
         if e.canonical_accession not in SKIP_ACCESSIONS]
print(f"Editors with UniProt accessions: {len(valid)}")

# Fetch sequences
print("Fetching sequences from UniProt...")
editor_seqs = []
for eid, acc in valid:
    seq = fetch_uniprot_sequence(acc)
    if seq:
        editor_seqs.append({"editor_id": eid, "accession": acc, "sequence": seq,
                             "length_aa": len(seq)})
        print(f"  {eid} ({acc}): {len(seq)} aa")
    else:
        print(f"  {eid} ({acc}): FAILED")
    time.sleep(0.1)

print(f"\nGot sequences for {len(editor_seqs)} editors")

# De-duplicate by accession for embeddings (e.g. PE2/PE5max/TwinPE all use SpCas9 Q99ZW2)
seen_acc = set()
unique_seqs = []
for es in editor_seqs:
    if es["accession"] not in seen_acc:
        seen_acc.add(es["accession"])
        unique_seqs.append(es)

print(f"Unique sequences to embed: {len(unique_seqs)}")

# Extract embeddings
embedder = ESM2Embedder()
emb_cache = {}  # accession -> embedding

for i, es in enumerate(unique_seqs):
    print(f"Embedding {i+1}/{len(unique_seqs)}: {es['editor_id']} ({es['accession']})")
    emb = embedder.embed(es["sequence"])
    emb_cache[es["accession"]] = emb

# Build final DataFrame (one row per editor_id, duplicates share embedding)
rows = []
for es in editor_seqs:
    acc = es["accession"]
    if acc in emb_cache:
        emb = emb_cache[acc]
        row = {"editor_id": es["editor_id"], "accession": acc, "length_aa": es["length_aa"]}
        row.update({f"esm2_{i}": float(v) for i, v in enumerate(emb)})
        rows.append(row)

df = pd.DataFrame(rows)
df.to_parquet(OUTPUT_PATH, index=False)
print(f"\nSaved {len(df)} editor embeddings to {OUTPUT_PATH}")
print(f"Shape: {df.shape}")
print(df[["editor_id", "accession", "length_aa"]].to_string())
