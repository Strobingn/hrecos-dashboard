"""Synthetic Hudson River soundscape clips.

Signals follow the published bands for the three fish classes and are mixed
with pink noise, a weak 60 Hz line, and occasional distant boat noise. This
corpus is what the committed probe is trained on. It is not a substitute for
annotated Hudson River recordings.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hrecos_ml.audio import write_wav
from hrecos_ml.labels import TARGET_SR, TRAIN_LABELS

SR = TARGET_SR


def _bandlimit(y: np.ndarray, fmin: float, fmax: float, sr: int = SR) -> np.ndarray:
    spec = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(y.size, d=1.0 / sr)
    spec[(freqs < fmin) | (freqs > fmax)] = 0
    out = np.fft.irfft(spec, n=y.size)
    return out.astype(np.float32)


def _rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y, dtype=np.float64))) + 1e-12)


def _scale_rms(y: np.ndarray, target: float) -> np.ndarray:
    return (y * (target / _rms(y))).astype(np.float32)


def pink_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.normal(size=n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / SR)
    spec[1:] /= np.maximum(freqs[1:], 1.0) ** 0.5
    y = np.fft.irfft(spec, n=n).astype(np.float32)
    peak = float(np.max(np.abs(y)) + 1e-9)
    return y / peak


def _hum(n: int, rng: np.random.Generator, harmonic_decay: float = 0.45) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    y = np.zeros(n, dtype=np.float32)
    amp = 1.0
    for k in range(1, 6):
        phase = float(rng.uniform(0, 2 * np.pi))
        y += amp * np.sin(2 * np.pi * 60.0 * k * t + phase).astype(np.float32)
        amp *= harmonic_decay
    return y


def _place(canvas: np.ndarray, snippet: np.ndarray, start: int) -> None:
    if snippet.size == 0:
        return
    start = int(np.clip(start, 0, canvas.size - 1))
    end = min(canvas.size, start + snippet.size)
    canvas[start:end] += snippet[: end - start]


def render_sturgeon(n: int, rng: np.random.Generator) -> np.ndarray:
    """Percussive bout, about 1.4–2.2 s, energy kept inside 10–100 Hz."""
    y = np.zeros(n, dtype=np.float32)
    bout_s = float(rng.uniform(1.4, 2.2))
    bout = int(bout_s * SR)
    start = int(rng.integers(0, max(1, n - bout)))
    n_beats = int(rng.integers(3, 7))
    gaps = rng.uniform(0.25, 0.55, size=n_beats)
    times = start + np.cumsum(gaps) * SR
    times = times[times < start + bout]
    if times.size == 0:
        times = np.array([start + bout // 3])
    for ts in times:
        f0 = float(np.clip(rng.normal(44.0, 10.0), 18.0, 90.0))
        dur = int(rng.uniform(0.08, 0.22) * SR)
        t = np.arange(dur, dtype=np.float32) / SR
        decay = np.exp(-t / float(rng.uniform(0.03, 0.09))).astype(np.float32)
        pulse = np.sin(2 * np.pi * f0 * t).astype(np.float32) * decay
        noise = rng.normal(size=dur).astype(np.float32) * decay
        pulse = pulse + 0.35 * noise
        pulse = _bandlimit(pulse, 10.0, 100.0)
        _place(y, pulse, int(ts))
    return _bandlimit(y, 10.0, 120.0)


def render_drum(n: int, rng: np.random.Generator) -> np.ndarray:
    """Knock train with energy around a few hundred hertz."""
    y = np.zeros(n, dtype=np.float32)
    n_knocks = int(rng.integers(5, 18))
    interval = float(rng.uniform(0.06, 0.16))
    span = int(n_knocks * interval * SR)
    start = int(rng.integers(0, max(1, n - span)))
    for i in range(n_knocks):
        f0 = float(np.clip(rng.normal(400.0, 60.0), 220.0, 700.0))
        dur = int(rng.uniform(0.008, 0.02) * SR)
        t = np.arange(dur, dtype=np.float32) / SR
        decay = np.exp(-t / 0.006).astype(np.float32)
        knock = np.sin(2 * np.pi * f0 * t).astype(np.float32) * decay
        knock += 0.5 * rng.normal(size=dur).astype(np.float32) * decay
        knock = _bandlimit(knock, 180.0, 900.0)
        _place(y, knock, start + int(i * interval * SR))
    return y


def render_toadfish(n: int, rng: np.random.Generator) -> np.ndarray:
    """Tonal boatwhistle, optional short grunt in front of it."""
    y = np.zeros(n, dtype=np.float32)
    dur_s = float(rng.uniform(0.25, 0.55))
    dur = int(dur_s * SR)
    start = int(rng.integers(0, max(1, n - dur - int(0.1 * SR))))
    if rng.random() < 0.7:
        grunt_dur = int(rng.uniform(0.03, 0.08) * SR)
        grunt = rng.normal(size=grunt_dur).astype(np.float32)
        grunt *= np.exp(-np.arange(grunt_dur) / (0.015 * SR)).astype(np.float32)
        grunt = _bandlimit(grunt, 80.0, 600.0)
        _place(y, grunt, start)
        start = start + grunt_dur + int(0.02 * SR)
    f0 = float(rng.uniform(110.0, 240.0))
    t = np.arange(dur, dtype=np.float32) / SR
    # Slow frequency droop, a few percent, typical of a boatwhistle.
    f_inst = f0 * (1.0 - float(rng.uniform(0.0, 0.06)) * (t / max(dur_s, 1e-3)))
    phase = 2 * np.pi * np.cumsum(f_inst) / SR
    tone = np.zeros(dur, dtype=np.float32)
    amp = 1.0
    for h in range(1, 5):
        tone += amp * np.sin(h * phase).astype(np.float32)
        amp *= 0.45
    env = np.ones(dur, dtype=np.float32)
    attack = int(0.03 * SR)
    release = int(0.05 * SR)
    if attack > 0:
        env[:attack] = np.linspace(0, 1, attack, dtype=np.float32)
    if release > 0:
        env[-release:] = np.linspace(1, 0, release, dtype=np.float32)
    _place(y, tone * env, start)
    return y


def render_boat(n: int, rng: np.random.Generator) -> np.ndarray:
    """Low-frequency engine modulation plus broadband rumble. Not a 60 Hz line."""
    noise = pink_noise(n, rng)
    noise = _bandlimit(noise, 20.0, 1500.0)
    t = np.arange(n, dtype=np.float32) / SR
    rate = float(rng.uniform(1.5, 6.0))
    mod = 0.55 + 0.45 * np.sin(2 * np.pi * rate * t + float(rng.uniform(0, 6))).astype(np.float32)
    engine_hz = float(rng.uniform(38.0, 52.0) if rng.random() < 0.5 else rng.uniform(70.0, 140.0))
    engine = np.sin(2 * np.pi * engine_hz * t).astype(np.float32)
    engine += 0.4 * np.sin(2 * np.pi * 2 * engine_hz * t).astype(np.float32)
    y = noise * mod + 0.8 * engine
    return y.astype(np.float32)


def render_train(n: int, rng: np.random.Generator) -> np.ndarray:
    """Rhythmic broadband impacts over low rumble."""
    y = _bandlimit(pink_noise(n, rng), 30.0, 2000.0) * 0.35
    rate = float(rng.uniform(2.0, 5.5))
    step = int(SR / rate)
    width = int(0.012 * SR)
    pos = int(rng.integers(0, step))
    while pos < n:
        dur = min(width, n - pos)
        burst = rng.normal(size=dur).astype(np.float32)
        burst *= np.hanning(dur).astype(np.float32)
        y[pos : pos + dur] += burst
        pos += step + int(rng.normal(0, 0.004 * SR))
    return _bandlimit(y, 30.0, 2500.0)


def render_hum(n: int, rng: np.random.Generator) -> np.ndarray:
    y = _hum(n, rng)
    # Slow level drift so the line is not perfectly stationary.
    t = np.arange(n, dtype=np.float32) / SR
    drift = 0.8 + 0.2 * np.sin(2 * np.pi * float(rng.uniform(0.1, 0.4)) * t).astype(np.float32)
    return (y * drift).astype(np.float32)


def render_background(n: int, rng: np.random.Generator) -> np.ndarray:
    y = _bandlimit(pink_noise(n, rng), 15.0, 4000.0)
    t = np.arange(n, dtype=np.float32) / SR
    drift = 0.75 + 0.25 * np.sin(2 * np.pi * float(rng.uniform(0.05, 0.3)) * t).astype(np.float32)
    return (y * drift).astype(np.float32)


RENDERERS = {
    "sturgeon_thunder": render_sturgeon,
    "drum_knock": render_drum,
    "toadfish_boatwhistle": render_toadfish,
    "boat": render_boat,
    "train": render_train,
    "hum_60hz": render_hum,
    "background": render_background,
}


def mix_scene(foreground: np.ndarray, label: str, rng: np.random.Generator) -> np.ndarray:
    """Place a class signal in river-like noise at a random SNR."""
    n = foreground.shape[0]
    noise = _scale_rms(_bandlimit(pink_noise(n, rng), 15.0, 4000.0), 0.05)
    signal = foreground.astype(np.float32)
    if _rms(signal) < 1e-6:
        signal = noise.copy()
    signal = _scale_rms(signal, 0.1)
    if label == "background":
        y = signal
        snr_db = 0.0
    else:
        snr_db = float(rng.uniform(-2.0, 16.0))
        noise_rms = _rms(signal) / (10 ** (snr_db / 20.0))
        y = signal + noise * (noise_rms / _rms(noise))
    # Every clip carries some electrical hum. Only hum_60hz is dominated by it.
    hum_rms = _rms(y) * (0.8 if label == "hum_60hz" else float(rng.uniform(0.02, 0.08)))
    y = y + _scale_rms(_hum(n, rng), hum_rms)
    fish = {"sturgeon_thunder", "drum_knock", "toadfish_boatwhistle"}
    if label in fish and rng.random() < 0.35:
        boat = _scale_rms(render_boat(n, rng), _rms(y) * float(rng.uniform(0.15, 0.45)))
        y = y + boat
    peak = float(np.max(np.abs(y)) + 1e-9)
    if peak > 0.98:
        y = y * (0.98 / peak)
    return y.astype(np.float32)


def render_clip(label: str, n: int, rng: np.random.Generator) -> np.ndarray:
    if label not in RENDERERS:
        raise KeyError(label)
    return mix_scene(RENDERERS[label](n, rng), label, rng)


def write_split(
    root: str | Path,
    split: str,
    n_per_class: int,
    seed: int,
    duration_s: float = 5.0,
) -> list[dict]:
    """Write deterministic clips and return manifest rows."""
    root = Path(root)
    rng = np.random.default_rng(seed)
    n = int(duration_s * SR)
    rows: list[dict] = []
    for label in TRAIN_LABELS:
        for i in range(n_per_class):
            audio = render_clip(label, n, rng)
            path = root / split / label / f"{i:04d}.wav"
            write_wav(path, audio, SR)
            rows.append(
                {
                    "path": str(path),
                    "label": label,
                    "split": split,
                    "source": "synthetic",
                    "license": "synthetic, generated by hrecos_ml.synthesize",
                    "attribution": "Procedural approximation of published frequency bands. Not a field recording.",
                    "sample_rate": SR,
                    "duration_s": duration_s,
                    "seed": seed,
                    "index": i,
                }
            )
    return rows
