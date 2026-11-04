"""Interfaces for a track classifier and a future ARIS-frame model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from sonar_node.simulate import SimulatedTrack


@dataclass(frozen=True)
class Classification:
    species_id: str | None
    confidence: float
    model_name: str
    model_version: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.species_id is None and self.confidence != 0.0:
            raise ValueError("an abstention has confidence 0")


class SonarClassifier(Protocol):
    model_name: str
    model_version: str

    def classify(self, track: SimulatedTrack) -> Classification:
        """Classify one track from its measurements and behavior summary.

        Implementations must not read `truth_species` or `truth_length_cm`.
        """


class FrameClassifier(Protocol):
    """Pluggable model over raw imaging-sonar frames.

    `frames` is a float array shaped (n_frames, height, width), one acoustic
    image per frame, not an RGB photo. No weights are shipped here. A real
    model would return a Classification; the stub raises.
    """

    model_name: str
    model_version: str

    def classify_frames(self, frames: np.ndarray) -> Classification:
        ...
