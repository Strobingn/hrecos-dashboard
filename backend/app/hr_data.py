import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List

import httpx
import requests

from app.registry import FOCUS_STATIONS, REGIONS, STATIONS

# ─────────────────────────────────────────────────────────────────────────────
# Data sources — HRECOS (NYS Mesonet) + USGS NWIS + NOAA CO-OPS + NOAA NDBC
# Station list: data/stations.json
# ─────────────────────────────────────────────────────────────────────────────

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"
NOAA_API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NDBC_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"
HRECOS_URL = (
    "https://nysm.hrecos.org/api/data/dynserv/hrecos/exportsite/csv/{sites}/{start}/{end}"
)

TEMP_FIELDS = {"temp", "air_temp", "dewpoint"}
WIND_FIELDS = {"wind_speed", "wind_gust"}
PRESS_FIELDS = {"pressure"}
DEPTH_FIELDS = {"depth"}
SENTINEL = -999999.0


def _c_to_f(celsius) -> Optional[float]:
    if celsius is None:
        return None
    return round(celsius * 9 / 5 + 32, 2)


def _ms_to_mph(meters_per_second) -> Optional[float]:
    if meters_per_second is None:
        return None
    return round(meters_per_second * 2.23694, 2)


def _hpa_to_inhg(hectopascals) -> Optional[float]:
    if hectopascals is None:
        return None
    return round(hectopascals * 0.02953, 3)


def _m_to_ft(meters) -> Optional[float]:
    if meters is None:
        return None
    return round(meters * 3.28084, 3)


def _to_imperial(reading: Dict) -> Dict:
    """Convert metric sensor values to the imperial units the API already publishes."""
    for field in TEMP_FIELDS:
        if field in reading:
            reading[field] = _c_to_f(reading[field])
    for field in WIND_FIELDS:
        if field in reading:
            reading[field] = _ms_to_mph(reading[field])
    for field in PRESS_FIELDS:
        if field in reading:
            reading[field] = _hpa_to_inhg(reading[field])
    for field in DEPTH_FIELDS:
        if field in reading:
            reading[field] = _m_to_ft(reading[field])
    return reading


def _codes(station_config: Dict) -> List[str]:
    seen = []
    for param in station_config.get("parameters") or []:
        code = param["code"]
        if code not in seen:
            seen.append(code)
    return seen


def _fields_for_code(station_config: Dict, code: str) -> List[str]:
    return [
        param["field"]
        for param in station_config.get("parameters") or []
        if param["code"] == code
    ]


def stations_for_region(region: Optional[str] = None) -> Dict:
    """Live observation stations, optionally limited to a named region."""
    def live_obs(keys):
        return {
            key: STATIONS[key]
            for key in keys
            if key in STATIONS
            and STATIONS[key].get("live")
            and STATIONS[key].get("kind") == "observation"
        }

    if not region or region == "all":
        return live_obs(FOCUS_STATIONS)
    info = REGIONS.get(region)
    if not info:
        return live_obs(FOCUS_STATIONS)
    return live_obs(info["stations"])


def _float_or_none(raw) -> Optional[float]:
    if raw in (None, "", "MM"):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value == SENTINEL:
        return None
    return value


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


# ─────────────────────────────────────────────────────────────────────────────
# HRECOS (NYS Mesonet CSV)
# ─────────────────────────────────────────────────────────────────────────────

def _hrecos_stamp(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M")


def _parse_hrecos_time(value: str) -> datetime:
    return datetime.strptime(value[:15], "%Y%m%dT%H%M%S")


def _hrecos_code(header: str) -> str:
    return header.split()[0].strip().lower()


def _parse_hrecos_csv(text: str) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        normalized = {_hrecos_code(key): value for key, value in row.items() if key}
        grouped.setdefault(normalized.get("station", ""), []).append(normalized)
    return grouped


def _reading_from_hrecos_rows(station_config: Dict, rows: List[Dict]) -> Optional[Dict]:
    reading: Dict = {}
    latest_time = None
    for param in station_config.get("parameters") or []:
        code = param["code"].lower()
        field = param["field"]
        for row in reversed(rows):
            value = _float_or_none(row.get(code))
            if value is None:
                continue
            stamp = row.get("datetime")
            if stamp:
                parsed = _parse_hrecos_time(stamp)
                if latest_time is None or parsed > latest_time:
                    latest_time = parsed
            reading[field] = round(value, 3)
            break
    if not reading:
        return None
    reading["timestamp"] = latest_time or datetime.utcnow()
    return _to_imperial(reading)


def _fetch_hrecos_sync(stations: Dict[str, Dict], hours: int = 3) -> Dict[str, Dict]:
    if not stations:
        return {}
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    codes = sorted({code for config in stations.values() for code in _codes(config)})
    url = HRECOS_URL.format(
        sites=",".join(config["id"] for config in stations.values()),
        start=_hrecos_stamp(start),
        end=_hrecos_stamp(end),
    )
    try:
        response = requests.get(
            url,
            params={"timezone": "UTC", "variables": ",".join(codes)},
            timeout=60,
        )
    except requests.RequestException as exc:
        print(f"HRECOS fetch failed: {exc}")
        return {}
    if response.status_code != 200:
        print(f"HRECOS fetch HTTP {response.status_code}")
        return {}
    grouped = _parse_hrecos_csv(response.text)
    results = {}
    for key, config in stations.items():
        reading = _reading_from_hrecos_rows(config, grouped.get(config["id"], []))
        if reading:
            results[key] = reading
    return results


async def _fetch_hrecos_async(stations: Dict[str, Dict], hours: int = 3) -> Dict[str, Dict]:
    if not stations:
        return {}
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    codes = sorted({code for config in stations.values() for code in _codes(config)})
    url = HRECOS_URL.format(
        sites=",".join(config["id"] for config in stations.values()),
        start=_hrecos_stamp(start),
        end=_hrecos_stamp(end),
    )
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                url, params={"timezone": "UTC", "variables": ",".join(codes)}
            )
    except httpx.HTTPError as exc:
        print(f"HRECOS async fetch failed: {exc}")
        return {}
    if response.status_code != 200:
        print(f"HRECOS async fetch HTTP {response.status_code}")
        return {}
    grouped = _parse_hrecos_csv(response.text)
    results = {}
    for key, config in stations.items():
        reading = _reading_from_hrecos_rows(config, grouped.get(config["id"], []))
        if reading:
            results[key] = reading
    return results


# ─────────────────────────────────────────────────────────────────────────────
# USGS
# ─────────────────────────────────────────────────────────────────────────────

def _parse_usgs_response(data: dict, wanted: Dict[str, str]) -> Optional[Dict]:
    series = data.get("value", {}).get("timeSeries", [])
    if not series:
        return None
    reading: Dict = {}
    latest_time = None
    for item in series:
        code = item["variable"]["variableCode"][0]["value"]
        field = wanted.get(code)
        if not field:
            continue
        values = item["values"][0]["value"]
        if not values:
            continue
        latest = values[-1]
        value = _float_or_none(latest.get("value"))
        if value is None:
            continue
        try:
            parsed = datetime.fromisoformat(latest["dateTime"].replace("Z", "+00:00"))
            parsed = _naive_utc(parsed)
            if latest_time is None or parsed > latest_time:
                latest_time = parsed
        except (TypeError, ValueError):
            pass
        reading[field] = round(value, 3)
    if not reading:
        return None
    reading["timestamp"] = latest_time or datetime.utcnow()
    return _to_imperial(reading)


def _usgs_wanted(station_config: Dict) -> Dict[str, str]:
    wanted = {}
    for param in station_config.get("parameters") or []:
        wanted[param["code"]] = param["field"]
    return wanted


def _fetch_usgs_sync(station_config: Dict) -> Optional[Dict]:
    wanted = _usgs_wanted(station_config)
    if not wanted:
        return None
    try:
        response = requests.get(USGS_IV_URL, params={
            "format": "json",
            "sites": station_config["id"],
            "parameterCd": ",".join(wanted),
            "siteStatus": "all",
        }, timeout=30)
        if response.status_code == 200:
            return _parse_usgs_response(response.json(), wanted)
    except requests.RequestException as exc:
        print(f"USGS sync fetch failed ({station_config['id']}): {exc}")
    return None


async def _fetch_usgs_async(station_config: Dict) -> Optional[Dict]:
    wanted = _usgs_wanted(station_config)
    if not wanted:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(USGS_IV_URL, params={
                "format": "json",
                "sites": station_config["id"],
                "parameterCd": ",".join(wanted),
                "siteStatus": "all",
            })
            if response.status_code == 200:
                return _parse_usgs_response(response.json(), wanted)
    except httpx.HTTPError as exc:
        print(f"USGS async fetch failed ({station_config['id']}): {exc}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# NOAA CO-OPS observations
# ─────────────────────────────────────────────────────────────────────────────

def _apply_noaa_row(reading: Dict, product: str, fields: List[str], row: Dict) -> None:
    try:
        reading["timestamp"] = datetime.strptime(row["t"], "%Y-%m-%d %H:%M")
    except (KeyError, ValueError):
        pass
    if product == "wind":
        mapping = {"wind_speed": "s", "wind_direction": "d", "wind_gust": "g"}
        for field in fields:
            reading[field] = _float_or_none(row.get(mapping.get(field, "s")))
        return
    if product == "salinity":
        raw = row.get("s", row.get("v"))
    else:
        raw = row.get("v")
    value = _float_or_none(raw)
    if product == "conductivity" and value is not None:
        # CO-OPS metric conductivity is millisiemens/cm. The rest of the API uses µS/cm.
        value = round(value * 1000, 3)
    if product == "water_level" and value is not None:
        value = _m_to_ft(value)
    for field in fields:
        reading[field] = value


def _fetch_noaa_sync(station_config: Dict) -> Optional[Dict]:
    reading: Dict = {}
    for code in _codes(station_config):
        try:
            response = requests.get(NOAA_API_URL, params={
                "station": station_config["id"],
                "product": code,
                "date": "latest",
                "datum": "MLLW",
                "units": "metric",
                "time_zone": "gmt",
                "format": "json",
            }, timeout=20)
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue
        payload = response.json()
        if payload.get("error"):
            continue
        data = payload.get("data") or []
        if not data:
            continue
        _apply_noaa_row(reading, code, _fields_for_code(station_config, code), data[0])
    if len(reading) <= (1 if "timestamp" in reading else 0):
        return None
    return _to_imperial(reading)


async def _fetch_noaa_async(station_config: Dict) -> Optional[Dict]:
    reading: Dict = {}
    async with httpx.AsyncClient(timeout=20.0) as client:
        for code in _codes(station_config):
            try:
                response = await client.get(NOAA_API_URL, params={
                    "station": station_config["id"],
                    "product": code,
                    "date": "latest",
                    "datum": "MLLW",
                    "units": "metric",
                    "time_zone": "gmt",
                    "format": "json",
                })
            except httpx.HTTPError:
                continue
            if response.status_code != 200:
                continue
            payload = response.json()
            if payload.get("error"):
                continue
            data = payload.get("data") or []
            if not data:
                continue
            _apply_noaa_row(reading, code, _fields_for_code(station_config, code), data[0])
    if len(reading) <= (1 if "timestamp" in reading else 0):
        return None
    return _to_imperial(reading)


# ─────────────────────────────────────────────────────────────────────────────
# NDBC
# ─────────────────────────────────────────────────────────────────────────────

def _parse_ndbc_text(text: str, station_config: Dict) -> Optional[Dict]:
    lines = text.strip().splitlines()
    if len(lines) < 3:
        return None
    headers = lines[0].lstrip("#").split()
    latest = lines[2].split()
    if len(latest) < len(headers):
        return None
    row = dict(zip(headers, latest))
    try:
        timestamp = datetime(
            int(row["YY"]), int(row["MM"]), int(row["DD"]), int(row["hh"]), int(row["mm"])
        )
    except (KeyError, ValueError):
        timestamp = datetime.utcnow()
    wanted = {param["code"]: param["field"] for param in station_config.get("parameters") or []}
    reading = {"timestamp": timestamp}
    for code, field in wanted.items():
        reading[field] = _float_or_none(row.get(code))
    if all(reading.get(field) is None for field in wanted.values()):
        return None
    return _to_imperial(reading)


def _fetch_ndbc_sync(station_config: Dict) -> Optional[Dict]:
    try:
        response = requests.get(NDBC_URL.format(station=station_config["id"].upper()), timeout=20)
        if response.status_code == 200:
            return _parse_ndbc_text(response.text, station_config)
    except requests.RequestException as exc:
        print(f"NDBC sync fetch failed ({station_config['id']}): {exc}")
    return None


async def _fetch_ndbc_async(station_config: Dict) -> Optional[Dict]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(NDBC_URL.format(station=station_config["id"].upper()))
            if response.status_code == 200:
                return _parse_ndbc_text(response.text, station_config)
    except httpx.HTTPError as exc:
        print(f"NDBC async fetch failed ({station_config['id']}): {exc}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Tide predictions (delegates to app.tides)
# ─────────────────────────────────────────────────────────────────────────────

def _prediction_reading(station_key: str, station_config: Dict) -> Optional[Dict]:
    from app.tides import get_tide_predictions

    predictions = get_tide_predictions(hours=18, station_key=station_key)
    if not predictions:
        return None
    now = datetime.utcnow()
    chosen = predictions[0]
    for item in predictions:
        if item["time"] >= now:
            chosen = item
            break
    return {
        "timestamp": chosen["time"],
        "tide_prediction": chosen["height"],
        "tide_type": chosen.get("type"),
        "station_id": station_config["id"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

def _route_sync(station_key: str, station_config: Dict) -> Optional[Dict]:
    if station_config.get("kind") == "prediction":
        return _prediction_reading(station_key, station_config)
    source = station_config["source"]
    if source == "hrecos":
        return _fetch_hrecos_sync({station_key: station_config}).get(station_key)
    if source == "noaa":
        return _fetch_noaa_sync(station_config)
    if source == "ndbc":
        return _fetch_ndbc_sync(station_config)
    if source == "usgs":
        return _fetch_usgs_sync(station_config)
    return None


async def _route_async(station_key: str, station_config: Dict) -> Optional[Dict]:
    if station_config.get("kind") == "prediction":
        return _prediction_reading(station_key, station_config)
    source = station_config["source"]
    if source == "hrecos":
        fetched = await _fetch_hrecos_async({station_key: station_config})
        return fetched.get(station_key)
    if source == "noaa":
        return await _fetch_noaa_async(station_config)
    if source == "ndbc":
        return await _fetch_ndbc_async(station_config)
    if source == "usgs":
        return await _fetch_usgs_async(station_config)
    return None


async def fetch_station_async(station_key: str, station_config: Dict) -> Optional[Dict]:
    try:
        return await _route_async(station_key, station_config)
    except Exception as exc:
        print(f"fetch_station_async failed for {station_key}: {exc}")
        return None


def fetch_station_sync(station_key: str, station_config: Dict) -> Optional[Dict]:
    try:
        return _route_sync(station_key, station_config)
    except Exception as exc:
        print(f"fetch_station_sync failed for {station_key}: {exc}")
        return None


async def fetch_all_stations(region: Optional[str] = None) -> Dict[str, Dict]:
    pool = stations_for_region(region)
    results: Dict[str, Dict] = {}
    hrecos = {key: config for key, config in pool.items() if config["source"] == "hrecos"}
    if hrecos:
        results.update(await _fetch_hrecos_async(hrecos))
    for key, config in pool.items():
        if key in hrecos:
            continue
        data = await fetch_station_async(key, config)
        if data:
            results[key] = data
    return results


def _historical_hrecos(station_key: str, config: Dict, hours: int) -> List[Dict]:
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    codes = _codes(config)
    url = HRECOS_URL.format(
        sites=config["id"],
        start=_hrecos_stamp(start),
        end=_hrecos_stamp(end),
    )
    try:
        response = requests.get(
            url,
            params={"timezone": "UTC", "variables": ",".join(codes)},
            timeout=60,
        )
    except requests.RequestException as exc:
        print(f"HRECOS history failed ({station_key}): {exc}")
        return []
    if response.status_code != 200:
        return []
    rows = _parse_hrecos_csv(response.text).get(config["id"], [])
    series = []
    for row in rows:
        reading = _reading_from_hrecos_rows(config, [row])
        if not reading:
            continue
        reading["timestamp"] = reading["timestamp"].isoformat()
        series.append(reading)
    series.sort(key=lambda item: item["timestamp"], reverse=True)
    return series


def _historical_usgs(station_key: str, config: Dict, hours: int) -> List[Dict]:
    wanted = _usgs_wanted(config)
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    try:
        response = requests.get(USGS_IV_URL, params={
            "format": "json",
            "sites": config["id"],
            "parameterCd": ",".join(wanted),
            "startDT": start.strftime("%Y-%m-%dT%H:%M+00:00"),
            "endDT": end.strftime("%Y-%m-%dT%H:%M+00:00"),
        }, timeout=30)
    except requests.RequestException as exc:
        print(f"Historical fetch failed for {station_key}: {exc}")
        return []
    if response.status_code != 200:
        return []
    merged: Dict[str, Dict] = {}
    for item in response.json().get("value", {}).get("timeSeries", []):
        code = item["variable"]["variableCode"][0]["value"]
        field = wanted.get(code)
        if not field:
            continue
        for value in item["values"][0]["value"]:
            stamp = value["dateTime"]
            merged.setdefault(stamp, {"timestamp": stamp})
            number = _float_or_none(value.get("value"))
            merged[stamp][field] = None if number is None else round(number, 3)
    rows = []
    for row in merged.values():
        _to_imperial(row)
        rows.append(row)
    return sorted(rows, key=lambda item: item["timestamp"], reverse=True)


def _historical_noaa(config: Dict, hours: int) -> List[Dict]:
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    merged: Dict[str, Dict] = {}
    for code in _codes(config):
        try:
            response = requests.get(NOAA_API_URL, params={
                "station": config["id"],
                "product": code,
                "begin_date": start.strftime("%Y%m%d %H:%M"),
                "end_date": end.strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "units": "metric",
                "time_zone": "gmt",
                "format": "json",
            }, timeout=30)
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue
        payload = response.json()
        if payload.get("error"):
            continue
        for row in payload.get("data") or []:
            stamp = row.get("t")
            if not stamp:
                continue
            bucket = merged.setdefault(stamp, {"timestamp": stamp})
            _apply_noaa_row(bucket, code, _fields_for_code(config, code), row)
            bucket["timestamp"] = stamp
    rows = []
    for row in merged.values():
        _to_imperial(row)
        rows.append(row)
    return sorted(rows, key=lambda item: item["timestamp"], reverse=True)


def fetch_historical_data(station_key: str, hours: int = 24) -> List[Dict]:
    config = STATIONS.get(station_key)
    if not config or not config.get("live") or config.get("kind") != "observation":
        return []
    source = config["source"]
    if source == "hrecos":
        return _historical_hrecos(station_key, config, hours)
    if source == "usgs":
        return _historical_usgs(station_key, config, hours)
    if source == "noaa":
        return _historical_noaa(config, hours)
    if source == "ndbc":
        reading = _fetch_ndbc_sync(config)
        if not reading:
            return []
        reading["timestamp"] = reading["timestamp"].isoformat()
        return [reading]
    return []


def generate_mock_data(station_id: str) -> Dict:
    """Kept so older callers import. Live fetches do not use it."""
    import random
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "temp": round((10.0 + random.gauss(0, 2)) * 9 / 5 + 32, 2),
        "flow": round(max(0, 500 + random.gauss(0, 100)), 2),
        "turbidity": round(max(0, 10 + random.gauss(0, 3)), 2),
        "dissolved_oxygen": round(random.uniform(7.0, 12.0), 2),
        "ph": round(random.uniform(6.8, 8.2), 2),
        "conductance": round(random.uniform(150, 300), 1),
        "salinity": round(random.uniform(0.0, 1.5), 3),
        "station_id": station_id,
    }
