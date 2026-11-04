"""Narrowband mains hum, and the impulsive low band of sturgeon thunder.

Hum is not a trained class. The synthetic hum used in 0.2.0 was a stack of
harmonics spread across the same 10–100 Hz band as Atlantic sturgeon thunder,
and the probe then called both real thunder supplements ``hum_60hz``. A real
mains line is a steady tone at 60 Hz with harmonics at 120 and 180 Hz.
Thunder is a few percussive beats, most of the energy between 10 and 100 Hz
(Cohen et al. 2025). Those two checks are deterministic.
"""

from __future__ import annotations

import numpy as np

# Share of the 40–400 Hz power that must sit on the 60/120/180 Hz lines.
LINE_SHARE = 0.45
# Crest of the 10–100 Hz envelope. A steady line is near 1. Beats are higher.
HUM_CREST_MAX = 3.0
# Most of a thunder's power is inside 10–100 Hz, and the envelope crests.
STURGEON_LOW_SHARE = 0.40
STURGEON_CREST_MIN = 4.0
_LINE_HZ = (60.0, 120.0, 180.0)
_LINE_HALF_WIDTH_HZ = 1.5


def _spectrum(audio: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(audio, dtype=np.float64)
    if x.size < 16:
        return np.zeros(1), np.zeros(1)
    x = x - np.mean(x)
    spec = np.fft.rfft(x * np.hanning(x.size))
    power = spec.real**2 + spec.imag**2
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(sample_rate))
    return freqs, power


def _lowband_crest(audio: np.ndarray, sample_rate: int) -> float:
    """Crest factor of the 10–100 Hz envelope. Steady energy is near 1."""
    x = np.asarray(audio, dtype=np.float64)
    if x.size < sample_rate // 5:
        return 1.0
    spec = np.fft.rfft(x - np.mean(x))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(sample_rate))
    spec[(freqs < 10.0) | (freqs > 100.0)] = 0
    low = np.fft.irfft(spec, n=x.size)
    frame = max(int(0.02 * sample_rate), 1)
    hop = max(frame // 2, 1)
    env = np.array(
        [np.sqrt(np.mean(low[i : i + frame] ** 2)) for i in range(0, max(1, x.size - frame), hop)],
        dtype=np.float64,
    )
    if env.size == 0:
        return 1.0
    return float(env.max() / (env.mean() + 1e-12))


def steady_mains_hum(audio: np.ndarray, sample_rate: int) -> tuple[bool, float]:
    """Return whether this window is a steady 60 Hz line, and the line share.

    The share is the fraction of power from 40 to 400 Hz that falls within
    1.5 Hz of 60, 120, or 180 Hz. A thunder bout fails it: the beats are
    spread across 10–100 Hz and the envelope crests.
    """
    freqs, power = _spectrum(audio, sample_rate)
    if power.size < 8:
        return False, 0.0
    band = (freqs >= 40.0) & (freqs <= 400.0)
    band_power = float(power[band].sum()) + 1e-12
    lines = np.zeros(freqs.shape, dtype=bool)
    for center in _LINE_HZ:
        lines |= np.abs(freqs - center) <= _LINE_HALF_WIDTH_HZ
    share = float(power[lines & (freqs <= 400.0)].sum()) / band_power
    crest = _lowband_crest(audio, sample_rate)
    return bool(share >= LINE_SHARE and crest < HUM_CREST_MAX), float(share)


def impulsive_sturgeon_band(audio: np.ndarray, sample_rate: int) -> bool:
    """True when the window still looks like thunder, not a chorus or a wash.

    Applied only after the probe has already said ``sturgeon_thunder``. A
    drum chorus can land near that class once hum is no longer there to
    absorb it; the chorus does not put most of its power in 10–100 Hz.
    """
    freqs, power = _spectrum(audio, sample_rate)
    if power.size < 8:
        return False
    total = float(power[freqs >= 10.0].sum()) + 1e-12
    low = float(power[(freqs >= 10.0) & (freqs <= 100.0)].sum())
    if low / total < STURGEON_LOW_SHARE:
        return False
    return _lowband_crest(audio, sample_rate) >= STURGEON_CREST_MIN
