-- Initialize TimescaleDB for the HRECOS readings store.
--
-- This script runs once, when the database container is first created.
-- Application tables do not exist yet at that point, so this file must NOT
-- reference them: indexes and the hypertable are created by the backend on
-- startup (see backend/app/models.py and backend/app/main.py).

CREATE EXTENSION IF NOT EXISTS timescaledb;
