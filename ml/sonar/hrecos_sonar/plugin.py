"""Entrypoint for the sonar node: classifier.name ml.

Loads the weights written by scripts/evaluate.py. Those weights were fit on
synthetic tracks only.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from sonar_node.classify.base import Classification
from sonar_node.classify.frames import require_frame_stack
from sonar_node.simulate import SimulatedTrack

from hrecos_sonar.softmax import ABSTAIN_PROBABILITY, SoftmaxModel

WEIGHTS = Path(__file__).resolve().parents[1] / "artifacts" / "softmax_weights.npz"
MODEL_NAME = "synthetic_softmax"
MODEL_VERSION = "0.1.0"


class SyntheticSoftmaxClassifier:
    model_name = MODEL_NAME
    model_version = MODEL_VERSION

    def __init__(self, path: Path | None = None):
        weight_path = Path(path) if path else WEIGHTS
        if not weight_path.is_file():
            raise FileNotFoundError(
                f"missing {weight_path}. Run ml/sonar/scripts/evaluate.py to fit "
                "the synthetic softmax. It is not a field model."
            )
        blob = np.load(weight_path)
        classes = tuple(str(item) for item in blob["classes"].tolist())
        self.model = SoftmaxModel(
            weights=blob["weights"],
            mean=blob["mean"],
            scale=blob["scale"],
            classes=classes,
        )

    def classify(self, track: SimulatedTrack) -> Classification:
        probabilities = self.model.predict_proba([track])[0]
        best = int(probabilities.argmax())
        confidence = float(probabilities[best])
        if confidence < ABSTAIN_PROBABILITY:
            species = None
            confidence = 0.0
        else:
            species = self.model.classes[best]
        return Classification(
            species_id=species,
            confidence=confidence,
            model_name=self.model_name,
            model_version=self.model_version,
        )

    def classify_frames(self, frames) -> Classification:
        require_frame_stack(frames)
        raise NotImplementedError(
            "synthetic_softmax was fit on track summaries, not on ARIS frames. "
            "A frame model should implement classify_frames((n_frames, height, width))."
        )


def build_classifier() -> SyntheticSoftmaxClassifier:
    return SyntheticSoftmaxClassifier()
