"""Pick a sonar node from the nearest station in data/stations.json.

Station keys (west_point, piermont, poughkeepsie) are gauge and HRECOS ids.
sonar_tracks.node_id has to be a sonar_nodes id (westpoint-cornwall,
poughkeepsie, tappan-zee). The importer takes the nearest station, then the
seeded sonar site nearest that station, and records the station key on the
row. --node overrides the site. A fix tens of kilometres from every station
is refused unless --node is set, so a log from outside the river is not
silently pinned to Albany or Piermont.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from sonar_node.contract import NODE_PRESETS

MAX_STATION_DISTANCE_M = 30_000.0


@dataclass(frozen=True)
class Station:
    key: str
    name: str
    lat: float
    lon: float
    distance_m: float


@dataclass(frozen=True)
class NodeChoice:
    node_id: str
    station: Station
    node_distance_m: float


def load_stations(path: Path) -> list[dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    stations = document.get("stations") if isinstance(document, dict) else None
    if not isinstance(stations, list) or not stations:
        raise ValueError(f"{path} has no stations list")
    return stations


def find_stations_file(explicit: Path | None, start: Path | None = None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise FileNotFoundError(f"stations file not found: {explicit}")
        return explicit
    roots = []
    if start is not None:
        roots.append(start)
    roots.append(Path.cwd())
    roots.append(Path(__file__).resolve())
    seen: set[Path] = set()
    for root in roots:
        current = root if root.is_dir() else root.parent
        for candidate in (current, *current.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            path = candidate / "data" / "stations.json"
            if path.is_file():
                return path
    raise FileNotFoundError(
        "data/stations.json was not found. Pass --stations, or run from the repo."
    )


def choose_node(
    latitude: float,
    longitude: float,
    stations: list[dict],
    override: str | None = None,
) -> NodeChoice:
    nearest = _nearest_station(latitude, longitude, stations)
    if override:
        if override not in NODE_PRESETS:
            known = ", ".join(sorted(NODE_PRESETS))
            raise ValueError(f"--node {override} is not a sonar site ({known})")
        node_id = override
    else:
        if nearest.distance_m > MAX_STATION_DISTANCE_M:
            raise ValueError(
                f"nearest station {nearest.key} is {nearest.distance_m / 1000:.0f} km "
                "from the log. Pass --node to pin the site. A down-looking log is "
                "not assigned to a Hudson station it was not recorded next to."
            )
        node_id = _nearest_preset(nearest.lat, nearest.lon)
    preset = NODE_PRESETS[node_id]
    return NodeChoice(
        node_id=node_id,
        station=nearest,
        node_distance_m=_haversine_m(nearest.lat, nearest.lon, preset["lat"], preset["lon"]),
    )


def _nearest_station(latitude: float, longitude: float, stations: list[dict]) -> Station:
    best: Station | None = None
    for raw in stations:
        if "lat" not in raw or "lon" not in raw or "key" not in raw:
            continue
        distance = _haversine_m(latitude, longitude, float(raw["lat"]), float(raw["lon"]))
        if best is None or distance < best.distance_m:
            best = Station(
                key=str(raw["key"]),
                name=str(raw.get("name") or raw["key"]),
                lat=float(raw["lat"]),
                lon=float(raw["lon"]),
                distance_m=distance,
            )
    if best is None:
        raise ValueError("stations file has no lat/lon rows")
    return best


def _nearest_preset(latitude: float, longitude: float) -> str:
    return min(
        NODE_PRESETS,
        key=lambda node_id: _haversine_m(
            latitude,
            longitude,
            NODE_PRESETS[node_id]["lat"],
            NODE_PRESETS[node_id]["lon"],
        ),
    )


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))
