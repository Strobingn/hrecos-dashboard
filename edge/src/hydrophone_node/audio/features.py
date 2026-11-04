"""Uncalibrated level features for a segment.

rms_db and band_levels are 20*log10(RMS) of the float samples, plus an optional
calibration offset. With the offset at 0 this is dBFS for audio scaled to
[-1, 1], not dB re 1 µPa. Set calibration_offset_db on the Pi once the
Aquarian H2a sensitivity and preamp gain are known.
"""

from __future__ import annotations

import numpy as np

from hydrophone_node.contract import BAND_LEVEL_KEYS

BANDS_HZ = {
    "10-100": (10.0, 100.0),
    "100-500": (100.0, 500.0),
    "500-2000": (500.0, 2000.0),
}


def rms(samples: np.ndarray) -> float:
    x = np.asarray(samples, dtype=np.float64)
    if x.size == 0:
        return 0.0
    x = x - np.mean(x)
    return float(np.sqrt(np.mean(np.square(x))))


def to_db(amplitude: float) -> float:
    return float(20.0 * np.log10(max(amplitude, 1e-12)))


def band_levels(samples: np.ndarray, sample_rate: float) -> dict[str, float]:
    """Band-limited RMS in dB, keyed exactly as the audio_segments contract."""
    x = np.asarray(samples, dtype=np.float64)
    if x.size == 0:
        return {key: to_db(0.0) for key in BAND_LEVEL_KEYS}
    x = x - np.mean(x)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(sample_rate))
    power = np.square(np.abs(spec))
    n = x.size
    levels: dict[str, float] = {}
    nyquist = float(sample_rate) / 2.0
    for key in BAND_LEVEL_KEYS:
        lo, hi = BANDS_HZ[key]
        hi_eff = min(hi, nyquist)
        if hi_eff <= lo or lo >= nyquist:
            levels[key] = to_db(0.0)
            continue
        mask = (freqs >= lo) & (freqs < hi_eff)
        if not np.any(mask):
            levels[key] = to_db(0.0)
            continue
        selected = power[mask]
        fsel = freqs[mask]
        # rfft bins other than DC and Nyquist represent two-sided power.
        scale = np.ones_like(selected)
        interior = (fsel > 0.0) & (fsel < nyquist - 1e-9)
        scale[interior] = 2.0
        mean_square = float(np.sum(selected * scale) / (n * n))
        levels[key] = to_db(np.sqrt(max(mean_square, 0.0)))
    return levels


def analyze(
    samples: np.ndarray,
    sample_rate: float,
    calibration_offset_db: float = 0.0,
) -> dict[str, float | dict[str, float]]:
    offset = float(calibration_offset_db)
    levels = {
        key: value + offset for key, value in band_levels(samples, sample_rate).items()
    }
    return {
        "rms_db": to_db(rms(samples)) + offset,
        "band_levels": levels,
    }
