"""Contract tests that do not download Perch or the external corpora."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

from hrecos_ml.audio import iter_windows
from hrecos_ml.embeddings import LowBandEmbedder
from hrecos_ml.export_onnx import export_probe_onnx, fold_affine, onnx_predict_proba
from hrecos_ml.infer import FishDetector, to_detection_rows
from hrecos_ml.labels import (
    DETECTION_LABELS,
    INFERENCE_LABEL,
    SPECIES,
    TRAIN_LABELS,
    WINDOW_SAMPLES,
)
from hrecos_ml.probe import fit_probe
from hrecos_ml.synthesize import render_clip, render_splash_bout, render_stop_start_wake
from hrecos_ml.hum import impulsive_sturgeon_band, steady_mains_hum
from hrecos_ml.temporal import drop_boat_outside_wash, gate_splash_labels

REPO = Path(__file__).resolve().parents[2]
SPECIES_SLUGS = {
    "sturgeon_thunder": "atlantic_sturgeon",
    "drum_knock": "freshwater_drum",
    "toadfish_boatwhistle": "oyster_toadfish",
    "bass_spawning_splash": "striped_bass",
    "boat": None,
    "unknown": None,
}


def test_detection_labels_match_the_table_contract():
    assert DETECTION_LABELS == (
        "bass_spawning_splash",
        "sturgeon_thunder",
        "drum_knock",
        "toadfish_boatwhistle",
        "boat",
        "unknown",
    )
    for label in ("train", "hum_60hz", "rain", "wave_slap", "background"):
        assert INFERENCE_LABEL[label] == "unknown"
    for label in (
        "sturgeon_thunder",
        "drum_knock",
        "toadfish_boatwhistle",
        "bass_spawning_splash",
        "boat",
    ):
        assert INFERENCE_LABEL[label] == label


def test_windows_cover_a_short_and_a_long_buffer():
    short = np.zeros(8000, dtype=np.float32)
    windows = list(iter_windows(short, 8000, hop_s=1.0))
    assert len(windows) == 1
    start, end, samples = windows[0]
    assert start == 0
    assert samples.shape == (WINDOW_SAMPLES,)
    assert abs(end - 1.0) < 1e-6

    long = np.zeros(32000 * 8, dtype=np.float32)
    windows = list(iter_windows(long, 32000, hop_s=1.0))
    assert windows[0][0] == 0
    assert windows[-1][0] == 7.0


def test_window_end_times():
    long = np.zeros(32000 * 8, dtype=np.float32)
    windows = list(iter_windows(long, 32000, hop_s=1.0))
    assert abs(windows[-1][1] - 8.0) < 1e-6
    short = list(iter_windows(np.zeros(16000, dtype=np.float32), 32000, hop_s=1.0))
    assert abs(short[0][1] - 0.5) < 1e-6


def test_detect_schema_and_onnx_head(tmp_path: Path):
    rng = np.random.default_rng(0)
    embedder = LowBandEmbedder()
    features = []
    labels = []
    clips = {}
    for label in TRAIN_LABELS:
        clips[label] = []
        for _ in range(8):
            audio = render_clip(label, WINDOW_SAMPLES, rng)
            clips[label].append(audio)
            features.append(embedder.embed(audio.reshape(1, -1))[0])
            labels.append(label)
    probe = fit_probe(np.stack(features), np.asarray(labels))
    metadata = {
        "model_name": "hrecos-fish-probe",
        "model_version": "test",
        "embedder": "lowband_v1",
        "threshold": 0.35,
    }
    detector = FishDetector(probe, embedder, metadata)
    events = detector.detect(clips["sturgeon_thunder"][0], 32000, hop_s=1.0)
    assert events, "a training sturgeon clip should clear the threshold"
    event = events[0]
    assert set(event) == {
        "start_time",
        "end_time",
        "label",
        "species_id",
        "confidence",
        "freq_low_hz",
        "freq_high_hz",
        "model_name",
        "model_version",
    }
    assert event["label"] in DETECTION_LABELS
    assert event["model_name"] == "hrecos-fish-probe"
    assert event["model_version"] == "test"
    assert event["start_time"] == 0
    assert event["freq_high_hz"] >= event["freq_low_hz"]
    if event["label"] == "sturgeon_thunder":
        assert event["species_id"] == "atlantic_sturgeon"
    rows = to_detection_rows(
        events,
        node_id="westpoint-cornwall",
        origin=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
    )
    errors = list(_detections_validator().iter_errors(rows[0]))
    assert errors == [], errors
    assert rows[0]["species_id"] == events[0]["species_id"]

    onnx_path = export_probe_onnx(probe, tmp_path / "probe.onnx")
    weight, bias = fold_affine(probe)
    sample = np.stack(features[:4])
    numpy_probs = probe.predict_proba(sample)
    onnx_probs = onnx_predict_proba(onnx_path, sample)
    assert numpy_probs.shape == (4, len(probe.classes))
    assert np.allclose(numpy_probs, onnx_probs, atol=1e-5)
    logits = sample @ weight.T + bias
    assert logits.shape == (4, len(probe.classes))


def test_species_ids_are_seed_slugs():
    seed = (REPO / "supabase" / "seed.sql").read_text()
    for label, slug in SPECIES_SLUGS.items():
        assert SPECIES[label]["species_id"] == slug
        if slug is not None:
            assert f"'{slug}'" in seed


def test_detection_rows_match_schema():
    """Every detection label becomes a public.detections object."""
    validator = _detections_validator()
    origin = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    events = []
    for index, label in enumerate(DETECTION_LABELS):
        events.append(
            {
                "start_time": float(index),
                "end_time": float(index) + 1.5,
                "label": label,
                "species_id": SPECIES[label]["species_id"],
                "confidence": 0.75,
                "freq_low_hz": 20.0,
                "freq_high_hz": 100.0,
                "model_name": "hrecos-fish-probe",
                "model_version": "0.2.0",
            }
        )
    rows = to_detection_rows(events, node_id="westpoint-cornwall", origin=origin)
    assert [row["species_id"] for row in rows] == [
        "striped_bass",
        "atlantic_sturgeon",
        "freshwater_drum",
        "oyster_toadfish",
        None,
        None,
    ]
    for row in rows:
        errors = list(validator.iter_errors(row))
        assert errors == [], errors
        start = datetime.fromisoformat(row["start_time"])
        end = datetime.fromisoformat(row["end_time"])
        assert end - start == timedelta(seconds=1.5)
    assert rows[0]["start_time"].startswith("2026-06-15T12:00:00")


def _detections_validator() -> Draft202012Validator:
    schema = json.loads((REPO / "contracts" / "detections.schema.json").read_text())
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _splash_event(start_s: float, end_s: float) -> dict:
    return {
        "start_time": start_s,
        "end_time": end_s,
        "label": "bass_spawning_splash",
        "species_id": "striped_bass",
        "confidence": 0.8,
        "freq_low_hz": 200.0,
        "freq_high_hz": 4000.0,
        "model_name": "hrecos-fish-probe",
        "model_version": "test",
    }


def test_stop_start_wake_suppresses_a_splash_label():
    rng = np.random.default_rng(1)
    wake = render_stop_start_wake(90.0, rng)
    on_wash = gate_splash_labels([_splash_event(12.0, 17.0)], wake, 32000)
    assert on_wash[0]["label"] == "boat"
    assert on_wash[0]["species_id"] is None
    # Quiet gap between the two washes (schedule 34–46 s of the 90 s template).
    in_gap = gate_splash_labels([_splash_event(36.0, 40.0)], wake, 32000)
    assert in_gap[0]["label"] == "boat"
    assert in_gap[0]["species_id"] is None


def test_splash_bout_keeps_the_splash_label():
    rng = np.random.default_rng(2)
    bout = render_splash_bout(70.0, rng)
    gated = gate_splash_labels([_splash_event(4.0, 8.0)], bout, 32000)
    assert gated[0]["label"] == "bass_spawning_splash"
    assert gated[0]["species_id"] == "striped_bass"


def test_splash_bout_drops_a_spurious_boat_label():
    rng = np.random.default_rng(4)
    bout = render_splash_bout(70.0, rng)
    events = [
        _splash_event(4.0, 8.0),
        {
            "start_time": 20.0,
            "end_time": 25.0,
            "label": "boat",
            "species_id": None,
            "confidence": 0.7,
            "freq_low_hz": 40.0,
            "freq_high_hz": 2000.0,
            "model_name": "hrecos-fish-probe",
            "model_version": "test",
        },
    ]
    gated = drop_boat_outside_wash(events, bout, 32000)
    assert [row["label"] for row in gated] == ["bass_spawning_splash"]


def test_wake_keeps_a_boat_label_on_the_wash():
    rng = np.random.default_rng(5)
    wake = render_stop_start_wake(90.0, rng)
    boat = {
        "start_time": 12.0,
        "end_time": 17.0,
        "label": "boat",
        "species_id": None,
        "confidence": 0.8,
        "freq_low_hz": 40.0,
        "freq_high_hz": 2000.0,
        "model_name": "hrecos-fish-probe",
        "model_version": "test",
    }
    gated = drop_boat_outside_wash([boat], wake, 32000)
    assert gated[0]["label"] == "boat"


def test_mains_hum_is_narrow_and_thunder_is_not():
    rng = np.random.default_rng(6)
    hum = render_clip("hum_60hz", 160_000, rng)
    thunder = render_clip("sturgeon_thunder", 160_000, rng)
    splash = render_clip("bass_spawning_splash", 160_000, rng)
    hum_hit, share = steady_mains_hum(hum, 32000)
    assert hum_hit and share >= 0.45
    assert steady_mains_hum(thunder, 32000)[0] is False
    assert steady_mains_hum(splash, 32000)[0] is False
    assert impulsive_sturgeon_band(thunder, 32000)
    assert impulsive_sturgeon_band(splash, 32000) is False
    assert impulsive_sturgeon_band(hum, 32000) is False


def test_short_buffer_is_not_gated():
    rng = np.random.default_rng(3)
    wake = render_stop_start_wake(20.0, rng)
    gated = gate_splash_labels([_splash_event(6.0, 10.0)], wake, 32000)
    assert gated[0]["label"] == "bass_spawning_splash"
