#!/usr/bin/env python3
"""Check every live station parameter in data/stations.json against the real provider.

Prints a table of station, provider, parameter, HTTP status, latest timestamp,
value, and OK/FAIL. Exits 0 when every live parameter returned a fresh value.
Stations with live=false are listed after the table and are not failures.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "stations.json"

USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"
NOAA_API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NOAA_OFFSET_URL = (
    "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station}/tidepredoffsets.json"
)
NDBC_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"
HRECOS_URL = (
    "https://nysm.hrecos.org/api/data/dynserv/hrecos/exportsite/csv/{sites}/{start}/{end}"
)

USER_AGENT = "hudson-station-check/1.0"
SENTINEL = -999999.0


def load_registry():
    with REGISTRY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _session():
    http = requests.Session()
    http.headers["User-Agent"] = USER_AGENT
    return http


def _parse_hrecos_time(value: str) -> datetime:
    # 20261103T144500+0000 with timezone=UTC
    stamp = value[:15]
    parsed = datetime.strptime(stamp, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    return parsed


def _header_code(header: str) -> str:
    return header.split()[0].strip().lower()


def _hrecos_table(http, stations, freshness_hours):
    codes = sorted({
        param["code"]
        for station in stations
        for param in station.get("parameters") or []
    })
    if not codes:
        return {}, 0, "no parameters"
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=max(freshness_hours, 3))).strftime("%Y%m%dT%H%M")
    end = now.strftime("%Y%m%dT%H%M")
    sites = ",".join(station["id"] for station in stations)
    url = HRECOS_URL.format(sites=sites, start=start, end=end)
    response = http.get(url, params={"timezone": "UTC", "variables": ",".join(codes)}, timeout=60)
    rows_by_station = {}
    if response.status_code == 200 and response.text and not response.text.lower().startswith("<"):
        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            normalized = {_header_code(key): value for key, value in row.items()}
            rows_by_station.setdefault(normalized.get("station", ""), []).append(normalized)
    return rows_by_station, response.status_code, response.text[:180].replace("\n", " ")


def _latest_hrecos(rows, code):
    for row in reversed(rows):
        raw = (row.get(code.lower()) or "").strip()
        if raw == "":
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if value == SENTINEL:
            continue
        return _parse_hrecos_time(row["datetime"]), value
    return None, None


def _noaa_latest(http, station_id, product):
    response = http.get(NOAA_API_URL, params={
        "station": station_id,
        "product": product,
        "date": "latest",
        "datum": "MLLW",
        "units": "metric",
        "time_zone": "gmt",
        "format": "json",
    }, timeout=30)
    payload = {}
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": {"message": response.text[:180]}}
    return response.status_code, payload


def _noaa_number(row, product, field):
    if product == "wind":
        key = {"wind_speed": "s", "wind_direction": "d", "wind_gust": "g"}.get(field, "s")
        raw = row.get(key)
    elif product == "salinity":
        raw = row.get("s", row.get("v"))
    else:
        raw = row.get("v")
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _noaa_time(row):
    return datetime.strptime(row["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)


def _prediction_harmonic(http, station_id):
    now = datetime.now(timezone.utc)
    response = http.get(NOAA_API_URL, params={
        "station": station_id,
        "product": "predictions",
        "begin_date": now.strftime("%Y%m%d %H:%M"),
        "end_date": (now + timedelta(hours=12)).strftime("%Y%m%d %H:%M"),
        "datum": "MLLW",
        "units": "english",
        "time_zone": "gmt",
        "interval": "h",
        "format": "json",
    }, timeout=30)
    try:
        payload = response.json()
    except ValueError:
        return response.status_code, None, None, "unreadable response"
    if payload.get("error"):
        message = payload["error"].get("message") if isinstance(payload["error"], dict) else payload["error"]
        return response.status_code, None, None, str(message)
    preds = payload.get("predictions") or []
    if not preds:
        return response.status_code, None, None, "no predictions"
    first = preds[0]
    when = datetime.strptime(first["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return response.status_code, when, float(first["v"]), ""


def _prediction_subordinate(http, station):
    offset_response = http.get(
        NOAA_OFFSET_URL.format(station=station["id"]), timeout=30
    )
    try:
        offsets = offset_response.json()
    except ValueError:
        offsets = {}
    reference = offsets.get("refStationId") or station.get("reference_id")
    if offset_response.status_code != 200 or not reference:
        return offset_response.status_code, None, None, "tide offsets unavailable"
    now = datetime.now(timezone.utc)
    response = http.get(NOAA_API_URL, params={
        "station": reference,
        "product": "predictions",
        "begin_date": now.strftime("%Y%m%d %H:%M"),
        "end_date": (now + timedelta(hours=18)).strftime("%Y%m%d %H:%M"),
        "datum": "MLLW",
        "units": "english",
        "time_zone": "gmt",
        "interval": "hilo",
        "format": "json",
    }, timeout=30)
    try:
        payload = response.json()
    except ValueError:
        return response.status_code, None, None, "unreadable reference predictions"
    if payload.get("error"):
        message = payload["error"].get("message") if isinstance(payload["error"], dict) else payload["error"]
        return response.status_code, None, None, str(message)
    events = payload.get("predictions") or []
    if not events:
        return response.status_code, None, None, "no reference hi/lo"
    event = events[0]
    is_high = (event.get("type") or "").lower() == "h"
    time_key = "timeOffsetHighTide" if is_high else "timeOffsetLowTide"
    height_key = "heightOffsetHighTide" if is_high else "heightOffsetLowTide"
    when = datetime.strptime(event["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    when = when + timedelta(minutes=float(offsets.get(time_key) or 0))
    height = float(event["v"])
    adjust = offsets.get(height_key)
    mode = (offsets.get("heightAdjustedType") or "A").upper()
    if adjust is not None:
        height = height * float(adjust) if mode == "R" else height + float(adjust)
    status = offset_response.status_code if offset_response.status_code != 200 else response.status_code
    return status, when, round(height, 3), ""


def _usgs_latest(http, stations):
    codes = sorted({
        param["code"]
        for station in stations
        for param in station.get("parameters") or []
    })
    response = http.get(USGS_IV_URL, params={
        "format": "json",
        "sites": ",".join(station["id"] for station in stations),
        "parameterCd": ",".join(codes),
        "siteStatus": "all",
    }, timeout=60)
    found = {}
    if response.status_code == 200:
        series = response.json().get("value", {}).get("timeSeries", [])
        for item in series:
            site = item["sourceInfo"]["siteCode"][0]["value"]
            code = item["variable"]["variableCode"][0]["value"]
            values = item["values"][0]["value"]
            if not values:
                continue
            latest = values[-1]
            try:
                value = float(latest["value"])
            except (TypeError, ValueError):
                continue
            if value == SENTINEL:
                continue
            when = datetime.fromisoformat(latest["dateTime"])
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            found[(site, code)] = (when, value)
    return response.status_code, found


def _ndbc_latest(http, station_id):
    response = http.get(NDBC_URL.format(station=station_id.upper()), timeout=30)
    if response.status_code != 200:
        return response.status_code, None, {}
    lines = [line for line in response.text.splitlines() if line and not line.startswith("#")]
    header_line = response.text.splitlines()[0].lstrip("#").split()
    if not lines:
        return response.status_code, None, {}
    latest = lines[0].split()
    row = dict(zip(header_line, latest))
    try:
        when = datetime(
            int(row["YY"]), int(row["MM"]), int(row["DD"]), int(row["hh"]), int(row["mm"]),
            tzinfo=timezone.utc,
        )
    except (KeyError, ValueError):
        when = None
    return response.status_code, when, row


def _fresh(when, freshness_hours, now):
    if when is None:
        return False
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (now - when) <= timedelta(hours=freshness_hours) and when <= now + timedelta(minutes=30)


def _format_time(when):
    if not isinstance(when, datetime):
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _result(station, provider, parameter, status, when, value, ok, detail=""):
    return {
        "station": station,
        "provider": provider,
        "parameter": parameter,
        "status": status,
        "timestamp": _format_time(when),
        "value": "" if value is None else value,
        "ok": "OK" if ok else "FAIL",
        "detail": detail,
    }


def collect_results(registry=None):
    registry = registry or load_registry()
    freshness = float(registry.get("meta", {}).get("freshness_hours", 6))
    now = datetime.now(timezone.utc)
    http = _session()
    stations = registry["stations"]
    live = [station for station in stations if station.get("live")]
    results = []

    hrecos_stations = [station for station in live if station["provider"] == "hrecos"]
    hrecos_rows, hrecos_status, hrecos_detail = ({}, 0, "")
    if hrecos_stations:
        try:
            hrecos_rows, hrecos_status, hrecos_detail = _hrecos_table(http, hrecos_stations, freshness)
        except requests.RequestException as exc:
            hrecos_status, hrecos_detail = 0, str(exc)

    usgs_stations = [station for station in live if station["provider"] == "usgs"]
    usgs_status, usgs_found = 0, {}
    if usgs_stations:
        try:
            usgs_status, usgs_found = _usgs_latest(http, usgs_stations)
        except requests.RequestException as exc:
            usgs_status, usgs_found = 0, {}
            usgs_error = str(exc)
        else:
            usgs_error = ""
    else:
        usgs_error = ""

    noaa_cache = {}

    for station in live:
        provider = station["provider"]
        for param in station.get("parameters") or []:
            field = param["field"]
            code = param["code"]
            label = f"{station['key']}"
            if provider == "hrecos":
                when, value = _latest_hrecos(hrecos_rows.get(station["id"], []), code)
                ok = hrecos_status == 200 and value is not None and _fresh(when, freshness, now)
                detail = "" if ok else hrecos_detail
                results.append(_result(label, provider, field, hrecos_status, when, value, ok, detail))
            elif provider == "usgs":
                when, value = usgs_found.get((station["id"], code), (None, None))
                ok = usgs_status == 200 and value is not None and _fresh(when, freshness, now)
                results.append(_result(label, provider, field, usgs_status, when, value, ok, usgs_error))
            elif provider == "ndbc":
                try:
                    status, when, row = _ndbc_latest(http, station["id"])
                except requests.RequestException as exc:
                    results.append(_result(label, provider, field, 0, None, None, False, str(exc)))
                    continue
                raw = row.get(code, "MM")
                value = None
                if raw not in (None, "", "MM"):
                    try:
                        value = float(raw)
                    except ValueError:
                        value = None
                ok = status == 200 and value is not None and _fresh(when, freshness, now)
                results.append(_result(label, provider, field, status, when, value, ok))
            elif provider == "noaa" and station.get("kind") == "prediction":
                try:
                    if station.get("tide_type") == "subordinate":
                        status, when, value, detail = _prediction_subordinate(http, station)
                    else:
                        status, when, value, detail = _prediction_harmonic(http, station["id"])
                except requests.RequestException as exc:
                    status, when, value, detail = 0, None, None, str(exc)
                ok = status == 200 and value is not None
                results.append(_result(label, provider, field, status, when, value, ok, detail))
            elif provider == "noaa":
                cache_key = (station["id"], code)
                if cache_key not in noaa_cache:
                    try:
                        noaa_cache[cache_key] = _noaa_latest(http, station["id"], code)
                    except requests.RequestException as exc:
                        noaa_cache[cache_key] = (0, {"error": {"message": str(exc)}})
                status, payload = noaa_cache[cache_key]
                detail = ""
                when, value = None, None
                if payload.get("error"):
                    err = payload["error"]
                    detail = err.get("message") if isinstance(err, dict) else str(err)
                else:
                    data = payload.get("data") or []
                    if data:
                        when = _noaa_time(data[0])
                        value = _noaa_number(data[0], code, field)
                    else:
                        detail = "empty data"
                ok = status == 200 and value is not None and _fresh(when, freshness, now)
                results.append(_result(label, provider, field, status, when, value, ok, detail))
            else:
                results.append(_result(label, provider, field, 0, None, None, False, "unknown provider"))
    skipped = [station for station in stations if not station.get("live")]
    return results, skipped


def format_table(results):
    headers = ["station", "provider", "parameter", "status", "timestamp", "value", "result"]
    rows = []
    for item in results:
        rows.append([
            item["station"],
            item["provider"],
            item["parameter"],
            str(item["status"]),
            item["timestamp"],
            str(item["value"]),
            item["ok"],
        ])
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def line(cells):
        return "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(cells))

    out = [line(headers), line(["-" * width for width in widths])]
    out.extend(line(row) for row in rows)
    failures = [item for item in results if item["ok"] != "OK"]
    out.append("")
    out.append(f"{sum(1 for item in results if item['ok'] == 'OK')} OK, {len(failures)} FAIL, {len(results)} checked")
    for item in failures:
        if item["detail"]:
            out.append(f"  {item['station']} {item['parameter']}: {item['detail']}")
    return "\n".join(out)


def main():
    registry = load_registry()
    results, skipped = collect_results(registry)
    print()
    print(format_table(results))
    if skipped:
        print("")
        print("Not checked (live=false):")
        for station in skipped:
            print(f"  {station['key']} {station['provider']} {station['id']} — {station.get('note', '')}")
    failed = any(item["ok"] != "OK" for item in results)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
