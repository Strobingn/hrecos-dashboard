"""Measured frequency bounds for a detection window."""

from __future__ import annotations

import numpy as np

from hrecos_ml.labels import TARGET_SR


def energy_percentiles(
    audio: np.ndarray,
    sample_rate: int = TARGET_SR,
    fmin: float = 10.0,
    fmax: float = 4000.0,
    q_low: float = 0.10,
    q_high: float = 0.90,
) -> tuple[float, float]:
    """Return frequencies enclosing the central portion of spectral energy.

    The band is data-derived. Class literature bounds live in ``labels.SPECIES``
    and are not substituted here.
    """
    x = np.asarray(audio, dtype=np.float64)
    if x.size < 16:
        return float(fmin), float(fmax)
    x = x - np.mean(x)
    window = np.hanning(x.size)
    spec = np.fft.rfft(x * window)
    power = spec.real**2 + spec.imag**2
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(sample_rate))
    mask = (freqs >= fmin) & (freqs <= fmax)
    if not np.any(mask) or float(power[mask].sum()) <= 0:
        return float(fmin), float(fmax)
    f = freqs[mask]
    p = power[mask]
    cdf = np.cumsum(p)
    cdf /= cdf[-1]
    low = float(f[int(np.searchsorted(cdf, q_low, side="left"))])
    high_idx = int(np.searchsorted(cdf, q_high, side="left"))
    high_idx = min(high_idx, f.size - 1)
    high = float(f[high_idx])
    if high < low:
        high = low
    return low, high
