"""WAV encode/decode that does not require libsndfile.

FLAC and float WAV still go through soundfile when a file source needs them.
"""

from __future__ import annotations

import io
import wave

import numpy as np


def write_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    pcm = np.clip(np.asarray(samples, dtype=np.float64), -1.0, 1.0)
    ints = (pcm * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(ints.tobytes())
    return buf.getvalue()


def decode_pcm(raw: bytes, sampwidth: int, channels: int) -> np.ndarray:
    if channels < 1:
        raise ValueError("WAV has no channels")
    if sampwidth == 1:
        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sampwidth == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sampwidth == 3:
        nbytes = len(raw) - (len(raw) % 3)
        triples = np.frombuffer(raw[:nbytes], dtype=np.uint8).reshape(-1, 3)
        values = (
            triples[:, 0].astype(np.int32)
            | (triples[:, 1].astype(np.int32) << 8)
            | (triples[:, 2].astype(np.int32) << 16)
        )
        values = np.where(values >= 2**23, values - 2**24, values)
        data = values.astype(np.float32) / float(2**23)
    elif sampwidth == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported WAV sample width: {sampwidth}")
    if channels > 1:
        usable = data.size - (data.size % channels)
        data = data[:usable].reshape(-1, channels).mean(axis=1)
    return np.ascontiguousarray(data, dtype=np.float32)


def read_wav(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as handle:
        sample_rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        raw = handle.readframes(handle.getnframes())
    return decode_pcm(raw, width, channels), sample_rate
