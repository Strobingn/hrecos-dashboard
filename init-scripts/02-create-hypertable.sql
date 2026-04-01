-- Convert tables to TimescaleDB hypertables
-- Run this after the application has created the tables

-- Note: This is handled automatically by the application
-- But can be run manually if needed:

-- SELECT create_hypertable('hrecos_readings', 'timestamp', if_not_exists => TRUE);
-- SELECT create_hypertable('anomaly_logs', 'timestamp', if_not_exists => TRUE);

-- Set chunk time interval (optional - default is 7 days)
-- SELECT set_chunk_time_interval('hrecos_readings', INTERVAL '1 day');
