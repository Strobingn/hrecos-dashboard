"""Edge-facing detector.

``detect(audio, sample_rate)`` returns a list of detections::

    {
        "start_time": float,       # seconds from the start of ``audio``
        "end_time": float,
        "label": str,              # sturgeon_thunder | drum_knock | toadfish_boatwhistle
                                   # | bass_spawning_splash | boat | unknown
        "species_id": str | None,  # public.species.id, or None for boat / unknown
        "confidence": float,
        "freq_low_hz": float,
        "freq_high_hz": float,
        "model_name": str,
        "model_version": str,
    }

``model_name`` and ``model_version`` match the artifact metadata. Times are
seconds from the start of ``audio``. :func:`to_detection_rows` turns that list
into ``public.detections`` objects (absolute timestamps, ``node_id``, species
slug) that validate against ``contracts/detections.schema.json``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from hrecos_ml.audio import iter_windows, resample
from hrecos_ml.hum import impulsive_sturgeon_band, steady_mains_hum
from hrecos_ml.temporal import drop_boat_outside_wash, gate_splash_labels
from hrecos_ml.embeddings import ConcatEmbedder, LowBandEmbedder, PerchOnnxEmbedder
from hrecos_ml.frequency import energy_percentiles
from hrecos_ml.labels import (
    DEFAULT_HOP_S,
    DEFAULT_THRESHOLD,
    EMITTED_TRAIN_LABELS,
    INFERENCE_LABEL,
    MODEL_NAME,
    MODEL_VERSION,
    SPECIES,
    TARGET_SR,
)
from hrecos_ml.probe import LinearProbe

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = _PACKAGE_ROOT / "artifacts" / MODEL_NAME / MODEL_VERSION
DEFAULT_PERCH_PATH = _PACKAGE_ROOT / "data" / "models" / "perch_v2_backbone.onnx"

_DETECTORS: dict[str, "FishDetector"] = {}


class FishDetector:
    def __init__(self, probe: LinearProbe, embedder, metadata: dict) -> None:
        self.probe = probe
        self.embedder = embedder
        self.metadata = metadata
        self.model_name = str(metadata.get("model_name", MODEL_NAME))
        self.model_version = str(metadata.get("model_version", MODEL_VERSION))
        self.threshold = float(metadata.get("threshold", DEFAULT_THRESHOLD))
        self.embedder_name = str(metadata.get("embedder", getattr(embedder, "name", "")))

    def detect(
        self,
        audio: np.ndarray,
        sample_rate: int,
        threshold: float | None = None,
        hop_s: float = DEFAULT_HOP_S,
        temporal_gate: bool = True,
    ) -> list[dict]:
        threshold = self.threshold if threshold is None else float(threshold)
        # One resampled buffer feeds both the windows and the splash gate,
        # so envelope times and event times share the same clock.
        y = resample(audio, sample_rate, TARGET_SR)
        # Drop windows that contain less than 0.5 s of real audio. Those are
        # the zero-padded tail of a file, not a separate event. A short buffer
        # still keeps its first window.
        windows = [
            item
            for item in iter_windows(y, TARGET_SR, hop_s=hop_s)
            if (item[1] - item[0]) >= 0.5 or item[0] == 0.0
        ]
        if not windows:
            return []
        batch = np.stack([chunk for _, _, chunk in windows], axis=0)
        features = self.embedder.embed(batch)
        if features.shape[1] != self.probe.n_features:
            raise ValueError(
                f"embedder produced {features.shape[1]} features, probe expects {self.probe.n_features}. "
                "The embedder in metadata does not match this probe."
            )
        probs = self.probe.predict_proba(features)
        raw_events = []
        for (start_s, end_s, chunk), row in zip(windows, probs):
            freq_low, freq_high = energy_percentiles(chunk, TARGET_SR)
            is_hum, line_share = steady_mains_hum(chunk, TARGET_SR)
            if is_hum and line_share >= threshold:
                raw_events.append(
                    _event(
                        start_s,
                        end_s,
                        "unknown",
                        None,
                        float(line_share),
                        freq_low,
                        freq_high,
                        self.model_name,
                        self.model_version,
                    )
                )
                continue
            winner = int(np.argmax(row))
            train_label = self.probe.classes[winner]
            confidence = float(row[winner])
            if train_label not in EMITTED_TRAIN_LABELS:
                continue
            if confidence < threshold:
                continue
            label = INFERENCE_LABEL[train_label]
            if label == "sturgeon_thunder" and not impulsive_sturgeon_band(chunk, TARGET_SR):
                continue
            species = SPECIES.get(label, SPECIES["unknown"])
            raw_events.append(
                _event(
                    start_s,
                    end_s,
                    label,
                    species.get("species_id"),
                    confidence,
                    freq_low,
                    freq_high,
                    self.model_name,
                    self.model_version,
                )
            )
        if temporal_gate:
            raw_events = gate_splash_labels(raw_events, y, TARGET_SR)
            raw_events = drop_boat_outside_wash(raw_events, y, TARGET_SR)
        return _merge(raw_events, hop_s)


def _event(
    start_s: float,
    end_s: float,
    label: str,
    species_id: str | None,
    confidence: float,
    freq_low: float,
    freq_high: float,
    model_name: str,
    model_version: str,
) -> dict:
    return {
        "start_time": float(start_s),
        "end_time": float(end_s),
        "label": label,
        "species_id": species_id,
        "confidence": confidence,
        "freq_low_hz": freq_low,
        "freq_high_hz": freq_high,
        "model_name": model_name,
        "model_version": model_version,
    }


def _merge(events: list[dict], hop_s: float) -> list[dict]:
    if not events:
        return []
    merged = [dict(events[0])]
    for event in events[1:]:
        prev = merged[-1]
        contiguous = event["start_time"] <= prev["end_time"] + hop_s * 0.51
        if event["label"] == prev["label"] and contiguous:
            prev["end_time"] = max(prev["end_time"], event["end_time"])
            if event["confidence"] > prev["confidence"]:
                prev["confidence"] = event["confidence"]
                prev["freq_low_hz"] = event["freq_low_hz"]
                prev["freq_high_hz"] = event["freq_high_hz"]
            continue
        merged.append(dict(event))
    return merged


def resolve_perch_path(perch_path: str | Path | None = None) -> Path:
    if perch_path is None:
        return DEFAULT_PERCH_PATH
    path = Path(perch_path)
    if path.is_file():
        return path
    candidate = _PACKAGE_ROOT / path
    if candidate.is_file():
        return candidate
    # metadata stores a repo-relative path ("ml/data/...").
    if path.parts and path.parts[0] == "ml":
        candidate = _PACKAGE_ROOT.parent / path
        if candidate.is_file():
            return candidate
    return path


def build_embedder(name: str, perch_path: str | Path | None = None):
    perch_path = resolve_perch_path(perch_path)
    if name == "lowband_v1":
        return LowBandEmbedder()
    if name == "perch_v2_backbone":
        return PerchOnnxEmbedder(perch_path)
    if name in {"perch_v2_backbone+lowband_v1", "lowband_v1+perch_v2_backbone"}:
        return ConcatEmbedder([PerchOnnxEmbedder(perch_path), LowBandEmbedder()])
    raise ValueError(f"unknown embedder {name}")


def load_detector(model_dir: str | Path | None = None, perch_path: str | Path | None = None) -> FishDetector:
    model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    key = str(model_dir.resolve())
    cached = _DETECTORS.get(key)
    if cached is not None:
        return cached
    metadata_path = model_dir / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"No model metadata at {metadata_path}. Train one with ml/scripts/train.py."
        )
    metadata = json.loads(metadata_path.read_text())
    probe_name = metadata.get("probe_file", "probe.npz")
    probe = LinearProbe.load(model_dir / probe_name)
    embedder = build_embedder(metadata["embedder"], perch_path=perch_path or metadata.get("perch_onnx"))
    detector = FishDetector(probe, embedder, metadata)
    _DETECTORS[key] = detector
    return detector


def detect(
    audio: np.ndarray,
    sample_rate: int,
    model_dir: str | Path | None = None,
    threshold: float | None = None,
    hop_s: float = DEFAULT_HOP_S,
    perch_path: str | Path | None = None,
    temporal_gate: bool = True,
) -> list[dict]:
    """Classify a hydrophone buffer.

    Parameters
    ----------
    audio:
        Mono or stereo samples. Integer PCM is scaled into [-1, 1].
    sample_rate:
        Sample rate of ``audio`` in hertz. Audio is resampled to 32 kHz.
    """
    detector = load_detector(model_dir, perch_path=perch_path)
    return detector.detect(
        audio,
        sample_rate,
        threshold=threshold,
        hop_s=hop_s,
        temporal_gate=temporal_gate,
    )


def to_detection_rows(events: list[dict], *, node_id: str, origin: datetime) -> list[dict]:
    """Map detector events onto ``public.detections`` inserts.

    ``origin`` is the timezone-aware timestamp of sample 0. Offsets in the
    events are added to it. ``species_id`` is copied through: a species-table
    slug, or None for boat and unknown.
    """
    if not node_id:
        raise ValueError("node_id is required")
    if origin.tzinfo is None or origin.utcoffset() is None:
        raise ValueError("origin must be timezone-aware")
    rows = []
    for event in events:
        start = origin + timedelta(seconds=float(event["start_time"]))
        end = origin + timedelta(seconds=float(event["end_time"]))
        if end < start:
            raise ValueError("event end_time is before start_time")
        rows.append(
            {
                "node_id": node_id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "label": event["label"],
                "species_id": event["species_id"],
                "confidence": float(event["confidence"]),
                "model_name": event["model_name"],
                "model_version": event["model_version"],
                "freq_low_hz": float(event["freq_low_hz"]),
                "freq_high_hz": float(event["freq_high_hz"]),
                "review_status": "unreviewed",
            }
        )
    return rows


def clear_detector_cache() -> None:
    _DETECTORS.clear()
