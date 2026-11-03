"""Registry consistency. Does not call external APIs."""

from app.registry import FOCUS_STATIONS, REGISTRY, STATIONS

DEAD_IDS = {"8518490", "01374019", "01376269", "01372043", "01372058", "0135980207"}
REQUIRED = ("key", "name", "provider", "id", "lat", "lon", "river_mile", "focus", "live", "kind", "parameters")


def test_registry_covers_focus_stretch():
    assert REGISTRY["meta"]["freshness_hours"] >= 1
    keys = [station["key"] for station in REGISTRY["stations"]]
    assert keys == list(STATIONS)
    for key in ("piermont", "west_point", "poughkeepsie", "newburgh", "beacon", "haverstraw", "peekskill"):
        assert key in STATIONS
        assert STATIONS[key]["focus"] is True
    assert STATIONS["west_point"]["id"] == "HWEST"
    assert STATIONS["west_point"]["provider"] == "hrecos"
    assert STATIONS["piermont"]["id"] == "HPMNT"
    assert STATIONS["poughkeepsie"]["id"] == "HPOUG"
    assert STATIONS["newburgh"]["id"] == "8518935"
    assert STATIONS["albany"]["focus"] is False
    assert STATIONS["schodack"]["focus"] is False
    assert STATIONS["schodack"]["live"] is False
    assert STATIONS["bear_mountain"]["live"] is False
    assert FOCUS_STATIONS == ["piermont", "west_point", "poughkeepsie"]


def test_every_station_has_identity_and_live_stations_have_parameters():
    seen = set()
    for station in REGISTRY["stations"]:
        for field in REQUIRED:
            assert field in station
        assert station["key"] not in seen
        seen.add(station["key"])
        assert station["provider"] in {"hrecos", "usgs", "noaa", "ndbc"}
        assert station["id"] not in DEAD_IDS
        if station["focus"]:
            assert 25 <= station["river_mile"] <= 75
        if station["live"]:
            assert station["parameters"], station["key"]
            for param in station["parameters"]:
                assert param["field"] and param["code"]
        else:
            assert station["parameters"] == []
