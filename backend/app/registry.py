"""Load the shared Hudson River station registry.

The file at data/stations.json is the source of truth for the backend and for
frontends that can fetch it (GitHub Pages at /data/stations.json, the mobile
app via mobile/src/data/stations.json).
"""

import json
from pathlib import Path
from typing import Dict, List

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "stations.json"


def load_registry(path: Path = REGISTRY_PATH) -> Dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _as_station(raw: Dict) -> Dict:
    station = dict(raw)
    station["source"] = raw["provider"]
    station["params"] = [item["field"] for item in raw.get("parameters") or []]
    station["region"] = "focus" if raw.get("focus") else "out_of_focus"
    return station


REGISTRY = load_registry()
STATIONS: Dict[str, Dict] = {
    item["key"]: _as_station(item) for item in REGISTRY["stations"]
}

# Live water-quality / met observations inside the Tappan Zee–Poughkeepsie reach.
# Tide-prediction stations are in the registry but are not polled as sensor data.
FOCUS_STATIONS: List[str] = [
    key
    for key, station in STATIONS.items()
    if station.get("focus") and station.get("live") and station.get("kind") == "observation"
]

FOCUS_STATION_KEYS: List[str] = [
    key for key, station in STATIONS.items() if station.get("focus")
]

LIVE_STATIONS: Dict[str, Dict] = {
    key: station for key, station in STATIONS.items() if station.get("live")
}

TIDE_STATIONS: Dict[str, Dict] = {}
for key, station in STATIONS.items():
    if station.get("provider") == "noaa" and station.get("kind") == "prediction":
        TIDE_STATIONS[key] = {
            "id": station["id"],
            "name": station["name"],
            "lat": station["lat"],
            "lon": station["lon"],
            "type": station.get("tide_type", "harmonic"),
            "reference_id": station.get("reference_id") or "8518750",
            "note": station.get("note"),
        }

DEFAULT_TIDE_STATION = "newburgh"

REGIONS = {
    "cornwall_on_hudson": {
        "name": "Cornwall-on-Hudson, NY",
        "center": {"lat": 41.4426, "lon": -74.0155},
        "stations": list(FOCUS_STATIONS),
        "tide_station": DEFAULT_TIDE_STATION,
        "description": (
            "Hudson River at West Point (river mile ~52) and Cornwall-on-Hudson "
            "(river mile ~56). Live water quality is HRECOS at Piermont, West Point, "
            "and Poughkeepsie. Tide reference is NOAA 8518935 Newburgh."
        ),
    }
}
REGIONS["cornwall"] = REGIONS["cornwall_on_hudson"]
