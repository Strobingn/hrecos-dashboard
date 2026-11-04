"""Frozen embedders.

Default stack is the Perch 2.0 backbone (1536-d, 5 s, 32 kHz) plus a small
fixed low-frequency descriptor. Perch's bird-oriented frontend is a poor match
for a 44 Hz sturgeon pulse, so the low-band descriptor is concatenated rather
than treated as a trained feature extractor.

SurfPerch (1280-d) is available as an optional TensorFlow SavedModel loader.
It is not the default: the Zenodo export needs TensorFlow, and this baseline
is meant to run on CPU with ONNX Runtime.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from hrecos_ml.labels import TARGET_SR, WINDOW_SAMPLES


def lowband_features(audio: np.ndarray, sample_rate: int = TARGET_SR) -> np.ndarray:
    """Fixed descriptor aimed at 8–160 Hz plus a few contrast ratios.

    The transform is deterministic and is not fit on labels.
    """
    x = np.asarray(audio, dtype=np.float64)
    if x.size != WINDOW_SAMPLES:
        raise ValueError(f"expected {WINDOW_SAMPLES} samples, got {x.size}")
    x = x - np.mean(x)
    spec = np.fft.rfft(x * np.hanning(x.size))
    power = spec.real**2 + spec.imag**2 + 1e-20
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(sample_rate))

    edges = np.geomspace(8.0, 160.0, 17)
    bands: list[float] = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (freqs >= lo) & (freqs < hi)
        bands.append(float(np.log10(power[mask].mean())) if np.any(mask) else -20.0)

    def integ(a: float, b: float) -> float:
        mask = (freqs >= a) & (freqs < b)
        return float(power[mask].sum()) if np.any(mask) else 1e-20

    def line(f0: float, bw: float = 1.5) -> float:
        mask = (freqs >= f0 - bw) & (freqs <= f0 + bw)
        return float(power[mask].mean()) if np.any(mask) else 1e-20

    low = (freqs >= 8.0) & (freqs <= 160.0)
    centroid = float((freqs[low] * power[low]).sum() / power[low].sum())
    flat = float(np.exp(np.mean(np.log(power[low]))) / power[low].mean())
    hum = float(np.log10(line(60.0) / (0.5 * (line(50.0, 3.0) + line(70.0, 3.0)))))
    ratio_low_mid = float(np.log10(integ(10.0, 100.0) / integ(200.0, 800.0)))

    frame = int(0.01 * sample_rate)
    n_frames = x.size // frame
    env = np.abs(x[: n_frames * frame]).reshape(n_frames, frame).mean(axis=1)
    env = env - env.mean()
    env_spec = np.abs(np.fft.rfft(env * np.hanning(env.size))) ** 2 + 1e-20
    env_freq = np.fft.rfftfreq(env.size, d=0.01)
    mod = (env_freq >= 0.4) & (env_freq <= 20.0)
    peak_rate = float(env_freq[mod][int(np.argmax(env_spec[mod]))])
    peak_prom = float(np.log10(env_spec[mod].max() / env_spec[mod].mean()))

    mid = (freqs >= 80.0) & (freqs <= 800.0)
    peak_f = float(freqs[mid][int(np.argmax(power[mid]))])
    rms = float(np.sqrt(np.mean(x**2)) + 1e-12)
    crest = float(np.max(np.abs(x)) / rms)
    zcr = float(np.mean(np.abs(np.diff(np.sign(x)))) / 2.0)

    feats = np.array(
        bands
        + [centroid, flat, hum, ratio_low_mid, peak_rate, peak_prom, peak_f, crest, zcr, np.log10(rms)],
        dtype=np.float32,
    )
    return np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=-20.0)


class LowBandEmbedder:
    name = "lowband_v1"

    def __init__(self) -> None:
        self.dim = int(lowband_features(np.zeros(WINDOW_SAMPLES, dtype=np.float32)).shape[0])

    def embed(self, batch: np.ndarray) -> np.ndarray:
        batch = np.asarray(batch, dtype=np.float32)
        if batch.ndim != 2 or batch.shape[1] != WINDOW_SAMPLES:
            raise ValueError(f"expected (N, {WINDOW_SAMPLES}), got {batch.shape}")
        return np.stack([lowband_features(row) for row in batch], axis=0)


class PerchOnnxEmbedder:
    """Perch 2.0 backbone. Input ``inputs`` float32 [N, 160000], output ``embedding`` [N, 1536]."""

    name = "perch_v2_backbone"

    def __init__(self, model_path: str | Path, batch_size: int = 8) -> None:
        import onnxruntime as ort

        self.model_path = str(model_path)
        self.session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        outputs = [o.name for o in self.session.get_outputs()]
        if "embedding" not in outputs:
            raise RuntimeError(f"Perch ONNX has no embedding output: {outputs}")
        self.output_name = "embedding"
        self.batch_size = batch_size
        probe = self.session.run([self.output_name], {self.input_name: np.zeros((1, WINDOW_SAMPLES), np.float32)})[0]
        self.dim = int(probe.shape[-1])

    def embed(self, batch: np.ndarray) -> np.ndarray:
        batch = np.asarray(batch, dtype=np.float32)
        if batch.ndim != 2 or batch.shape[1] != WINDOW_SAMPLES:
            raise ValueError(f"expected (N, {WINDOW_SAMPLES}), got {batch.shape}")
        chunks = []
        for start in range(0, batch.shape[0], self.batch_size):
            part = batch[start : start + self.batch_size]
            emb = self.session.run([self.output_name], {self.input_name: part})[0]
            chunks.append(np.asarray(emb, dtype=np.float32))
        return np.concatenate(chunks, axis=0)


class ConcatEmbedder:
    def __init__(self, parts: list) -> None:
        if not parts:
            raise ValueError("need at least one embedder")
        self.parts = parts
        self.name = "+".join(p.name for p in parts)
        self.dim = sum(int(p.dim) for p in parts)

    def embed(self, batch: np.ndarray) -> np.ndarray:
        return np.concatenate([p.embed(batch) for p in self.parts], axis=1)


class SurfPerchTFEmbedder:
    """Optional SurfPerch loader. Requires TensorFlow and a SavedModel directory.

    The Zenodo v1 bundle (record 11060189) is about 128 MB and exports a
    TensorFlow SavedModel that consumes 5 s at 32 kHz and returns a 1280-d
    embedding. This class is untested in the default CPU run because
    TensorFlow is not installed there.
    """

    name = "surfperch_v1"

    def __init__(self, saved_model_dir: str | Path) -> None:
        import tensorflow as tf

        self.model = tf.saved_model.load(str(saved_model_dir))
        self.infer = self.model.signatures["serving_default"]
        self.dim = 1280

    def embed(self, batch: np.ndarray) -> np.ndarray:
        import tensorflow as tf

        batch = np.asarray(batch, dtype=np.float32)
        out = self.infer(inputs=tf.constant(batch))
        if "embedding" not in out:
            raise RuntimeError(f"SurfPerch signature outputs {list(out)} have no embedding")
        return np.asarray(out["embedding"].numpy(), dtype=np.float32)
