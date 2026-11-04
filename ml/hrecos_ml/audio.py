"""Audio loading, resampling, and 5-second windowing."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from hrecos_ml.labels import TARGET_SR, WINDOW_SAMPLES, WINDOW_S


def as_float_mono(audio: np.ndarray) -> np.ndarray:
    """Convert an array to mono float32 in roughly [-1, 1]."""
    x = np.asarray(audio)
    if x.size == 0:
        return np.zeros(0, dtype=np.float32)
    if np.issubdtype(x.dtype, np.integer):
        max_val = float(np.iinfo(x.dtype).max)
        x = x.astype(np.float32) / max_val
    else:
        x = x.astype(np.float32, copy=False)
    if x.ndim == 1:
        return np.ascontiguousarray(x)
    if x.ndim != 2:
        raise ValueError(f"audio must be 1-D or 2-D, got shape {x.shape}")
    # (samples, channels) when the channel axis is the short one.
    if x.shape[1] <= 8 and x.shape[0] > x.shape[1]:
        x = x.mean(axis=1)
    elif x.shape[0] <= 8:
        x = x.mean(axis=0)
    else:
        x = x.mean(axis=-1)
    return np.ascontiguousarray(x.astype(np.float32))


def resample(audio: np.ndarray, sample_rate: int, target_sr: int = TARGET_SR) -> np.ndarray:
    audio = as_float_mono(audio)
    if sample_rate == target_sr or audio.size == 0:
        return audio
    if sample_rate <= 0 or target_sr <= 0:
        raise ValueError("sample rates must be positive")
    from math import gcd

    g = gcd(int(sample_rate), int(target_sr))
    up = int(target_sr) // g
    down = int(sample_rate) // g
    y = resample_poly(audio, up, down).astype(np.float32)
    return y


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Load wav/flac/mp3 as mono float32. Uses soundfile, then ffmpeg."""
    path = Path(path)
    try:
        import soundfile as sf

        audio, sr = sf.read(str(path), always_2d=False)
        return as_float_mono(audio), int(sr)
    except Exception:
        return _load_ffmpeg(path)


def _load_ffmpeg(path: Path) -> tuple[np.ndarray, int]:
    sr = TARGET_SR
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        str(sr),
        "-f",
        "f32le",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode("utf-8", "replace")[-500:]
        raise RuntimeError(f"ffmpeg could not read {path}: {err}")
    audio = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    return audio, sr


def write_wav(path: str | Path, audio: np.ndarray, sample_rate: int) -> None:
    import soundfile as sf

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.asarray(audio, dtype=np.float32), sample_rate)


def iter_windows(
    audio: np.ndarray,
    sample_rate: int,
    hop_s: float = 1.0,
    window_s: float = WINDOW_S,
):
    """Yield (start_s, end_s, samples) with samples fixed at 5 s / 32 kHz.

    ``end_s`` is clipped to the original duration. Short inputs are zero-padded
    to the model window. Windows that start at or after the end of the audio
    are not emitted. A final window is included when audio remains.
    """
    y = resample(audio, sample_rate, TARGET_SR)
    duration = float(y.shape[0]) / TARGET_SR if y.size else 0.0
    if duration <= 0:
        return
    win = int(window_s * TARGET_SR)
    if win != WINDOW_SAMPLES:
        raise ValueError("window length must stay on the 5 s / 32 kHz contract")
    hop = max(int(round(hop_s * TARGET_SR)), 1)
    starts = list(range(0, y.shape[0], hop))
    if not starts:
        starts = [0]
    for start in starts:
        if start >= y.shape[0]:
            break
        chunk = y[start : start + win]
        if chunk.shape[0] < win:
            pad = np.zeros(win, dtype=np.float32)
            pad[: chunk.shape[0]] = chunk
            chunk = pad
        start_s = start / TARGET_SR
        end_s = min(duration, start_s + window_s)
        yield start_s, end_s, np.ascontiguousarray(chunk, dtype=np.float32)
