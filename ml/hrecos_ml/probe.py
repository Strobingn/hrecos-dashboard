"""NumPy linear probe. Weights are an npz file, not a pickle."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


class LinearProbe:
    def __init__(
        self,
        mean: np.ndarray,
        scale: np.ndarray,
        coef: np.ndarray,
        intercept: np.ndarray,
        classes: list[str],
    ) -> None:
        self.mean = np.asarray(mean, dtype=np.float64)
        self.scale = np.asarray(scale, dtype=np.float64)
        self.scale = np.where(self.scale == 0, 1.0, self.scale)
        self.coef = np.asarray(coef, dtype=np.float64)
        self.intercept = np.asarray(intercept, dtype=np.float64)
        self.classes = list(classes)

    @property
    def n_features(self) -> int:
        return int(self.mean.shape[0])

    def logits(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        z = (x - self.mean) / self.scale
        return z @ self.coef.T + self.intercept

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        scores = self.logits(features)
        scores = scores - scores.max(axis=1, keepdims=True)
        exp = np.exp(scores)
        return exp / exp.sum(axis=1, keepdims=True)

    def predict(self, features: np.ndarray) -> list[str]:
        probs = self.predict_proba(features)
        idx = np.argmax(probs, axis=1)
        return [self.classes[int(i)] for i in idx]

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            mean=self.mean.astype(np.float32),
            scale=self.scale.astype(np.float32),
            coef=self.coef.astype(np.float32),
            intercept=self.intercept.astype(np.float32),
            classes=np.asarray(self.classes),
        )

    @classmethod
    def load(cls, path: str | Path) -> "LinearProbe":
        with np.load(path, allow_pickle=False) as data:
            classes = [str(c) for c in data["classes"].tolist()]
            return cls(data["mean"], data["scale"], data["coef"], data["intercept"], classes)


def fit_probe(features: np.ndarray, labels: np.ndarray, seed: int = 0) -> LinearProbe:
    scaler = StandardScaler()
    x = scaler.fit_transform(np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0))
    clf = LogisticRegression(
        C=1.0,
        max_iter=500,
        solver="lbfgs",
        class_weight="balanced",
        random_state=seed,
    )
    clf.fit(x, labels)
    # sklearn orders classes_ lexicographically. Coef rows follow that order.
    return LinearProbe(
        mean=scaler.mean_,
        scale=scaler.scale_,
        coef=clf.coef_,
        intercept=clf.intercept_,
        classes=[str(c) for c in clf.classes_],
    )
