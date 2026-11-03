"""Band-energy detector against the synthetic call templates."""

import numpy as np
import pytest

from hydrophone_node.audio.synthesize import (
    BASS_BOUT_DURATION_S,
    BOAT_PASS_DURATION_S,
    DRUM_DURATION_S,
    STURGEON_DURATION_S,
    TOADFISH_DURATION_S,
    SynthEvent,
    render_interval,
    render_scene,
)
from hydrophone_node.contract import LABEL_SPECIES
from hydrophone_node.detect.band_energy import BandEnergyDetector
from hydrophone_node.detect.registry import build_detector, load_entrypoint

SAMPLE_RATE = 8000
FISH = {
    "sturgeon_thunder",
    "drum_knock",
    "toadfish_boatwhistle",
    "bass_spawning_splash",
}


def _detect(events, duration=12.0, seed=1):
    audio = render_scene(SAMPLE_RATE, duration, events, seed=seed)
    return BandEnergyDetector().detect(audio, SAMPLE_RATE), audio


def _overlaps(event, start, end):
    return event.end_offset_s > start and event.start_offset_s < end + 0.15


def test_detects_sturgeon_thunder_and_not_the_other_fish():
    start = 3.0
    events, _ = _detect([SynthEvent("sturgeon_thunder", start, STURGEON_DURATION_S)])
    hits = [
        event
        for event in events
        if event.label == "sturgeon_thunder" and _overlaps(event, start, start + 1.9)
    ]
    assert len(hits) == 1
    assert hits[0].species_id == "atlantic_sturgeon"
    assert hits[0].freq_low_hz == 10
    assert hits[0].freq_high_hz == 100
    assert 0.0 <= hits[0].confidence <= 1.0
    assert not any(event.label in FISH - {"sturgeon_thunder"} for event in events)


def test_detects_drum_knock_train():
    start = 3.0
    events, _ = _detect([SynthEvent("drum_knock", start, DRUM_DURATION_S)])
    hits = [
        event
        for event in events
        if event.label == "drum_knock" and _overlaps(event, start, start + 0.8)
    ]
    assert len(hits) == 1
    assert hits[0].species_id == LABEL_SPECIES["drum_knock"]
    assert hits[0].freq_low_hz == 350
    assert not any(event.label in FISH - {"drum_knock"} for event in events)


def test_detects_toadfish_boatwhistle():
    start = 3.0
    events, _ = _detect(
        [SynthEvent("toadfish_boatwhistle", start, TOADFISH_DURATION_S)]
    )
    hits = [
        event
        for event in events
        if event.label == "toadfish_boatwhistle"
        and _overlaps(event, start, start + 0.5)
    ]
    assert len(hits) == 1
    assert hits[0].species_id == "oyster_toadfish"
    assert not any(event.label in FISH - {"toadfish_boatwhistle"} for event in events)


def test_detects_a_close_boat_pass():
    start = 2.0
    events, _ = _detect(
        [SynthEvent("boat", start, BOAT_PASS_DURATION_S)],
        duration=12.0,
    )
    hits = [
        event
        for event in events
        if event.label == "boat" and _overlaps(event, start, start + 5)
    ]
    assert len(hits) == 1
    assert hits[0].species_id is None
    assert not any(event.label in FISH for event in events)


def test_detects_bass_spawning_splash():
    start = 4.0
    events, _ = _detect(
        [SynthEvent("bass_spawning_splash", start, BASS_BOUT_DURATION_S)],
        duration=12.0,
    )
    hits = [
        event
        for event in events
        if event.label == "bass_spawning_splash"
        and _overlaps(event, start, start + BASS_BOUT_DURATION_S)
    ]
    assert len(hits) == 1
    assert hits[0].species_id == "striped_bass"
    assert hits[0].freq_low_hz == 200
    assert hits[0].freq_high_hz == 2000
    assert 0.0 <= hits[0].confidence <= 1.0
    assert not any(event.label in FISH - {"bass_spawning_splash"} for event in events)


def test_stop_start_wake_is_not_a_spawning_splash():
    """A long stop-start wake, with engine rumble before each slap, is not bass.

    The on-periods last many seconds. That is the field distinction from a
    rock fight, which is a short cluster of sharp splashes.
    """
    events, _ = _detect(
        [SynthEvent("stop_start_wake", 0.0, 48.0)],
        duration=48.0,
        seed=3,
    )
    assert not any(event.label == "bass_spawning_splash" for event in events)


def test_rain_is_not_a_spawning_splash():
    events, _ = _detect([], duration=30.0, seed=5)
    rainy, _ = _detect(
        [SynthEvent("rain", 0.0, 30.0)],
        duration=30.0,
        seed=5,
    )
    assert not any(event.label == "bass_spawning_splash" for event in events)
    assert not any(event.label == "bass_spawning_splash" for event in rainy)


def test_bass_bout_still_detected_after_a_wake():
    events, _ = _detect(
        [
            SynthEvent("stop_start_wake", 0.0, 36.0),
            SynthEvent("bass_spawning_splash", 42.0, BASS_BOUT_DURATION_S),
        ],
        duration=50.0,
        seed=4,
    )
    bass = [event for event in events if event.label == "bass_spawning_splash"]
    assert len(bass) == 1
    assert _overlaps(bass[0], 42.0, 42.0 + BASS_BOUT_DURATION_S)
    assert bass[0].species_id == "striped_bass"


def test_hum_and_distant_boats_are_not_fish():
    events, _ = _detect([], duration=15.0, seed=9)
    assert not any(event.label in FISH for event in events)


@pytest.mark.parametrize("sample_rate", [8000, 48000])
def test_one_minute_scene_finds_every_template(sample_rate):
    audio = render_interval(0.0, 60.0, sample_rate, 60.0, seed=2)
    events = BandEnergyDetector().detect(audio, sample_rate)
    labels = {event.label for event in events}
    assert {
        "sturgeon_thunder",
        "drum_knock",
        "toadfish_boatwhistle",
        "bass_spawning_splash",
        "boat",
    } <= labels
    for event in events:
        assert event.model_name == "band_energy"
        assert event.model_version == "1.0.0"
        assert 0.0 <= event.confidence <= 1.0


def test_ml_entrypoint_replaces_the_baseline(tmp_path, monkeypatch):
    plugin = tmp_path / "demo_detector.py"
    plugin.write_text(
        "class Demo:\n"
        "    model_name = 'demo'\n"
        "    model_version = '9'\n"
        "    def detect(self, samples, sample_rate, segment_start=None):\n"
        "        return []\n"
        "def build():\n"
        "    return Demo()\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    detector = load_entrypoint("demo_detector:build")
    assert detector.model_name == "demo"
    assert build_detector("ml", "demo_detector:build").detect(np.zeros(10), 8000) == []


def test_unknown_detector_name_is_rejected():
    try:
        build_detector("mystery")
    except ValueError as exc:
        assert "band_energy" in str(exc)
    else:
        raise AssertionError("expected ValueError")
