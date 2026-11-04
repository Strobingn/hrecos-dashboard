"""YAML config with environment overrides.

Environment wins over the file when both are set:

- NODE_ID
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- SONAR_SOURCE          synth
- SONAR_RATE
- REPLAY_SPEED
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from sonar_node.contract import (
    DEFAULT_HARDWARE,
    NODE_PRESETS,
    NODE_STATUSES,
    SONAR_BUCKET,
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
    status: str = "simulated"


@dataclass
class SourceConfig:
    kind: str = "synth"
    seed: int = 1
    start: str = "2026-05-15T00:00:00Z"
    hours: float = 6.0
    rate: float = 1.0


@dataclass
class SupabaseConfig:
    url: str = ""
    service_role_key: str = ""
    sonar_bucket: str = SONAR_BUCKET


@dataclass
class ClassifierConfig:
    name: str = "rules"
    entrypoint: str | None = None


@dataclass
class AppConfig:
    node: NodeConfig
    source: SourceConfig = field(default_factory=SourceConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    classifier: ClassifierConfig = field(default_factory=ClassifierConfig)
    replay_speed: float = 0.0
    output_dir: str = "out"

    def window(self) -> tuple[datetime, datetime]:
        from datetime import timedelta

        start = _parse_time(self.source.start)
        return start, start + timedelta(hours=float(self.source.hours))


def _parse_time(text: str) -> datetime:
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_config(path: str | Path) -> AppConfig:
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    document = _expand_env(document)
    node_raw = dict(document.get("node") or {})
    source_raw = dict(document.get("source") or {})
    supabase_raw = dict(document.get("supabase") or {})
    classifier_raw = dict(document.get("classifier") or {})

    node_id = os.environ.get("NODE_ID") or node_raw.get("id") or "westpoint-cornwall"
    preset = NODE_PRESETS.get(str(node_id), {})
    status = str(node_raw.get("status") or "simulated")
    if status not in NODE_STATUSES:
        raise ValueError(f"node.status must be one of {NODE_STATUSES}")

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
        status=status,
    )

    kind = os.environ.get("SONAR_SOURCE") or source_raw.get("kind") or "synth"
    if str(kind) != "synth":
        raise ValueError(
            "source.kind must be 'synth'. A reader for real ARIS files is not in this package."
        )
    rate_raw = os.environ.get("SONAR_RATE")
    rate = float(rate_raw if rate_raw not in (None, "") else source_raw.get("rate") or 1.0)
    if rate < 0:
        raise ValueError("source.rate must be >= 0")
    source = SourceConfig(
        kind="synth",
        seed=int(source_raw.get("seed") or 1),
        start=str(source_raw.get("start") or "2026-05-15T00:00:00Z"),
        hours=float(source_raw.get("hours") or 6),
        rate=rate,
    )
    supabase = SupabaseConfig(
        url=str(os.environ.get("SUPABASE_URL") or supabase_raw.get("url") or ""),
        service_role_key=str(
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or supabase_raw.get("service_role_key")
            or ""
        ),
        sonar_bucket=str(supabase_raw.get("sonar_bucket") or SONAR_BUCKET),
    )
    classifier = ClassifierConfig(
        name=str(classifier_raw.get("name") or "rules"),
        entrypoint=classifier_raw.get("entrypoint") or None,
    )
    replay = float(os.environ.get("REPLAY_SPEED") or document.get("replay_speed") or 0.0)
    if replay < 0:
        raise ValueError("replay_speed must be >= 0")
    return AppConfig(
        node=node,
        source=source,
        supabase=supabase,
        classifier=classifier,
        replay_speed=replay,
        output_dir=str(document.get("output_dir") or "out"),
    )
