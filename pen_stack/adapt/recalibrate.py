"""WS-F2(a) - isotonic recalibration of a released score on user labels (private, in-container).

Isotonic regression learns a monotonic map released_score -> calibrated probability. Being monotonic it
NEVER changes the ranking (AUROC is preserved); it only fixes calibration (Brier / ECE). Small and robust on
the small datasets users typically have. The calibrator is saved as plain JSON under models/local_<id>/ -
the released model is untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class IsotonicCalibrator:
    """Thin, serializable wrapper around sklearn's IsotonicRegression (saved as JSON, no pickle)."""

    def __init__(self):
        self._iso = None
        self.fitted = False

    def fit(self, scores, labels) -> "IsotonicCalibrator":
        from sklearn.isotonic import IsotonicRegression
        s, y = np.asarray(scores, float), np.asarray(labels, float)
        self._iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self._iso.fit(s, y)
        self.fitted = True
        return self

    def transform(self, scores):
        if not self.fitted:
            raise RuntimeError("calibrator not fitted")
        return self._iso.predict(np.asarray(scores, float))

    def to_dict(self) -> dict:
        return {"kind": "isotonic", "x": list(map(float, self._iso.X_thresholds_)),
                "y": list(map(float, self._iso.y_thresholds_))}

    def save(self, path: str | Path) -> Path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return Path(path)

    @classmethod
    def load(cls, path: str | Path) -> "IsotonicCalibrator":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        obj = cls()
        from sklearn.isotonic import IsotonicRegression
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(np.asarray(d["x"], float), np.asarray(d["y"], float)) # re-fit on the stored knots
        obj._iso, obj.fitted = iso, True
        return obj


def recalibrate(scores, labels) -> IsotonicCalibrator:
    """Fit an isotonic calibrator mapping a released score to a calibrated probability on user labels."""
    return IsotonicCalibrator().fit(scores, labels)
