"""PEN-DISCOVER: Sequence-to-TrueWriter prediction for uncharacterized IS110 orthologues."""
from pen_stack.discover.embeddings import ESM2Embedder
from pen_stack.discover.predictor import DiscoverPredictor, DiscoverPrediction
from pen_stack.discover.screen import screen_orthologues, fetch_is110_sequences

__all__ = ["ESM2Embedder", "DiscoverPredictor", "DiscoverPrediction",
           "screen_orthologues", "fetch_is110_sequences", "predict_from_fasta"]


def predict_from_fasta(fasta_path: str) -> DiscoverPrediction:
    """One-call API: FASTA file -> TrueWriter prediction.

    Args:
        fasta_path: path to FASTA file with a single IS110 protein sequence

    Returns:
        DiscoverPrediction with tw_probability, predicted_tier, recommendation
    """
    from Bio import SeqIO
    record = next(SeqIO.parse(fasta_path, "fasta"))
    embedder = ESM2Embedder()
    predictor = DiscoverPredictor()
    predictor.load()
    emb = embedder.embed(str(record.seq))
    return predictor.predict(emb, editor_id=record.id)
