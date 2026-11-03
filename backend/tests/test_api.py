"""Smoke tests for the HRECOS API.

These run against SQLite and never touch the network: external data fetchers
are monkeypatched so results are deterministic and CI stays offline-safe.
"""

from datetime import datetime

import app.main as main


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["stations_configured"] > 0


def test_root_lists_stations(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "operational"
    assert isinstance(body["stations"], list) and body["stations"]


def test_stations_endpoint(client):
    response = client.get("/api/stations")
    assert response.status_code == 200
    body = response.json()
    assert body["stations"]
    station = body["stations"][0]
    assert {"key", "name", "location", "parameters"} <= station.keys()


def test_unknown_region_returns_404(client):
    response = client.get("/api/stations", params={"region": "atlantis"})
    assert response.status_code == 404


def test_latest_uses_fetcher(client, monkeypatch):
    async def fake_fetch_all_stations(region=None):
        return {
            "norrie_point": {
                "timestamp": datetime.utcnow().isoformat(),
                "air_temp": 61.2,
                "wind_speed": 9.0,
            }
        }

    monkeypatch.setattr(main, "fetch_all_stations", fake_fetch_all_stations)

    response = client.get("/api/latest")
    assert response.status_code == 200
    body = response.json()
    assert "norrie_point" in body["readings"]
    assert body["readings"]["norrie_point"]["wind_speed"] == 9.0


def test_data_alias_matches_latest(client, monkeypatch):
    async def fake_fetch_all_stations(region=None):
        return {"turkey_point": {"timestamp": datetime.utcnow().isoformat(), "temp": 58.0}}

    monkeypatch.setattr(main, "fetch_all_stations", fake_fetch_all_stations)
    assert client.get("/api/data").status_code == 200


def test_tides_are_serialized(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "get_tide_predictions",
        lambda hours, region: [
            {"time": datetime(2026, 1, 1, 12, 0), "height": 3.2, "type": "high"}
        ],
    )
    monkeypatch.setattr(
        main,
        "get_current_tide",
        lambda region: {
            "current_height": 2.1,
            "current_type": "rising",
            "next_type": "high",
            "next_time": datetime(2026, 1, 1, 12, 0),
        },
    )

    response = client.get("/api/tides")
    assert response.status_code == 200
    body = response.json()
    assert body["predictions"][0]["height"] == 3.2
    assert body["current"]["next_time"].startswith("2026-01-01T12:00")


def test_historical_falls_back_to_generated_data(client):
    response = client.get("/api/historical/turkey_point", params={"hours": 6})
    assert response.status_code == 200
    body = response.json()
    assert body["station"] == "turkey_point"
    assert body["count"] > 0


def test_stats_on_empty_database(client):
    response = client.get("/api/stats/turkey_point", params={"hours": 24})
    assert response.status_code == 200
    body = response.json()
    assert body["station"] == "turkey_point"
    assert body["readings_count"] == 0
