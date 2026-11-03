"""
Tide predictions for the Hudson between Tappan Zee and Poughkeepsie.

Station ids, tide type, and reference stations come from data/stations.json.
Newburgh (8518935) is subordinate to The Battery (8518750). Beacon (8518934)
is a harmonic station and the fallback when a subordinate series is empty.
Times are UTC (NOAA time_zone=gmt).
"""

import math
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.registry import DEFAULT_TIDE_STATION, REGIONS, TIDE_STATIONS

NOAA_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NOAA_META_BASE = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"

_offsets_cache: Dict[str, Dict] = {}


def _fetch_offsets(station_id: str) -> Dict:
    if station_id in _offsets_cache:
        return _offsets_cache[station_id]
    try:
        resp = requests.get(
            f"{NOAA_META_BASE}/{station_id}/tidepredoffsets.json",
            timeout=15,
        )
        if resp.status_code == 200:
            _offsets_cache[station_id] = resp.json()
            return _offsets_cache[station_id]
    except Exception as e:
        print(f"Offset fetch failed for {station_id}: {e}")
    return {}


def _fetch_harmonic_predictions(
    station_id: str,
    hours: int,
    interval: str = "h",
) -> List[Dict]:
    now = datetime.utcnow()
    params = {
        "station": station_id,
        "product": "predictions",
        "begin_date": now.strftime("%Y%m%d %H:%M"),
        "end_date": (now + timedelta(hours=hours)).strftime("%Y%m%d %H:%M"),
        "datum": "mllw",
        "units": "english",
        "time_zone": "gmt",
        "interval": interval,
        "format": "json",
    }
    try:
        resp = requests.get(NOAA_API_BASE, params=params, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if "error" in data:
            return []
        return [
            {
                "time": datetime.strptime(p["t"], "%Y-%m-%d %H:%M"),
                "height": float(p["v"]),
                "type": p.get("type", "").lower() or "unknown",
            }
            for p in data.get("predictions", [])
        ]
    except Exception as e:
        print(f"Harmonic tide fetch failed ({station_id}): {e}")
        return []


def _fetch_reference_hilo(reference_id: str, hours: int) -> List[Dict]:
    now = datetime.utcnow()
    params = {
        "station": reference_id,
        "product": "predictions",
        "begin_date": now.strftime("%Y%m%d %H:%M"),
        "end_date": (now + timedelta(hours=hours)).strftime("%Y%m%d %H:%M"),
        "datum": "mllw",
        "units": "english",
        "time_zone": "gmt",
        "interval": "hilo",
        "format": "json",
    }
    try:
        resp = requests.get(NOAA_API_BASE, params=params, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if "error" in data:
            return []
        return [
            {
                "time": datetime.strptime(p["t"], "%Y-%m-%d %H:%M"),
                "height": float(p["v"]),
                "type": p.get("type", "").lower(),
            }
            for p in data.get("predictions", [])
        ]
    except Exception as e:
        print(f"Reference hilo fetch failed ({reference_id}): {e}")
        return []


def _apply_subordinate_offsets(hilo: List[Dict], offsets: Dict) -> List[Dict]:
    """Apply NOAA tidepredoffsets. heightAdjustedType R is a ratio; A is added feet."""
    mode = (offsets.get("heightAdjustedType") or "A").upper()
    adjusted = []
    for event in hilo:
        is_high = event["type"] == "h"
        time_off = offsets.get("timeOffsetHighTide" if is_high else "timeOffsetLowTide") or 0
        height_off = offsets.get("heightOffsetHighTide" if is_high else "heightOffsetLowTide")
        if height_off is None:
            height_off = 0
        if mode == "R":
            height = event["height"] * float(height_off)
        else:
            height = event["height"] + float(height_off)
        adjusted.append({
            "time": event["time"] + timedelta(minutes=float(time_off)),
            "height": round(height, 3),
            "type": event["type"],
        })
    return adjusted


def _interpolate_between_events(events: List[Dict], hours: int) -> List[Dict]:
    """Build a smooth tide curve from adjusted high/low events."""
    if len(events) < 2:
        return events

    now = datetime.utcnow()
    end = now + timedelta(hours=hours)
    step_minutes = 30
    curve: List[Dict] = []

    for i in range(int(hours * 60 / step_minutes) + 1):
        t = now + timedelta(minutes=i * step_minutes)
        if t > end:
            break

        prev_evt = events[0]
        next_evt = events[-1]
        for j in range(len(events) - 1):
            if events[j]["time"] <= t <= events[j + 1]["time"]:
                prev_evt = events[j]
                next_evt = events[j + 1]
                break
            if t < events[0]["time"]:
                prev_evt = events[0]
                next_evt = events[1] if len(events) > 1 else events[0]
                break

        span = (next_evt["time"] - prev_evt["time"]).total_seconds()
        mid = prev_evt["height"]
        if span <= 0:
            height = prev_evt["height"]
        else:
            phase = (t - prev_evt["time"]).total_seconds() / span
            mid = (prev_evt["height"] + next_evt["height"]) / 2
            amp = abs(prev_evt["height"] - next_evt["height"]) / 2
            direction = 1 if next_evt["height"] >= prev_evt["height"] else -1
            height = mid + direction * amp * math.sin(math.pi * (phase - 0.5))

        curve.append({
            "time": t,
            "height": round(height, 2),
            "type": "high" if height >= mid else "low",
        })

    return curve


def _fetch_subordinate_predictions(station_id: str, reference_id: str, hours: int) -> List[Dict]:
    offsets = _fetch_offsets(station_id)
    if not offsets:
        return []
    hilo = _fetch_reference_hilo(reference_id, hours + 24)
    if not hilo:
        return []
    adjusted = _apply_subordinate_offsets(hilo, offsets)
    return _interpolate_between_events(adjusted, hours)


def get_tide_station_key(region: Optional[str] = None) -> str:
    if region and region in REGIONS:
        return REGIONS[region].get("tide_station") or DEFAULT_TIDE_STATION
    return DEFAULT_TIDE_STATION


def get_tide_predictions(
    hours: int = 48,
    region: Optional[str] = None,
    station_key: Optional[str] = None,
) -> List[Dict]:
    key = station_key or get_tide_station_key(region)
    config = TIDE_STATIONS.get(key)
    if not config:
        return []

    if config["type"] == "harmonic":
        preds = _fetch_harmonic_predictions(config["id"], hours, interval="h")
    else:
        preds = _fetch_subordinate_predictions(
            config["id"],
            config.get("reference_id", "8518750"),
            hours,
        )

    if preds:
        return preds

    beacon = TIDE_STATIONS.get("beacon")
    if beacon and key != "beacon":
        return _fetch_harmonic_predictions(beacon["id"], hours, interval="h")
    return []


def get_current_tide(region: Optional[str] = None, station_key: Optional[str] = None) -> Dict:
    key = station_key or get_tide_station_key(region)
    config = TIDE_STATIONS.get(key, {})
    tides = get_tide_predictions(hours=12, region=region, station_key=key)
    now = datetime.utcnow()

    if not tides:
        return {
            "station_key": key,
            "station_id": config.get("id"),
            "station_name": config.get("name"),
            "region": region or "cornwall_on_hudson",
            "current_height": None,
            "current_type": None,
            "next_time": None,
            "next_type": None,
            "next_height": None,
            "error": "no predictions",
        }

    current = tides[0]
    for index, tide in enumerate(tides):
        if tide["time"] > now:
            current = tides[index - 1] if index > 0 else tide
            break

    next_tide = None
    for tide in tides:
        if tide["time"] > now:
            next_tide = tide
            break

    return {
        "station_key": key,
        "station_id": config.get("id"),
        "station_name": config.get("name"),
        "region": region or "cornwall_on_hudson",
        "current_height": current["height"],
        "current_type": current["type"],
        "next_time": next_tide["time"] if next_tide else None,
        "next_type": next_tide["type"] if next_tide else None,
        "next_height": next_tide["height"] if next_tide else None,
    }


def should_poll_data(region: Optional[str] = None) -> bool:
    current = get_current_tide(region=region)
    now = datetime.utcnow()

    if current["next_time"]:
        time_to_tide = (current["next_time"] - now).total_seconds() / 60
        if -30 <= time_to_tide <= 30:
            return True

    return now.minute < 10