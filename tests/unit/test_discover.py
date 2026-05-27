"""PEN-DISCOVER unit tests."""
import numpy as np
import pytest
from pen_stack.discover.predictor import DiscoverPredictor, _tw_from_gates, _estimate_uncertainty


def test_tw_from_gates_all_pass():
    probs = {"gate_1_dsb": 1.0, "gate_2_prog": 1.0,
             "gate_3_cargo": 1.0, "gate_4_deliv": 1.0, "gate_5_evidence": 1.0}
    assert _tw_from_gates(probs) == pytest.approx(1.0)


def test_tw_from_gates_g1_fail():
    probs = {"gate_1_dsb": 0.0, "gate_2_prog": 1.0,
             "gate_3_cargo": 1.0, "gate_4_deliv": 1.0, "gate_5_evidence": 1.0}
    assert _tw_from_gates(probs) == pytest.approx(0.0)   # G1 fail -> zero


def test_tw_from_gates_partial():
    probs = {"gate_1_dsb": 1.0, "gate_2_prog": 0.5,
             "gate_3_cargo": 0.5, "gate_4_deliv": 0.5, "gate_5_evidence": 0.5}
    result = _tw_from_gates(probs)
    assert 0.0 < result < 1.0


def test_estimate_uncertainty_low():
    # All gates near 1.0 -> low uncertainty
    probs = {"gate_1_dsb": 0.99, "gate_2_prog": 0.98,
             "gate_3_cargo": 0.97, "gate_4_deliv": 0.99, "gate_5_evidence": 0.98}
    unc = _estimate_uncertainty(probs)
    assert unc < 0.2


def test_estimate_uncertainty_high():
    # All gates near 0.5 -> high uncertainty
    probs = {"gate_1_dsb": 0.5, "gate_2_prog": 0.5,
             "gate_3_cargo": 0.5, "gate_4_deliv": 0.5, "gate_5_evidence": 0.5}
    unc = _estimate_uncertainty(probs)
    assert unc > 0.8  # Max entropy is 1.0 at p=0.5


def test_predictor_smoke_no_model():
    """Predictor raises RuntimeError if not trained."""
    predictor = DiscoverPredictor(model_dir="/tmp/nonexistent_discover_models")
    with pytest.raises(RuntimeError, match="not trained"):
        predictor.predict(np.zeros(1280), editor_id="test")


def test_predictor_smoke_with_fake_model(tmp_path):
    """Predictor trains and predicts on tiny fake data."""
    import pandas as pd
    np.random.seed(42)
    n = 10
    emb_cols = {f"esm2_{i}": np.random.randn(n) for i in range(10)}
    emb_df = pd.DataFrame({"editor_id": [f"e{i}" for i in range(n)], **emb_cols})
    labels_df = pd.DataFrame({
        "editor_id": [f"e{i}" for i in range(n)],
        "gate_1_dsb": [1]*5 + [0]*5,
        "gate_2_prog": [1]*4 + [0]*6,
        "gate_3_cargo": [1]*6 + [0]*4,
        "gate_4_deliv": [1]*3 + [0]*7,
        "gate_5_evidence": [1]*5 + [0]*5,
        "tw_probability": [0.9, 0.8, 0.7, 0.6, 0.5, 0.1, 0.1, 0.1, 0.0, 0.0],
    })

    predictor = DiscoverPredictor(model_dir=tmp_path / "models")
    predictor.train(emb_df, labels_df)
    assert predictor._trained

    fake_emb = np.random.randn(10)
    pred = predictor.predict(fake_emb, editor_id="query")
    assert 0.0 <= pred.tw_probability <= 1.0
    assert pred.predicted_tier in ["TRUE_WRITER", "PROBABLE_WRITER",
                                    "EMERGING_WRITER", "NOT_WRITER"]
    assert pred.recommendation in ["characterize", "deprioritize", "uncertain"]
    assert isinstance(pred.gate_probabilities, dict)
    assert isinstance(pred.gate_predictions, dict)
    assert isinstance(pred.low_confidence, bool)
