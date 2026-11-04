"""Detector interface shared by the band-energy baseline and future ML models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class DetectionEvent:
    """A detection measured in seconds from the start of the segment."""

    start_offset_s: float
    end_offset_s: float
    label: str
    species_id: str | None
    confidence: float
    freq_low_hz: float
    freq_high_hz: float
    model_name: str
    model_version: str


class Detector(Protocol):
    model_name: str
    model_version: str

    def detect(
        self,
        samples: np.ndarray,
        sample_rate: float,
        segment_start: datetime | None = None,
    ) -> list[DetectionEvent]:
        """Return zero or more detections inside this segment.

        segment_start is available for models that need absolute time. The
        baseline detector uses offsets only; the pipeline adds segment_start
        when it builds the detections row.
        """
