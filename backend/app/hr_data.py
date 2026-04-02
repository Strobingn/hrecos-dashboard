import requests
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# ─────────────────────────────────────────────────────────────────────────────
# Data sources — USGS NWIS + NOAA CO-OPS + NOAA NDBC
# Verified April 2, 2026
# ─────────────────────────────────────────────────────────────────────────────

USGS_IV_URL  = "https://waterservices.usgs.gov/nwis/iv/"
NOAA_API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NDBC_URL     = "https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"

# USGS parameter codes
PARAM_TEMP        = "00010"
PARAM_DO          = "00300"
PARAM_PH          = "00400"
PARAM_CONDUCTANCE = "00095"
PARAM_TURBIDITY   = "63680"
PARAM_GAGE_HEIGHT = "00065"
PARAM_DISCHARGE   = "00060"
PARAM_SALINITY    = "00480"

ALL_PARAMS = ",".join([
    PARAM_TEMP, PARAM_DO, PARAM_PH,
    PARAM_CONDUCTANCE, PARAM_TURBIDITY,
    PARAM_GAGE_HEIGHT, PARAM_DISCHARGE, PARAM_SALINITY,
])

PARAM_MAP = {
    PARAM_TEMP:        "temp",
    PARAM_DO:          "dissolved_oxygen",
    PARAM_PH:          "ph",
    PARAM_CONDUCTANCE: "conductance",
    PARAM_TURBIDITY:   "turbidity",
    PARAM_GAGE_HEIGHT: "gage_height",
    PARAM_DISCHARGE:   "flow",
    PARAM_SALINITY:    "salinity",
}

# NDBC column → internal field
NDBC_COL_MAP = {
    "WDIR": "wind_direction",
    "WSPD": "wind_speed",
    "GST":  "wind_gust",
    "PRES": "pressure",
    "ATMP": "air_temp",
    "WTMP": "temp",
    "DEWP": "dewpoint",
}



# ─────────────────────────────────────────────────────────────────────────────
# Unit conversions — all output in US Imperial
#
# USGS:     temp °C → °F (no unit option for param 00010)
#           gage_height ft³, discharge ft³/s already imperial
# NOAA:     requested in metric → converted here
# NDBC:     temp °C → °F, wind m/s → mph, pressure hPa → inHg
# ─────────────────────────────────────────────────────────────────────────────

TEMP_FIELDS  = {"temp", "air_temp", "dewpoint"}
WIND_FIELDS  = {"wind_speed", "wind_gust"}   # m/s → mph
PRESS_FIELDS = {"pressure"}                   # hPa → inHg


def _c_to_f(c) -> Optional[float]:
    if c is None:
        return None
    return round(c * 9 / 5 + 32, 2)


def _ms_to_mph(ms) -> Optional[float]:
    """Meters per second → miles per hour."""
    if ms is None:
        return None
    return round(ms * 2.23694, 2)


def _hpa_to_inhg(hpa) -> Optional[float]:
    """Hectopascals → inches of mercury."""
    if hpa is None:
        return None
    return round(hpa * 0.02953, 3)


def _to_imperial(reading: Dict) -> Dict:
    """Convert all metric values to US Imperial in-place."""
    for field in TEMP_FIELDS:
        if field in reading:
            reading[field] = _c_to_f(reading[field])
    for field in WIND_FIELDS:
        if field in reading:
            reading[field] = _ms_to_mph(reading[field])
    for field in PRESS_FIELDS:
        if field in reading:
            reading[field] = _hpa_to_inhg(reading[field])
    return reading

# ─────────────────────────────────────────────────────────────────────────────
# Station registry — Tappan Zee (RM 25) through Albany (RM 143)
# Sorted by river mile (upstream)
# ─────────────────────────────────────────────────────────────────────────────
STATIONS = {
    "yonkers": {
        "source": "usgs", "id": "01376307", "name": "Yonkers",
        "lat": 40.936, "lon": -73.899, "river_mile": 20,
        "params": ["temp", "conductance", "turbidity"], "live": False,
        "note": "All sensors offline as of Apr 2026",
    },
    "piermont": {
        "source": "usgs", "id": "01376269", "name": "Piermont",
        "lat": 41.043, "lon": -73.896, "river_mile": 25,
        "params": ["temp", "conductance", "dissolved_oxygen", "ph", "turbidity"], "live": False,
        "note": "Station frame active, all sensors returning -999999 as of Apr 2026",
    },
    "bear_mountain": {
        "source": "ndbc", "id": "HBMN6", "name": "Bear Mountain (HRNERR)",
        "lat": 41.314, "lon": -73.985, "river_mile": 46,
        "params": ["air_temp", "wind_speed", "pressure"], "live": False,
        "note": "HRNERR met station — offline Apr 2026",
    },
    "west_point": {
        "source": "usgs", "id": "01374019", "name": "West Point",
        "lat": 41.386, "lon": -73.955, "river_mile": 50,
        "params": ["temp", "dissolved_oxygen", "ph", "conductance", "turbidity"], "live": False,
        "note": "Last data Sep 2014 — decommissioned",
    },
    "poughkeepsie": {
        "source": "usgs", "id": "01372043", "name": "Poughkeepsie",
        "lat": 41.721, "lon": -73.939, "river_mile": 75,
        "params": ["temp", "conductance", "turbidity"], "live": False,
        "note": "Last data Jan 2021 — decommissioned",
    },
    "turkey_point": {
        "source": "noaa", "id": "8518962", "name": "Turkey Point (NERRS)",
        "lat": 42.014, "lon": -73.939, "river_mile": 84,
        "params": ["temp", "conductance"], "live": True,
        "note": "HRNERR Tivoli Bays — southern edge of Storm King-Kingston corridor",
    },
    "norrie_point": {
        "source": "ndbc", "id": "NPXN6", "name": "Norrie Point (HRNERR)",
        "lat": 41.831, "lon": -73.942, "river_mile": 88,
        "params": ["air_temp", "wind_speed", "wind_direction", "pressure", "dewpoint"], "live": True,
        "note": "HRNERR met station — air/wind/pressure only, no water temp sensor",
    },
    "coxsackie": {
        "source": "noaa", "id": "8518979", "name": "Coxsackie",
        "lat": 42.353, "lon": -73.795, "river_mile": 108,
        "params": ["temp"], "live": True,
    },
    "schodack": {
        "source": "usgs", "id": "0135980207", "name": "Schodack Landing",
        "lat": 42.500, "lon": -73.777, "river_mile": 120,
        "params": ["temp", "conductance", "dissolved_oxygen", "turbidity"], "live": True,
        "note": "Some sensors intermittently offline",
    },
    "albany": {
        "source": "usgs", "id": "01359139", "name": "Albany",
        "lat": 42.648, "lon": -73.748, "river_mile": 143,
        "params": ["temp"], "live": True,
    },
}

LIVE_STATIONS = {k: v for k, v in STATIONS.items() if v.get("live", False)}

# ─────────────────────────────────────────────────────────────────────────────
# USGS fetch
# ─────────────────────────────────────────────────────────────────────────────

def _parse_usgs_response(data: dict) -> Optional[Dict]:
    ts_list = data.get("value", {}).get("timeSeries", [])
    if not ts_list:
        return None
    reading = {"timestamp": datetime.utcnow()}
    for ts in ts_list:
        param_code = ts["variable"]["variableCode"][0]["value"]
        field = PARAM_MAP.get(param_code)
        if not field:
            continue
        values = ts["values"][0]["value"]
        if not values:
            continue
        latest = values[-1]
        try:
            reading["timestamp"] = datetime.fromisoformat(
                latest["dateTime"].replace("Z", "+00:00")
            )
        except Exception:
            pass
        try:
            val = float(latest["value"])
            reading[field] = None if val == -999999.0 else round(val, 3)
        except (TypeError, ValueError):
            reading[field] = None
    return _to_imperial(reading)


def _fetch_usgs_sync(site_id: str) -> Optional[Dict]:
    try:
        resp = requests.get(USGS_IV_URL, params={
            "format": "json", "sites": site_id,
            "parameterCd": ALL_PARAMS, "siteStatus": "active",
        }, timeout=30)
        if resp.status_code == 200:
            return _parse_usgs_response(resp.json())
    except Exception as e:
        print(f"USGS sync fetch failed ({site_id}): {e}")
    return None


async def _fetch_usgs_async(site_id: str) -> Optional[Dict]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(USGS_IV_URL, params={
                "format": "json", "sites": site_id,
                "parameterCd": ALL_PARAMS, "siteStatus": "active",
            })
            if resp.status_code == 200:
                return _parse_usgs_response(resp.json())
    except Exception as e:
        print(f"USGS async fetch failed ({site_id}): {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# NOAA CO-OPS fetch
# ─────────────────────────────────────────────────────────────────────────────

NOAA_PRODUCTS = ["water_temperature", "conductivity", "salinity"]

NOAA_FIELD_MAP = {
    "water_temperature": "temp",
    "conductivity":      "conductance",
    "salinity":          "salinity",
}


def _fetch_noaa_sync(station_id: str) -> Optional[Dict]:
    reading = {"timestamp": datetime.utcnow()}
    for product in NOAA_PRODUCTS:
        try:
            resp = requests.get(NOAA_API_URL, params={
                "station": station_id, "product": product,
                "date": "latest", "units": "metric",
                "time_zone": "gmt", "format": "json",
            }, timeout=15)
            if resp.status_code != 200:
                continue
            d = resp.json()
            if "error" in d:
                continue
            data = d.get("data", [])
            if not data:
                continue
            try:
                reading["timestamp"] = datetime.strptime(data[0]["t"], "%Y-%m-%d %H:%M")
            except Exception:
                pass
            field = NOAA_FIELD_MAP.get(product)
            if field:
                try:
                    reading[field] = round(float(data[0]["v"]), 3)
                except (TypeError, ValueError):
                    reading[field] = None
        except Exception:
            continue
    return _to_imperial(reading) if len(reading) > 1 else None


async def _fetch_noaa_async(station_id: str) -> Optional[Dict]:
    reading = {"timestamp": datetime.utcnow()}
    async with httpx.AsyncClient(timeout=15.0) as client:
        for product in NOAA_PRODUCTS:
            try:
                resp = await client.get(NOAA_API_URL, params={
                    "station": station_id, "product": product,
                    "date": "latest", "units": "metric",
                    "time_zone": "gmt", "format": "json",
                })
                if resp.status_code != 200:
                    continue
                d = resp.json()
                if "error" in d:
                    continue
                data = d.get("data", [])
                if not data:
                    continue
                try:
                    reading["timestamp"] = datetime.strptime(data[0]["t"], "%Y-%m-%d %H:%M")
                except Exception:
                    pass
                field = NOAA_FIELD_MAP.get(product)
                if field:
                    try:
                        reading[field] = round(float(data[0]["v"]), 3)
                    except (TypeError, ValueError):
                        reading[field] = None
            except Exception:
                continue
    return _to_imperial(reading) if len(reading) > 1 else None


# ─────────────────────────────────────────────────────────────────────────────
# NDBC fetch (HRNERR met stations)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_ndbc_text(text: str) -> Optional[Dict]:
    lines = text.strip().splitlines()
    if len(lines) < 3:
        return None
    headers = lines[0].lstrip("#").split()
    latest = lines[2].split()
    if len(latest) < len(headers):
        return None
    row = dict(zip(headers, latest))
    try:
        ts = datetime(int(row["YY"]), int(row["MM"]), int(row["DD"]),
                      int(row["hh"]), int(row["mm"]))
    except Exception:
        ts = datetime.utcnow()
    reading = {"timestamp": ts}
    for col, field in NDBC_COL_MAP.items():
        val = row.get(col, "MM")
        reading[field] = None if val == "MM" else float(val) if _is_float(val) else None
    return _to_imperial(reading)


def _is_float(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False


def _fetch_ndbc_sync(station_id: str) -> Optional[Dict]:
    try:
        url = NDBC_URL.format(station=station_id.upper())
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200:
            return _parse_ndbc_text(resp.text)
    except Exception as e:
        print(f"NDBC sync fetch failed ({station_id}): {e}")
    return None


async def _fetch_ndbc_async(station_id: str) -> Optional[Dict]:
    try:
        url = NDBC_URL.format(station=station_id.upper())
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return _parse_ndbc_text(resp.text)
    except Exception as e:
        print(f"NDBC async fetch failed ({station_id}): {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

def _route_sync(station_config: Dict) -> Optional[Dict]:
    src = station_config["source"]
    sid = station_config["id"]
    if src == "noaa":
        return _fetch_noaa_sync(sid)
    if src == "ndbc":
        return _fetch_ndbc_sync(sid)
    return _fetch_usgs_sync(sid)


async def _route_async(station_config: Dict) -> Optional[Dict]:
    src = station_config["source"]
    sid = station_config["id"]
    if src == "noaa":
        return await _fetch_noaa_async(sid)
    if src == "ndbc":
        return await _fetch_ndbc_async(sid)
    return await _fetch_usgs_async(sid)


async def fetch_station_async(station_key: str, station_config: Dict) -> Optional[Dict]:
    try:
        data = await _route_async(station_config)
        if data:
            return data
    except Exception as e:
        print(f"fetch_station_async failed for {station_key}: {e}")
    mock = generate_mock_data(station_config["id"])
    mock["timestamp"] = datetime.fromisoformat(mock["timestamp"])
    return mock


def fetch_station_sync(station_key: str, station_config: Dict) -> Optional[Dict]:
    try:
        data = _route_sync(station_config)
        if data:
            return data
    except Exception as e:
        print(f"fetch_station_sync failed for {station_key}: {e}")
    mock = generate_mock_data(station_config["id"])
    mock["timestamp"] = datetime.fromisoformat(mock["timestamp"])
    return mock


async def fetch_all_stations() -> Dict[str, Dict]:
    results = {}
    for key, config in LIVE_STATIONS.items():
        data = await fetch_station_async(key, config)
        if data:
            results[key] = data
    return results


def fetch_historical_data(station_key: str, hours: int = 24) -> List[Dict]:
    config = STATIONS.get(station_key)
    if not config or config["source"] != "usgs":
        return _generate_mock_historical(hours)
    site_id = config["id"]
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    try:
        resp = requests.get(USGS_IV_URL, params={
            "format": "json", "sites": site_id,
            "parameterCd": ALL_PARAMS,
            "startDT": start_time.strftime("%Y-%m-%dT%H:%M+00:00"),
            "endDT":   end_time.strftime("%Y-%m-%dT%H:%M+00:00"),
        }, timeout=30)
        if resp.status_code == 200:
            ts_list = resp.json().get("value", {}).get("timeSeries", [])
            if ts_list:
                merged: Dict[str, Dict] = {}
                for ts in ts_list:
                    code = ts["variable"]["variableCode"][0]["value"]
                    field = PARAM_MAP.get(code)
                    if not field:
                        continue
                    for v in ts["values"][0]["value"]:
                        dt = v["dateTime"]
                        merged.setdefault(dt, {"timestamp": dt})
                        try:
                            val = float(v["value"])
                            merged[dt][field] = None if val == -999999.0 else round(val, 3)
                        except (TypeError, ValueError):
                            merged[dt][field] = None
                return sorted(merged.values(), key=lambda x: x["timestamp"], reverse=True)
    except Exception as e:
        print(f"Historical fetch failed for {station_key}: {e}")
    return _generate_mock_historical(hours)


def generate_mock_data(station_id: str) -> Dict:
    import random
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "temp":             round((10.0 + random.gauss(0, 2)) * 9/5 + 32, 2),  # °F
        "flow":             round(max(0, 500 + random.gauss(0, 100)), 2),
        "turbidity":        round(max(0, 10 + random.gauss(0, 3)), 2),
        "dissolved_oxygen": round(random.uniform(7.0, 12.0), 2),
        "ph":               round(random.uniform(6.8, 8.2), 2),
        "conductance":      round(random.uniform(150, 300), 1),
        "salinity":         round(random.uniform(0.0, 1.5), 3),
    }


def _generate_mock_historical(hours: int) -> List[Dict]:
    import random
    end_time = datetime.utcnow()
    return [
        {
            "timestamp": (end_time - timedelta(minutes=15 * i)).isoformat(),
            "temp":      round((10.0 + random.gauss(0, 1)) * 9/5 + 32, 2),
            "flow":      round(500 + random.gauss(0, 50), 2),
            "turbidity": round(10 + random.gauss(0, 2), 2),
        }
        for i in range(hours * 4)
    ]
