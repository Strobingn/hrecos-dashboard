"""Real sturgeon and drum clips. Skipped when the audio or Perch file is absent.

Sturgeon is required: both Cohen et al. 2025 supplements must produce
``sturgeon_thunder`` from ``detect()``. Drum clips are run in the same test.
A bass splash label on those fish files fails the test. Striped bass stays
the priority class, and these clips are not allowed to wear it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hrecos_ml.audio import load_audio
from hrecos_ml.infer import DEFAULT_MODEL_DIR, DEFAULT_PERCH_PATH, detect

ROOT = Path(__file__).resolve().parents[1]
STURGEON = (
    ROOT / "data" / "external" / "esr01429" / "n058p001_AS1.mp3",
    ROOT / "data" / "external" / "esr01429" / "n058p001_AS2.mp3",
)
DRUM = (
    ROOT / "data" / "external" / "fishsounds" / "200686.wav",
    ROOT / "data" / "external" / "fishsounds" / "200719.wav",
    ROOT / "data" / "external" / "fishsounds" / "200764.wav",
    ROOT / "data" / "external" / "fishsounds" / "200676.wav",
)


def _ready() -> None:
    if not (DEFAULT_MODEL_DIR / "metadata.json").is_file():
        pytest.skip("trained probe is not in the artifact directory")
    if not DEFAULT_PERCH_PATH.is_file():
        pytest.skip("Perch ONNX is not downloaded")
    missing = [path.name for path in (*STURGEON, *DRUM) if not path.is_file()]
    if missing:
        pytest.skip("real clips not downloaded: " + ", ".join(missing))


def test_real_sturgeon_is_detected_and_drum_is_not_bass():
    _ready()
    for path in STURGEON:
        audio, sr = load_audio(path)
        events = detect(audio, sr, hop_s=1.0)
        sturgeon = [event for event in events if event["label"] == "sturgeon_thunder"]
        assert sturgeon, f"{path.name} produced {[event['label'] for event in events]}"
        assert all(event["species_id"] == "atlantic_sturgeon" for event in sturgeon)
    for path in DRUM:
        audio, sr = load_audio(path)
        events = detect(audio, sr, hop_s=1.0)
        assert all(event["label"] != "bass_spawning_splash" for event in events), path.name
        if path.name == "200676.wav":
            assert all(event["label"] != "sturgeon_thunder" for event in events), path.name
        if path.name in {"200719.wav", "200764.wav"}:
            assert any(event["label"] == "drum_knock" for event in events), path.name
