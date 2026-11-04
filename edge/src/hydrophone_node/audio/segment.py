"""Cut a continuous mono stream into fixed-length segments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

import numpy as np


@dataclass(frozen=True)
class AudioSegment:
    start_time: datetime
    end_time: datetime
    samples: np.ndarray
    sample_rate: int

    @property
    def duration_s(self) -> float:
        return float(self.samples.size) / float(self.sample_rate)


def iter_segments(
    chunks: Iterator[np.ndarray],
    sample_rate: int,
    segment_seconds: float,
    origin: datetime,
) -> Iterator[AudioSegment]:
    """Yield contiguous segments. A trailing partial segment is dropped.

    Acoustic time advances with the sample clock, independent of replay speed.
    """
    if segment_seconds <= 0:
        raise ValueError("segment_seconds must be positive")
    if origin.tzinfo is None:
        origin = origin.replace(tzinfo=timezone.utc)
    else:
        origin = origin.astimezone(timezone.utc)

    segment_samples = int(round(segment_seconds * sample_rate))
    if segment_samples < 1:
        raise ValueError("segment is shorter than one sample")

    buffer = np.zeros(0, dtype=np.float32)
    emitted = 0
    for chunk in chunks:
        chunk = np.asarray(chunk, dtype=np.float32).reshape(-1)
        if chunk.size == 0:
            continue
        buffer = np.concatenate([buffer, chunk])
        while buffer.size >= segment_samples:
            samples = buffer[:segment_samples].copy()
            buffer = buffer[segment_samples:]
            start = origin + timedelta(seconds=emitted / sample_rate)
            emitted += segment_samples
            end = origin + timedelta(seconds=emitted / sample_rate)
            yield AudioSegment(start, end, samples, sample_rate)
