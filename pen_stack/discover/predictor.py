"""Gate-probability predictor trained on ESM-2 embeddings.

5 binary classifiers + 1 TrueWriter probability regressor.
Training data: curated editors from pen-score v0.1.3 with known gate values.

Technical notes:
- ~24 training examples is small; use calibrated logistic regression with L2
  regularization (not neural network). Calibration via Platt scaling (cv=3).
- Feature: 1280-dim ESM-2 embedding
- This is a low-N intentional classifier: scientifically honest about uncertainty.
- Fallback for unknown editors: report highest uncertainty band (confidence < 0.5)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline as SkPipeline
import joblib

GATE_LABELS = ["gate_1_dsb", "gate_2_prog", "gate_3_cargo",
               "gate_4_deliv", "gate_5_evidence"]
MODEL_SAVE_DIR = Path("data/discover_models/")


@dataclass
class DiscoverPrediction:
    editor_id: str
    tw_probability: float          # continuous TrueWriter probability (0-1)
    tw_uncertainty: float          # uncertainty from gate entropy
    predicted_tier: str            # predicted tier
    gate_probabilities: dict       # gate_id -> P(pass)
    gate_predictions: dict         # gate_id -> bool
    low_confidence: bool           # True if tw_uncertainty > 0.25
    recommendation: str            # "characterize" / "deprioritize" / "uncertain"
    note: str


class DiscoverPredictor:
    def __init__(self, model_dir: Path = MODEL_SAVE_DIR):
        self.model_dir = Path(model_dir)
        self.gate_models: dict = {}
        self.tw_model = None
        self._trained = False

    def train(self, embeddings_df: pd.DataFrame, labels_df: pd.DataFrame):
        """Train gate classifiers and TW probability regressor.

        Args:
            embeddings_df: (N, 1280+) DataFrame with ESM-2 features + editor_id
            labels_df: (N, 6+) DataFrame with gate labels + tw_probability per editor
        """
        self.model_dir.mkdir(parents=True, exist_ok=True)

        emb_cols = [c for c in embeddings_df.columns if c.startswith("esm2_")]
        merged = embeddings_df.merge(labels_df, on="editor_id")
        X = merged[emb_cols].values
        n = len(X)

        print(f"Training on {n} editors, {len(emb_cols)} features")

        # CV folds: use min(3, n//3) to avoid too-small folds
        cv = max(2, min(3, n // 3))

        for gate in GATE_LABELS:
            if gate not in merged.columns:
                print(f"  Skipping {gate} (no labels)")
                continue
            y = merged[gate].astype(int).values
            if len(np.unique(y)) < 2:
                print(f"  Skipping {gate} (only one class in labels)")
                continue
            clf = CalibratedClassifierCV(
                LogisticRegression(C=0.1, max_iter=500, random_state=42),
                cv=cv,
                method="sigmoid",
            )
            pipe = SkPipeline([("scaler", StandardScaler()), ("clf", clf)])
            pipe.fit(X, y)
            self.gate_models[gate] = pipe
            save_path = self.model_dir / f"{gate}_model.joblib"
            joblib.dump(pipe, save_path)
            print(f"  {gate}: trained (pos_rate={y.mean():.2f}) -> {save_path}")

        # TrueWriter probability regressor
        if "tw_probability" in merged.columns:
            from sklearn.linear_model import Ridge
            y_tw = merged["tw_probability"].values
            pipe_tw = SkPipeline([("scaler", StandardScaler()),
                                   ("reg", Ridge(alpha=1.0))])
            pipe_tw.fit(X, y_tw)
            self.tw_model = pipe_tw
            joblib.dump(pipe_tw, self.model_dir / "tw_probability_model.joblib")
            print("  TrueWriter probability model: trained")

        self._trained = True

    def load(self):
        """Load pre-trained models from disk."""
        for gate in GATE_LABELS:
            p = self.model_dir / f"{gate}_model.joblib"
            if p.exists():
                self.gate_models[gate] = joblib.load(p)
        tw_path = self.model_dir / "tw_probability_model.joblib"
        if tw_path.exists():
            self.tw_model = joblib.load(tw_path)
        self._trained = bool(self.gate_models)

    def predict(self, esm2_embedding: np.ndarray, editor_id: str = "query") -> DiscoverPrediction:
        """Predict TrueWriter probability + gate values from an ESM-2 embedding."""
        if not self._trained:
            raise RuntimeError("Model not trained. Call .train() or .load() first.")

        X = esm2_embedding.reshape(1, -1)

        gate_probs = {}
        gate_preds = {}
        for gate, model in self.gate_models.items():
            prob = float(model.predict_proba(X)[0][1])  # P(PASS)
            gate_probs[gate] = prob
            gate_preds[gate] = prob >= 0.5

        # TrueWriter probability from direct regressor
        if self.tw_model is not None:
            tw_prob = float(np.clip(self.tw_model.predict(X)[0], 0, 1))
        else:
            tw_prob = _tw_from_gates(gate_probs)

        # Uncertainty from gate entropy
        tw_unc = _estimate_uncertainty(gate_probs)

        # Predicted tier
        g1 = gate_probs.get("gate_1_dsb", 0)
        if g1 < 0.5:
            tier = "NOT_WRITER"
        elif tw_prob >= 0.7:
            tier = "TRUE_WRITER"
        elif tw_prob >= 0.4:
            tier = "PROBABLE_WRITER"
        elif tw_prob >= 0.1:
            tier = "EMERGING_WRITER"
        else:
            tier = "NOT_WRITER"

        low_confidence = tw_unc > 0.25

        if tw_prob >= 0.6 and not low_confidence:
            rec = "characterize"
            note = f"High TrueWriter probability ({tw_prob:.2f}). Priority for experimental validation."
        elif tw_prob <= 0.2:
            rec = "deprioritize"
            note = f"Low TrueWriter probability ({tw_prob:.2f}). Unlikely to be functional writer."
        else:
            rec = "uncertain"
            note = f"Uncertain ({tw_prob:.2f} +/- {tw_unc:.2f}). Could characterize if resources allow."

        return DiscoverPrediction(
            editor_id=editor_id,
            tw_probability=tw_prob,
            tw_uncertainty=tw_unc,
            predicted_tier=tier,
            gate_probabilities=gate_probs,
            gate_predictions=gate_preds,
            low_confidence=low_confidence,
            recommendation=rec,
            note=note,
        )


def _tw_from_gates(gate_probs: dict) -> float:
    g1 = gate_probs.get("gate_1_dsb", 0)
    q_mean = np.mean([gate_probs.get(g, 0)
                       for g in ["gate_2_prog", "gate_3_cargo", "gate_4_deliv", "gate_5_evidence"]])
    return g1 * q_mean


def _estimate_uncertainty(gate_probs: dict) -> float:
    probs = list(gate_probs.values())
    entropies = [-p * np.log2(p + 1e-9) - (1-p) * np.log2(1-p + 1e-9) for p in probs]
    return float(np.mean(entropies))
