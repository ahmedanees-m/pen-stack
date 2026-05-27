import sys
sys.path.insert(0, "/workspace/pen-stack")
from pen_stack.discover.screen import fetch_is110_sequences, screen_orthologues
seqs = fetch_is110_sequences(n_max=500)
print("Fetched", len(seqs), "sequences")
if seqs:
    df = screen_orthologues(seqs, output_path="data/discover_screen_results.parquet")
    print("Total screened:", len(df))
    char_count = (df.recommendation=="characterize").sum()
    print("Characterize candidates:", char_count)
    print(df[["ncbi_id","tw_probability","predicted_tier"]].head(10).to_string())
else:
    print("No sequences fetched - check connectivity")
