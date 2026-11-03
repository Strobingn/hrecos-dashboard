"""Build the exact JSON rows the Supabase tables expect."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from hydrophone_node.audio.features import analyze
from hydrophone_node.audio.segment import AudioSegment
from hydrophone_node.audio.wavio import write_wav_bytes
from hydrophone_node.config import AppConfig
from hydrophone_node.contract import (
    BAND_LEVEL_KEYS,
    DETECTION_COLUMNS,
    DETECTION_LABELS,
    NODE_COLUMNS,
    REVIEW_STATUS_DEFAULT,
    SEGMENT_COLUMNS,
)
from hydrophone_node.detect.base import DetectionEvent, Detector


def isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def node_row(config: AppConfig, when: datetime | None = None) -> dict:
    row = {
        "id": config.node.id,
        "name": config.node.name,
        "lat": config.node.lat,
        "lon": config.node.lon,
        "river_mile": config.node.river_mile,
        "hardware": config.node.hardware,
        "sample_rate_hz": int(config.node.sample_rate_hz),
        "status": config.node.status,
        "last_heartbeat": isoformat(when or datetime.now(timezone.utc)),
    }
    _require_keys(row, NODE_COLUMNS)
    return row


def _require_keys(row: dict, columns: tuple[str, ...]) -> None:
    if tuple(row.keys()) != columns:
        raise RuntimeError(f"row keys {tuple(row.keys())} do not match {columns}")


def _clip(samples, sample_rate: int, start_s: float, end_s: float, pad_s: float):
    import numpy as np

    start = max(0, int(round((start_s - pad_s) * sample_rate)))
    end = min(samples.size, int(round((end_s + pad_s) * sample_rate)))
    if end <= start:
        return np.zeros(0, dtype=np.float32)
    return samples[start:end]


def build_segment_product(
    segment: AudioSegment,
    config: AppConfig,
    detector: Detector,
) -> dict:
    """Return segment row, segment wav, and detection (row, wav) pairs."""
    features = analyze(
        segment.samples, segment.sample_rate, config.calibration_offset_db
    )
    band_levels = features["band_levels"]
    if tuple(band_levels.keys()) != BAND_LEVEL_KEYS:
        raise RuntimeError("band_levels keys drifted from the contract")

    segment_id = str(uuid.uuid4())
    stamp = segment.start_time.astimezone(timezone.utc)
    storage_path = f"{config.node.id}/{stamp:%Y/%m/%d}/{segment_id}.wav"
    segment_row = {
        "id": segment_id,
        "node_id": config.node.id,
        "start_time": isoformat(segment.start_time),
        "end_time": isoformat(segment.end_time),
        "storage_path": storage_path,
        "rms_db": features["rms_db"],
        "band_levels": band_levels,
    }
    _require_keys(segment_row, SEGMENT_COLUMNS)

    events = detector.detect(segment.samples, segment.sample_rate, segment.start_time)
    detections: list[dict] = []
    for event in events:
        _validate_event(event)
        detection_id = str(uuid.uuid4())
        clip_path = f"{config.node.id}/clips/{detection_id}.wav"
        start = segment.start_time + timedelta(seconds=event.start_offset_s)
        end = segment.start_time + timedelta(seconds=event.end_offset_s)
        row = {
            "id": detection_id,
            "node_id": config.node.id,
            "segment_id": segment_id,
            "start_time": isoformat(start),
            "end_time": isoformat(end),
            "label": event.label,
            "species_id": event.species_id,
            "confidence": round(float(event.confidence), 4),
            "model_name": event.model_name,
            "model_version": event.model_version,
            "freq_low_hz": event.freq_low_hz,
            "freq_high_hz": event.freq_high_hz,
            "clip_path": clip_path,
            "review_status": REVIEW_STATUS_DEFAULT,
        }
        _require_keys(row, DETECTION_COLUMNS)
        if not 0.0 <= row["confidence"] <= 1.0:
            raise RuntimeError(f"confidence out of range: {row['confidence']}")
        clip = _clip(
            segment.samples,
            segment.sample_rate,
            event.start_offset_s,
            event.end_offset_s,
            config.clip_pad_s,
        )
        detections.append(
            {"row": row, "wav": write_wav_bytes(clip, segment.sample_rate)}
        )

    return {
        "segment": segment_row,
        "wav": write_wav_bytes(segment.samples, segment.sample_rate),
        "detections": detections,
    }


def _validate_event(event: DetectionEvent) -> None:
    if event.label not in DETECTION_LABELS:
        raise ValueError(f"label {event.label!r} is not in the detections contract")
    if event.end_offset_s < event.start_offset_s:
        raise ValueError("detection end is before start")
