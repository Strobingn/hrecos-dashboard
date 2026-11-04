"""API regressions using a temporary SQLite database and mocked tide data."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import main
from app.db import get_db
from app.models import Base, HRECOSReading


@asynccontextmanager
async def api_client(db_path, readings=()):
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessions = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sessions() as session:
        session.add_all(readings)
        await session.commit()

    async def database():
        async with sessions() as session:
            yield session

    main.app.dependency_overrides[get_db] = database
    try:
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


@pytest.mark.parametrize("value", [0.0, 12.5, None])
def test_station_stats_preserve_zero_and_missing_values(tmp_path, value):
    async def check():
        reading = HRECOSReading(
            station="west_point",
            timestamp=datetime.now(timezone.utc),
            temp=value,
            flow=value,
            turbidity=value,
        )
        async with api_client(tmp_path / "stats.db", [reading]) as client:
            response = await client.get("/api/stats/west_point")
        assert response.status_code == 200
        data = response.json()
        assert data["readings_count"] == 1
        for metric in ("temperature", "flow"):
            assert data[metric] == {"avg": value, "min": value, "max": value}
        assert data["turbidity"]["avg"] == value

    asyncio.run(check())


def test_station_stats_without_readings(tmp_path):
    async def check():
        async with api_client(tmp_path / "empty.db") as client:
            response = await client.get("/api/stats/west_point")
        assert response.status_code == 200
        data = response.json()
        assert data["readings_count"] == 0
        assert data["temperature"] == {"avg": None, "min": None, "max": None}

    asyncio.run(check())


@pytest.mark.parametrize("hours, step_minutes", [(1, 30), (48, 30), (168, 60)])
def test_tides_return_the_full_requested_forecast(tmp_path, monkeypatch, hours, step_minutes):
    start = datetime(2026, 6, 15, 12)
    predictions = [
        {"time": start + timedelta(minutes=i * step_minutes), "height": 1.25, "type": "high"}
        for i in range(hours * 60 // step_minutes + 1)
    ]
    current = {"current_height": 1.25, "next_time": start + timedelta(hours=1)}

    def forecast(**kwargs):
        assert kwargs == {"hours": hours, "region": "cornwall_on_hudson"}
        return predictions

    monkeypatch.setattr(main, "get_tide_predictions", forecast)
    monkeypatch.setattr(main, "get_current_tide", lambda **kwargs: current)

    async def check():
        async with api_client(tmp_path / "tides.db") as client:
            response = await client.get("/api/tides", params={"hours": hours})
        assert response.status_code == 200
        data = response.json()
        assert data["hours"] == hours
        assert len(data["predictions"]) == len(predictions)
        assert data["predictions"][-1]["time"] == (start + timedelta(hours=hours)).isoformat()

    asyncio.run(check())
