import numpy as np

from hydrophone_node.audio.features import analyze, band_levels, rms, to_db
from hydrophone_node.contract import BAND_LEVEL_KEYS


def test_sine_rms_matches_closed_form():
    sample_rate = 8000
    amplitude = 0.5
    t = np.arange(sample_rate) / sample_rate
    tone = amplitude * np.sin(2 * np.pi * 44 * t)
    expected = amplitude / np.sqrt(2)
    assert abs(rms(tone) - expected) < 1e-3
    assert abs(to_db(rms(tone)) - to_db(expected)) < 0.05


def test_band_levels_put_44_hz_in_the_low_band():
    sample_rate = 8000
    t = np.arange(sample_rate * 2) / sample_rate
    tone = 0.4 * np.sin(2 * np.pi * 44 * t)
    levels = band_levels(tone, sample_rate)
    assert tuple(levels) == BAND_LEVEL_KEYS
    assert levels["10-100"] > levels["100-500"] + 20
    assert levels["10-100"] > levels["500-2000"] + 20


def test_calibration_offset_is_added_to_every_level():
    sample_rate = 8000
    t = np.arange(sample_rate) / sample_rate
    tone = 0.2 * np.sin(2 * np.pi * 400 * t)
    plain = analyze(tone, sample_rate, 0)
    shifted = analyze(tone, sample_rate, 6)
    assert abs(shifted["rms_db"] - plain["rms_db"] - 6) < 1e-9
    for key in BAND_LEVEL_KEYS:
        assert abs(shifted["band_levels"][key] - plain["band_levels"][key] - 6) < 1e-9
