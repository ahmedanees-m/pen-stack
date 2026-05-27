#!/usr/bin/env python3
"""Pre-download ESM-2 650M weights into the Docker layer cache.

Called at image build time via:
    RUN python3 scripts/predownload_esm2.py
"""
from transformers import EsmModel, EsmTokenizer

CACHE = "/root/.cache/esm2"
MODEL_ID = "facebook/esm2_t33_650M_UR50D"

print(f"Downloading {MODEL_ID} to {CACHE} ...")
EsmModel.from_pretrained(MODEL_ID, cache_dir=CACHE)
EsmTokenizer.from_pretrained(MODEL_ID, cache_dir=CACHE)
print("ESM-2 650M pre-downloaded successfully.")
