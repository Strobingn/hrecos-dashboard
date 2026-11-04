"""Manifest and embedding-matrix helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from hrecos_ml.audio import load_audio
from hrecos_ml.labels import WINDOW_SAMPLES, WINDOW_S


def read_manifest(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_manifest(path: str | Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _window_for_row(row: dict) -> np.ndarray:
    audio, sr = load_audio(row["path"])
    if audio.size == 0:
        return np.zeros(WINDOW_SAMPLES, dtype=np.float32)
    # Use a single 5 s window. Field clips shorter than 5 s are zero-padded.
    # Longer clips contribute their first window here; event detection uses hop.
    from hrecos_ml.audio import resample

    y = resample(audio, sr)
    if y.size >= WINDOW_SAMPLES:
        # Center the window so a short call in the middle of a file is kept.
        if y.size > WINDOW_SAMPLES and row.get("source") != "synthetic":
            start = max(0, (y.size - WINDOW_SAMPLES) // 2)
            y = y[start : start + WINDOW_SAMPLES]
        else:
            y = y[:WINDOW_SAMPLES]
    else:
        pad = np.zeros(WINDOW_SAMPLES, dtype=np.float32)
        pad[: y.size] = y
        y = pad
    return np.ascontiguousarray(y, dtype=np.float32)


def embed_manifest(rows: list[dict], embedders: dict, cache_path: str | Path | None = None) -> dict:
    """Embed each manifest row once per embedder.

    Returns arrays ``windows`` [N, 160000], plus one feature matrix per embedder
    name, and parallel ``labels`` / ``paths`` / ``sources``.
    """
    cache_path = Path(cache_path) if cache_path else None
    if cache_path and cache_path.is_file():
        with np.load(cache_path, allow_pickle=False) as data:
            loaded = {key: data[key] for key in data.files}
        if loaded["paths"].shape[0] == len(rows) and list(loaded["paths"]) == [r["path"] for r in rows]:
            return loaded

    windows = np.stack([_window_for_row(row) for row in rows], axis=0)
    out: dict = {
        "windows": windows.astype(np.float32),
        "labels": np.asarray([row["label"] for row in rows]),
        "paths": np.asarray([row["path"] for row in rows]),
        "sources": np.asarray([row.get("source", "") for row in rows]),
        "splits": np.asarray([row.get("split", "") for row in rows]),
    }
    for name, embedder in embedders.items():
        out[name] = embedder.embed(windows).astype(np.float32)
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache_path, **out)
    return out


def rows_for_duration(rows: list[dict]) -> list[dict]:
    """Annotate rows with duration. Synthetic rows already carry it."""
    for row in rows:
        row.setdefault("duration_s", WINDOW_S)
    return rows
