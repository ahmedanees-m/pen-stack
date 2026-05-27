"""ESM-2 650M protein embeddings for PEN-DISCOVER.

Model: facebook/esm2_t33_650M_UR50D (Apache 2.0)
Strategy: mean-pool layers 20-33 (empirically better for functional annotation
than last-layer only; Simon et al. 2024 InterPLM analysis)
"""
from __future__ import annotations
import torch
import numpy as np
from pathlib import Path
from typing import Optional
from transformers import EsmTokenizer, EsmModel

# Model constants
ESM2_MODEL = "facebook/esm2_t33_650M_UR50D"
ESM2_LAYERS = list(range(20, 34))   # layers 20-33 (14 layers out of 33)
ESM2_DIM = 1280                      # hidden dim for 650M model
ESM2_CACHE = Path("/root/.cache/esm2")


class ESM2Embedder:
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = EsmTokenizer.from_pretrained(
            ESM2_MODEL, cache_dir=str(ESM2_CACHE)
        )
        self.model = EsmModel.from_pretrained(
            ESM2_MODEL, cache_dir=str(ESM2_CACHE),
            output_hidden_states=True,
        ).to(self.device)
        self.model.eval()
        print(f"ESM-2 650M loaded on {self.device}")

    @torch.no_grad()
    def embed(self, sequence: str) -> np.ndarray:
        """Return mean-pooled embedding from layers 20-33.

        Input:  amino acid sequence string (max 1022 aa; IS110 editors ~326 aa)
        Output: 1D numpy array of shape (1280,)
        """
        seq = sequence.upper().replace("*", "").replace("X", "A")
        if len(seq) > 1022:
            seq = seq[:1022]

        inputs = self.tokenizer(
            seq, return_tensors="pt", truncation=True, max_length=1024
        ).to(self.device)

        outputs = self.model(**inputs)
        hidden_states = outputs.hidden_states   # tuple of 34 tensors, each (1, L, 1280)

        # Mean-pool specified layers, then mean-pool over sequence length
        layer_embeddings = torch.stack(
            [hidden_states[l] for l in ESM2_LAYERS], dim=0
        )  # (14, 1, L, 1280)
        mean_over_layers = layer_embeddings.mean(0)   # (1, L, 1280)
        mean_over_positions = mean_over_layers.squeeze(0).mean(0)   # (1280,)

        return mean_over_positions.cpu().numpy()

    def embed_batch(self, sequences: list[str], verbose: bool = True) -> np.ndarray:
        """Embed a list of sequences. Returns array of shape (N, 1280)."""
        embeddings = []
        for i, seq in enumerate(sequences):
            if verbose:
                print(f"Embedding {i+1}/{len(sequences)}")
            embeddings.append(self.embed(seq))
        return np.stack(embeddings)
