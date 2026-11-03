"""YAML config with environment overrides.

Environment wins over the file when both are set:

- NODE_ID
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- HYDROPHONE_SOURCE          folder | noaa | synth | device
- HYDROPHONE_SOURCE_PATH     local folder, or NOAA object prefix
- SAMPLE_RATE_HZ
- REPLAY_SPEED
- NOAA_PREFIX
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from hydrophone_node.contract import (
    AUDIO_BUCKET,
    DEFAULT_HARDWARE,
    NODE_PRESETS,
    NODE_STATUSES,
)

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value):
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda match: os.environ.get(match.group(1), ""), value)
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    return value


@dataclass
class NodeConfig:
    id: str
    name: str
    lat: float
    lon: float
    river_mile: float
    hardware: str
    sample_rate_hz: int
    status: str = "simulated"


@dataclass
class SourceConfig:
    kind: str = "synth"
    path: str = ""
    prefix: str = ""
    bucket: str = "noaa-passive-bioacoustic"
    max_files: int | None = 20
    seed: int = 1
    duration_s: float | None = None
    calls: bool = True
    hum: bool = True
    ambient_boat: bool = True
    device: str | None = None


@dataclass
class SupabaseConfig:
    url: str = ""
    service_role_key: str = ""
    audio_bucket: str = AUDIO_BUCKET


@dataclass
class DetectorConfig:
    name: str = "band_energy"
    entrypoint: str | None = None


@dataclass
class AppConfig:
    node: NodeConfig
    source: SourceConfig = field(default_factory=SourceConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    segment_seconds: float = 60.0
    replay_speed: float = 1.0
    heartbeat_interval_s: float = 60.0
    calibration_offset_db: float = 0.0
    stream_start: str = "now"
    output_dir: str = "out"
    clip_pad_s: float = 0.15

    @property
    def sample_rate_hz(self) -> int:
        return int(self.node.sample_rate_hz)

    def stream_origin(self, now: datetime | None = None) -> datetime:
        if self.stream_start in ("", "now"):
            current = now or datetime.now(timezone.utc)
            if current.tzinfo is None:
                return current.replace(tzinfo=timezone.utc)
            return current.astimezone(timezone.utc)
        text = self.stream_start.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


def _as_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_optional_float(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _as_optional_int(value) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def load_config(path: str | Path) -> AppConfig:
    raw_text = Path(path).read_text(encoding="utf-8")
    document = yaml.safe_load(raw_text) or {}
    document = _expand_env(document)
    node_raw = dict(document.get("node") or {})
    source_raw = dict(document.get("source") or {})
    supabase_raw = dict(document.get("supabase") or {})
    detector_raw = dict(document.get("detector") or {})

    node_id = os.environ.get("NODE_ID") or node_raw.get("id") or "poughkeepsie"
    preset = NODE_PRESETS.get(node_id, {})
    status = str(node_raw.get("status") or "simulated")
    if status not in NODE_STATUSES:
        raise ValueError(f"node.status must be one of {NODE_STATUSES}")

    sample_rate = int(
        os.environ.get("SAMPLE_RATE_HZ") or node_raw.get("sample_rate_hz") or 48000
    )
    node = NodeConfig(
        id=str(node_id),
        name=str(node_raw.get("name") or preset.get("name") or node_id),
        lat=float(
            node_raw.get("lat")
            if node_raw.get("lat") not in (None, "")
            else preset.get("lat", 0.0)
        ),
        lon=float(
            node_raw.get("lon")
            if node_raw.get("lon") not in (None, "")
            else preset.get("lon", 0.0)
        ),
        river_mile=float(
            node_raw.get("river_mile")
            if node_raw.get("river_mile") not in (None, "")
            else preset.get("river_mile", 0.0)
        ),
        hardware=str(node_raw.get("hardware") or DEFAULT_HARDWARE),
        sample_rate_hz=sample_rate,
        status=status,
    )

    kind = os.environ.get("HYDROPHONE_SOURCE") or source_raw.get("kind") or "synth"
    source_path = (
        os.environ.get("HYDROPHONE_SOURCE_PATH") or source_raw.get("path") or ""
    )
    prefix = os.environ.get("NOAA_PREFIX") or source_raw.get("prefix") or ""
    if kind == "noaa" and source_path and not prefix:
        prefix = source_path
    max_files = source_raw.get("max_files", 20)
    source = SourceConfig(
        kind=str(kind),
        path=str(source_path),
        prefix=str(prefix),
        bucket=str(source_raw.get("bucket") or "noaa-passive-bioacoustic"),
        max_files=_as_optional_int(max_files),
        seed=int(source_raw.get("seed") or 1),
        duration_s=_as_optional_float(source_raw.get("duration_s")),
        calls=_as_bool(source_raw.get("calls"), True),
        hum=_as_bool(source_raw.get("hum"), True),
        ambient_boat=_as_bool(source_raw.get("ambient_boat"), True),
        device=source_raw.get("device"),
    )

    supabase = SupabaseConfig(
        url=str(os.environ.get("SUPABASE_URL") or supabase_raw.get("url") or ""),
        service_role_key=str(
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or supabase_raw.get("service_role_key")
            or ""
        ),
        audio_bucket=str(supabase_raw.get("audio_bucket") or AUDIO_BUCKET),
    )
    detector = DetectorConfig(
        name=str(detector_raw.get("name") or "band_energy"),
        entrypoint=detector_raw.get("entrypoint") or None,
    )
    replay = float(
        os.environ.get("REPLAY_SPEED") or document.get("replay_speed") or 1.0
    )
    if replay < 0:
        raise ValueError(
            "replay_speed must be >= 0 (0 means as fast as the machine can go)"
        )
    segment_seconds = float(document.get("segment_seconds") or 60)
    if segment_seconds <= 0:
        raise ValueError("segment_seconds must be positive")

    return AppConfig(
        node=node,
        source=source,
        supabase=supabase,
        detector=detector,
        segment_seconds=segment_seconds,
        replay_speed=replay,
        heartbeat_interval_s=float(document.get("heartbeat_interval_s") or 60),
        calibration_offset_db=float(document.get("calibration_offset_db") or 0.0),
        stream_start=str(document.get("stream_start") or "now"),
        output_dir=str(document.get("output_dir") or "out"),
        clip_pad_s=float(document.get("clip_pad_s") or 0.15),
    )
