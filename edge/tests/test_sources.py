import wave
from pathlib import Path

import numpy as np
import pytest

from hydrophone_node.audio.sources import (
    FolderSource,
    audio_names_from_gcs_list,
    gcs_media_url,
    resample_audio,
)
from hydrophone_node.audio.wavio import read_wav, write_wav_bytes


def test_gcs_helpers_match_the_public_bucket():
    payload = {
        "items": [
            {"name": "sanctsound/readme.pdf"},
            {"name": "sanctsound/audio/site_a.wav"},
            {"name": "sanctsound/audio/site_b.flac"},
            {"name": "sanctsound/audio/notes.txt"},
        ]
    }
    assert audio_names_from_gcs_list(payload) == [
        "sanctsound/audio/site_a.wav",
        "sanctsound/audio/site_b.flac",
    ]
    url = gcs_media_url("noaa-passive-bioacoustic", "sanctsound/audio/site_a.wav")
    assert (
        url
        == "https://storage.googleapis.com/noaa-passive-bioacoustic/sanctsound/audio/site_a.wav"
    )


def test_folder_source_concatenates_wavs_in_name_order(tmp_path: Path):
    sample_rate = 8000
    first = np.full(sample_rate, 0.25, dtype=np.float32)
    second = np.full(sample_rate // 2, -0.5, dtype=np.float32)
    (tmp_path / "b.wav").write_bytes(write_wav_bytes(second, sample_rate))
    (tmp_path / "a.wav").write_bytes(write_wav_bytes(first, sample_rate))
    chunks = list(FolderSource(tmp_path, sample_rate))
    audio = np.concatenate(chunks)
    assert audio.size == first.size + second.size
    assert audio[0] > 0
    assert audio[-1] < 0


def test_resample_doubles_a_known_length():
    samples = np.zeros(1000, dtype=np.float32)
    converted = resample_audio(samples, 4000, 8000)
    assert converted.size == 2000


def test_flac_roundtrip(tmp_path: Path):
    soundfile = pytest.importorskip("soundfile")
    sample_rate = 8000
    tone = (
        0.3 * np.sin(2 * np.pi * 180 * np.arange(sample_rate) / sample_rate)
    ).astype(np.float32)
    path = tmp_path / "tone.flac"
    soundfile.write(path, tone, sample_rate)
    chunks = list(FolderSource(tmp_path, sample_rate))
    audio = np.concatenate(chunks)
    assert abs(audio.size - tone.size) <= 2
    assert np.corrcoef(tone[: audio.size], audio[: tone.size])[0, 1] > 0.98


def test_wav_roundtrip_preserves_a_tone(tmp_path: Path):
    sample_rate = 8000
    t = np.arange(sample_rate) / sample_rate
    tone = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    path = tmp_path / "tone.wav"
    path.write_bytes(write_wav_bytes(tone, sample_rate))
    decoded, rate = read_wav(str(path))
    assert rate == sample_rate
    assert np.corrcoef(tone, decoded[: tone.size])[0, 1] > 0.99
    # stdlib wave header is mono 16-bit
    with wave.open(str(path), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
