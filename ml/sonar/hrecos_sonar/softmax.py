"""Multinomial logistic regression on synthetic track features.

NumPy only. Balanced class weights. The probabilities are whatever the
linear model emits on this generator. They are not calibrated on river data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hrecos_sonar.features import design_matrix
from sonar_node.contract import SPECIES_IDS
from sonar_node.simulate import SimulatedTrack

CLASSES = SPECIES_IDS
ABSTAIN_PROBABILITY = 0.45


@dataclass
class SoftmaxModel:
    weights: np.ndarray  # (features + bias, n_classes)
    mean: np.ndarray
    scale: np.ndarray
    classes: tuple[str, ...] = CLASSES

    def predict_proba(self, tracks: list[SimulatedTrack]) -> np.ndarray:
        raw = design_matrix(tracks)
        scaled = (raw - self.mean) / self.scale
        biased = np.concatenate([scaled, np.ones((scaled.shape[0], 1))], axis=1)
        return _softmax(biased @ self.weights)

    def predict(self, tracks: list[SimulatedTrack]) -> list[str | None]:
        probabilities = self.predict_proba(tracks)
        labels = []
        for row in probabilities:
            if float(row.max()) < ABSTAIN_PROBABILITY:
                labels.append(None)
            else:
                labels.append(self.classes[int(row.argmax())])
        return labels


def fit_softmax(
    tracks: list[SimulatedTrack],
    steps: int = 400,
    lr: float = 0.4,
    seed: int = 0,
) -> SoftmaxModel:
    if not tracks:
        raise ValueError("no tracks to fit")
    raw = design_matrix(tracks)
    mean = raw.mean(axis=0)
    scale = raw.std(axis=0)
    scale[scale < 1e-8] = 1.0
    scaled = (raw - mean) / scale
    design = np.concatenate([scaled, np.ones((scaled.shape[0], 1))], axis=1)
    index = {name: i for i, name in enumerate(CLASSES)}
    target = np.array([index[track.truth_species] for track in tracks], dtype=np.int64)
    counts = np.bincount(target, minlength=len(CLASSES)).astype(np.float64)
    class_weight = counts.sum() / np.maximum(counts, 1.0)
    sample_weight = class_weight[target]
    sample_weight /= sample_weight.mean()

    rng = np.random.default_rng(seed)
    weights = rng.normal(0.0, 0.01, size=(design.shape[1], len(CLASSES)))
    eye = np.eye(len(CLASSES))
    for _ in range(steps):
        probabilities = _softmax(design @ weights)
        residual = (probabilities - eye[target]) * sample_weight[:, None]
        gradient = design.T @ residual / design.shape[0]
        weights -= lr * gradient
    return SoftmaxModel(weights=weights, mean=mean, scale=scale)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)
