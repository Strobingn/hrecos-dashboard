-- Initialize TimescaleDB hypertable for HRECOS readings
-- This script runs when the database container starts for the first time

-- Create extension if not exists
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- The tables are created by SQLAlchemy, but we need to convert them to hypertables
-- This will be done by the application on first startup

-- Note: hypertable creation requires the table to exist first
-- The application will handle this in models.py via event listeners

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_readings_station_time 
    ON hrecos_readings (station, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
    ON hrecos_readings (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_anomalies_station 
    ON anomaly_logs (station, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_anomalies_severity 
    ON anomaly_logs (severity, timestamp DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
