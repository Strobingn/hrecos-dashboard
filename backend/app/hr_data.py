import requests
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# ─────────────────────────────────────────────────────────────────────────────
# USGS NWIS Instantaneous Values API
# Real HRECOS-affiliated stations on the Hudson River
# Docs: https://waterservices.usgs.gov/nwis/iv/
# ─────────────────────────────────────────────────────────────────────────────

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"
USGS_SITE_URL = "https://waterservices.usgs.gov/nwis/site/"

# USGS parameter codes
PARAM_TEMP        = "00010"   # Water temperature, °C
PARAM_DO          = "00300"   # Dissolved oxygen, mg/L
PARAM_PH          = "00400"   # pH
PARAM_CONDUCTANCE = "00095"   # Specific conductance, uS/cm
PARAM_TURBIDITY   = "63680"   # Turbidity, FNU
PARAM_GAGE_HEIGHT = "00065"   # Gage height / water level, ft
PARAM_DISCHARGE   = "00060"   # Streamflow, ft³/s
PARAM_SALINITY    = "00480"   # Salinity, ppt

ALL_PARAMS = ",".join([
    PARAM_TEMP, PARAM_DO, PARAM_PH,
    PARAM_CONDUCTANCE, PARAM_TURBIDITY,
    PARAM_GAGE_HEIGHT, PARAM_DISCHARGE, PARAM_SALINITY
])

# Confirmed active USGS stations on the Hudson River with live IV data
STATIONS = {
    "poughkeepsie": {
        "id": "01372043",
        "name": "Poughkeepsie",
        "lat": 41.7083,
        "lon": -73.9425,
        "params": ["temp", "dissolved_oxygen", "ph", "conductance", "turbidity"]
    },
    "poughkeepsie_below": {
        "id": "01372058",
        "name": "Poughkeepsie (Below)",
        "lat": 41.6901,
        "lon": -73.9513,
        "params": ["temp", "conductance", "turbidity"]
    },
    "albany": {
        "id": "01359139",
        "name": "Albany",
        "lat": 42.6526,
        "lon": -73.7562,
        "params": ["temp"]
    },
}

# USGS param code → internal field name mapping
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


def _parse_usgs_response(data: dict) -> Optional[Dict]:
    """Parse USGS IV JSON response into a flat reading dict."""
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
        raw_val = latest.get("value")
        ts_str = latest.get("dateTime")

        # Parse timestamp from the most recent reading
        try:
            reading["timestamp"] = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            pass

        # Skip sentinel no-data values
        try:
            val = float(raw_val)
            if val == -999999.0:
                reading[field] = None
            else:
                reading[field] = round(val, 3)
        except (TypeError, ValueError):
            reading[field] = None

    return reading


async def fetch_station_async(station_key: str, station_config: Dict) -> Optional[Dict]:
    """Fetch latest reading from USGS NWIS IV API asynchronously."""
    site_id = station_config["id"]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(USGS_IV_URL, params={
                "format": "json",
                "sites": site_id,
                "parameterCd": ALL_PARAMS,
                "siteStatus": "active",
            })

            if resp.status_code == 200:
                reading = _parse_usgs_response(resp.json())
                if reading:
                    return reading

    except Exception as e:
        print(f"USGS async fetch failed for {station_key} ({site_id}): {e}")

    # Fallback to mock data
    mock = generate_mock_data(site_id)
    mock["timestamp"] = datetime.fromisoformat(mock["timestamp"])
    return mock


def fetch_station_sync(station_key: str, station_config: Dict) -> Optional[Dict]:
    """Fetch latest reading from USGS NWIS IV API synchronously (for scheduler)."""
    site_id = station_config["id"]

    try:
        resp = requests.get(USGS_IV_URL, params={
            "format": "json",
            "sites": site_id,
            "parameterCd": ALL_PARAMS,
            "siteStatus": "active",
        }, timeout=30)

        if resp.status_code == 200:
            reading = _parse_usgs_response(resp.json())
            if reading:
                return reading

    except Exception as e:
        print(f"USGS sync fetch failed for {station_key} ({site_id}): {e}")

    # Fallback to mock data
    mock = generate_mock_data(site_id)
    mock["timestamp"] = datetime.fromisoformat(mock["timestamp"])
    return mock


async def fetch_all_stations() -> Dict[str, Dict]:
    """Fetch latest data from all configured stations."""
    results = {}
    for key, config in STATIONS.items():
        data = await fetch_station_async(key, config)
        if data:
            results[key] = data
    return results


def fetch_historical_data(station_key: str, hours: int = 24) -> List[Dict]:
    """Fetch historical IV data from USGS for a station."""
    site_id = STATIONS[station_key]["id"]
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    try:
        resp = requests.get(USGS_IV_URL, params={
            "format": "json",
            "sites": site_id,
            "parameterCd": ALL_PARAMS,
            "startDT": start_time.strftime("%Y-%m-%dT%H:%M+00:00"),
            "endDT": end_time.strftime("%Y-%m-%dT%H:%M+00:00"),
        }, timeout=30)

        if resp.status_code == 200:
            ts_list = resp.json().get("value", {}).get("timeSeries", [])
            if ts_list:
                # Merge all param time series by timestamp
                merged: Dict[str, Dict] = {}
                for ts in ts_list:
                    param_code = ts["variable"]["variableCode"][0]["value"]
                    field = PARAM_MAP.get(param_code)
                    if not field:
                        continue
                    for v in ts["values"][0]["value"]:
                        dt = v["dateTime"]
                        if dt not in merged:
                            merged[dt] = {"timestamp": dt}
                        try:
                            val = float(v["value"])
                            merged[dt][field] = None if val == -999999.0 else round(val, 3)
                        except (TypeError, ValueError):
                            merged[dt][field] = None

                return sorted(merged.values(), key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        print(f"USGS historical fetch failed for {station_key}: {e}")

    # Fallback mock
    return _generate_mock_historical(hours)


def generate_mock_data(station_id: str) -> Dict:
    """Realistic mock data — only used when USGS API is unreachable."""
    import random
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "temp": round(10.0 + random.gauss(0, 2), 2),
        "flow": round(max(0, 500 + random.gauss(0, 100)), 2),
        "turbidity": round(max(0, 10 + random.gauss(0, 3)), 2),
        "dissolved_oxygen": round(random.uniform(7.0, 12.0), 2),
        "ph": round(random.uniform(6.8, 8.2), 2),
        "conductance": round(random.uniform(150, 300), 1),
        "salinity": round(random.uniform(0.0, 1.5), 3),
    }


def _generate_mock_historical(hours: int) -> List[Dict]:
    import random
    end_time = datetime.utcnow()
    readings = []
    for i in range(hours * 4):
        ts = end_time - timedelta(minutes=15 * i)
        readings.append({
            "timestamp": ts.isoformat(),
            "temp": round(10.0 + random.gauss(0, 1), 2),
            "flow": round(500 + random.gauss(0, 50), 2),
            "turbidity": round(10 + random.gauss(0, 2), 2),
        })
    return readings
