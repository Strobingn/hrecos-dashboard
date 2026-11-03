"""Audio sources that all yield mono float32 chunks at the node sample rate.

folder  local WAV/FLAC files, played as one continuous stream
noaa    anonymous reads from gs://noaa-passive-bioacoustic/
synth   procedural river audio with optional fish calls
device  Aquarian H2a via the Pi's USB sound card (sounddevice)
"""

from __future__ import annotations

import logging
import wave
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

import numpy as np
import requests
from scipy.signal import resample_poly

from hydrophone_node.audio.synthesize import render_interval
from hydrophone_node.audio.wavio import decode_pcm

logger = logging.getLogger(__name__)

AUDIO_SUFFIXES = {".wav", ".flac"}
NOAA_BUCKET = "noaa-passive-bioacoustic"
_GCD_CACHE: dict[tuple[int, int], tuple[int, int]] = {}


def resample_audio(
    samples: np.ndarray, source_rate: int, target_rate: int
) -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if samples.size == 0 or source_rate == target_rate:
        return samples
    key = (int(source_rate), int(target_rate))
    if key not in _GCD_CACHE:
        from math import gcd

        divisor = gcd(key[0], key[1])
        _GCD_CACHE[key] = (key[1] // divisor, key[0] // divisor)
    up, down = _GCD_CACHE[key]
    converted = resample_poly(samples, up, down).astype(np.float32)
    return converted


def iter_wav_chunks(
    path: Path, target_rate: int, block_frames: int = 65536
) -> Iterator[np.ndarray]:
    with wave.open(str(path), "rb") as handle:
        source_rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        while True:
            raw = handle.readframes(block_frames)
            if not raw:
                break
            yield resample_audio(
                decode_pcm(raw, width, channels), source_rate, target_rate
            )


def iter_soundfile_chunks(
    path: Path, target_rate: int, block_frames: int = 65536
) -> Iterator[np.ndarray]:
    try:
        import soundfile as sf
    except ImportError as exc:
        raise RuntimeError(
            "Reading this file needs the soundfile package and libsndfile. "
            "They are installed in the node image; locally pip install soundfile."
        ) from exc
    with sf.SoundFile(str(path)) as handle:
        source_rate = int(handle.samplerate)
        while True:
            block = handle.read(block_frames, dtype="float32", always_2d=True)
            if len(block) == 0:
                break
            mono = block.mean(axis=1).astype(np.float32)
            yield resample_audio(mono, source_rate, target_rate)


def iter_audio_file(path: Path, target_rate: int) -> Iterator[np.ndarray]:
    suffix = path.suffix.lower()
    if suffix == ".wav":
        try:
            yield from iter_wav_chunks(path, target_rate)
            return
        except wave.Error:
            logger.info("stdlib wave could not read %s; trying soundfile", path)
    if suffix in AUDIO_SUFFIXES:
        yield from iter_soundfile_chunks(path, target_rate)
        return
    raise ValueError(f"unsupported audio file: {path}")


class AudioSource:
    """Base class. realtime sources are already clocked by the hardware."""

    realtime = False

    def __iter__(self) -> Iterator[np.ndarray]:
        raise NotImplementedError


class FolderSource(AudioSource):
    def __init__(
        self, path: str | Path, sample_rate: int, max_files: int | None = None
    ):
        self.path = Path(path)
        self.sample_rate = int(sample_rate)
        self.max_files = max_files

    def files(self) -> list[Path]:
        if not self.path.exists():
            raise FileNotFoundError(f"audio folder does not exist: {self.path}")
        found = [
            item
            for item in sorted(self.path.rglob("*"))
            if item.is_file() and item.suffix.lower() in AUDIO_SUFFIXES
        ]
        if self.max_files is not None:
            found = found[: self.max_files]
        if not found:
            raise FileNotFoundError(f"no WAV or FLAC files under {self.path}")
        return found

    def __iter__(self) -> Iterator[np.ndarray]:
        for path in self.files():
            logger.info("reading %s", path)
            yield from iter_audio_file(path, self.sample_rate)


def gcs_list_url(bucket: str) -> str:
    return f"https://storage.googleapis.com/storage/v1/b/{bucket}/o"


def gcs_media_url(bucket: str, object_name: str) -> str:
    return f"https://storage.googleapis.com/{bucket}/{quote(object_name, safe='/')}"


def audio_names_from_gcs_list(payload: dict) -> list[str]:
    names: list[str] = []
    for item in payload.get("items") or []:
        name = item.get("name") or ""
        suffix = Path(name).suffix.lower()
        if suffix in AUDIO_SUFFIXES:
            names.append(name)
    return names


class NoaaBucketSource(AudioSource):
    """Anonymous reader for gs://noaa-passive-bioacoustic/.

    The bucket is public (NOAA NCEI passive acoustic archive). Listing uses
    the GCS JSON API without credentials. Set source.prefix to a project or
    deployment (for example ``nrs/`` or ``sanctsound/``) and source.max_files
    so a node does not try to walk the entire archive.
    """

    def __init__(
        self,
        sample_rate: int,
        prefix: str = "",
        bucket: str = NOAA_BUCKET,
        max_files: int | None = 20,
        session: requests.Session | None = None,
        download_dir: str | Path | None = None,
    ):
        self.sample_rate = int(sample_rate)
        self.prefix = prefix
        self.bucket = bucket
        self.max_files = max_files
        self.session = session or requests.Session()
        self.download_dir = Path(download_dir) if download_dir else None

    def list_audio_objects(self) -> list[str]:
        names: list[str] = []
        page_token: str | None = None
        while True:
            params: dict[str, str | int] = {"prefix": self.prefix, "maxResults": 1000}
            if page_token:
                params["pageToken"] = page_token
            response = self.session.get(
                gcs_list_url(self.bucket), params=params, timeout=60
            )
            response.raise_for_status()
            payload = response.json()
            names.extend(audio_names_from_gcs_list(payload))
            if self.max_files is not None and len(names) >= self.max_files:
                return names[: self.max_files]
            page_token = payload.get("nextPageToken")
            if not page_token:
                return names

    def download(self, object_name: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = gcs_media_url(self.bucket, object_name)
        with self.session.get(url, stream=True, timeout=(15, 300)) as response:
            response.raise_for_status()
            with dest.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        return dest

    def __iter__(self) -> Iterator[np.ndarray]:
        import tempfile

        names = self.list_audio_objects()
        if not names:
            raise FileNotFoundError(
                f"no WAV/FLAC objects under gs://{self.bucket}/{self.prefix}"
            )
        root = self.download_dir
        temporary = None
        if root is None:
            temporary = tempfile.TemporaryDirectory(prefix="noaa-pad-")
            root = Path(temporary.name)
        try:
            for name in names:
                dest = root / Path(name).name
                logger.info("downloading gs://%s/%s", self.bucket, name)
                self.download(name, dest)
                yield from iter_audio_file(dest, self.sample_rate)
        finally:
            if temporary is not None:
                temporary.cleanup()


class SynthSource(AudioSource):
    def __init__(
        self,
        sample_rate: int,
        segment_seconds: float,
        seed: int = 1,
        duration_s: float | None = None,
        calls: bool = True,
        hum: bool = True,
        ambient_boat: bool = True,
    ):
        self.sample_rate = int(sample_rate)
        self.segment_seconds = float(segment_seconds)
        self.seed = int(seed)
        self.duration_s = duration_s
        self.calls = calls
        self.hum = hum
        self.ambient_boat = ambient_boat

    def __iter__(self) -> Iterator[np.ndarray]:
        t = 0.0
        while self.duration_s is None or t < self.duration_s - 1e-6:
            remaining = self.segment_seconds
            if self.duration_s is not None:
                remaining = min(remaining, self.duration_s - t)
            if remaining <= 0:
                break
            yield render_interval(
                t,
                t + remaining,
                self.sample_rate,
                self.segment_seconds,
                seed=self.seed,
                hum=self.hum,
                ambient_boat=self.ambient_boat,
                calls=self.calls,
            )
            t += remaining


class DeviceSource(AudioSource):
    """Live Aquarian H2a input on the Pi.

    The hydrophone is analog. On the Pi it is digitized by a USB audio
    interface; ``source.device`` is the sounddevice name or index
    (for example ``hw:1,0``). The virtual node does not use this class.
    """

    realtime = True

    def __init__(
        self,
        sample_rate: int,
        device: str | int | None = None,
        block_seconds: float = 1.0,
    ):
        self.sample_rate = int(sample_rate)
        self.device = device
        self.block_seconds = float(block_seconds)

    def __iter__(self) -> Iterator[np.ndarray]:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "Live hydrophone input needs the sounddevice package on the Pi "
                "(pip install sounddevice) and a USB audio interface for the Aquarian H2a."
            ) from exc
        block = max(1, int(self.sample_rate * self.block_seconds))
        with sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.sample_rate,
            dtype="float32",
            blocksize=block,
        ) as stream:
            while True:
                data, overflowed = stream.read(block)
                if overflowed:
                    logger.warning("audio input overflowed; the Pi is dropping samples")
                yield np.asarray(data[:, 0], dtype=np.float32).copy()


def open_source(config) -> AudioSource:
    kind = config.source.kind
    sample_rate = config.sample_rate_hz
    if kind == "folder":
        return FolderSource(
            config.source.path, sample_rate, max_files=config.source.max_files
        )
    if kind == "noaa":
        return NoaaBucketSource(
            sample_rate,
            prefix=config.source.prefix,
            bucket=config.source.bucket or NOAA_BUCKET,
            max_files=config.source.max_files,
        )
    if kind == "synth":
        return SynthSource(
            sample_rate,
            segment_seconds=config.segment_seconds,
            seed=config.source.seed,
            duration_s=config.source.duration_s,
            calls=config.source.calls,
            hum=config.source.hum,
            ambient_boat=config.source.ambient_boat,
        )
    if kind == "device":
        return DeviceSource(sample_rate, device=config.source.device)
    raise ValueError(f"unknown source.kind '{kind}'")
