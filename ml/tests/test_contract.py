"""Contract tests that do not download Perch or the external corpora."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hrecos_ml.audio import iter_windows
from hrecos_ml.embeddings import LowBandEmbedder
from hrecos_ml.export_onnx import export_probe_onnx, fold_affine, onnx_predict_proba
from hrecos_ml.infer import FishDetector
from hrecos_ml.labels import DETECTION_LABELS, INFERENCE_LABEL, TRAIN_LABELS, WINDOW_SAMPLES
from hrecos_ml.probe import fit_probe
from hrecos_ml.synthesize import render_clip


def test_detection_labels_match_the_table_contract():
    assert DETECTION_LABELS == (
        "sturgeon_thunder",
        "drum_knock",
        "toadfish_boatwhistle",
        "boat",
        "unknown",
    )
    for label in ("train", "hum_60hz", "background"):
        assert INFERENCE_LABEL[label] == "unknown"
    for label in ("sturgeon_thunder", "drum_knock", "toadfish_boatwhistle", "boat"):
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
        assert event["species_id"] == "itis:624004"

    onnx_path = export_probe_onnx(probe, tmp_path / "probe.onnx")
    weight, bias = fold_affine(probe)
    sample = np.stack(features[:4])
    numpy_probs = probe.predict_proba(sample)
    onnx_probs = onnx_predict_proba(onnx_path, sample)
    assert numpy_probs.shape == (4, len(probe.classes))
    assert np.allclose(numpy_probs, onnx_probs, atol=1e-5)
    # The folded affine is what the ONNX graph multiplies.
    logits = sample @ weight.T + bias
    assert logits.shape == (4, len(probe.classes))
