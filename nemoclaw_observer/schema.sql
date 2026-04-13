-- ─────────────────────────────────────────────────────────────────────────────
-- NemoClaw Observer — PostgreSQL Schema
-- Run once on the Hetzy VPS PostgreSQL instance.
--
-- Connect:  psql -h 46.225.51.30 -U postgres amep_schema_v1
-- Apply:    \i schema.sql
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Core log table (append-only, one row per service per run)
CREATE TABLE IF NOT EXISTS nemoclaw_dashboard_log (
    id        SERIAL      PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    layer     TEXT        NOT NULL,                      -- VPS / Local / Agent / LLM / App
    service   TEXT        NOT NULL,                      -- n8n / PostgreSQL / Ollama / …
    status    TEXT        NOT NULL                       -- ok / warn / error
              CHECK (status IN ('ok', 'warn', 'error')),
    note      TEXT                                       -- human-readable detail
);

-- Indexes for fast recent-status queries
CREATE INDEX IF NOT EXISTS idx_ndl_timestamp
    ON nemoclaw_dashboard_log (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_ndl_service_time
    ON nemoclaw_dashboard_log (service, timestamp DESC);

-- 2. Convenience view — latest status for every service
CREATE OR REPLACE VIEW nemoclaw_latest_status AS
SELECT DISTINCT ON (service)
    timestamp,
    layer,
    service,
    status,
    note
FROM   nemoclaw_dashboard_log
ORDER  BY service, timestamp DESC;

-- 3. Convenience view — last 7 days of alerts only
CREATE OR REPLACE VIEW nemoclaw_recent_alerts AS
SELECT timestamp, layer, service, status, note
FROM   nemoclaw_dashboard_log
WHERE  status IN ('warn', 'error')
  AND  timestamp >= NOW() - INTERVAL '7 days'
ORDER  BY timestamp DESC;

COMMENT ON TABLE nemoclaw_dashboard_log IS
    'Append-only log of NemoClaw Observer dashboard snapshots. '
    'One row per service per scheduled or manual run.';

COMMENT ON VIEW nemoclaw_latest_status IS
    'Latest recorded status for every monitored service.';

COMMENT ON VIEW nemoclaw_recent_alerts IS
    'All warn/error events in the last 7 days, newest first.';
