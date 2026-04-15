-- Fireclaw — Postgres incident log (optional).
-- Mirror of ~/.fireclaw/incidents.jsonl for cross-host querying.
-- Append-only. Truth: rows are never updated or deleted.

CREATE TABLE IF NOT EXISTS fireclaw_incidents (
    id                  BIGSERIAL PRIMARY KEY,
    ts                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    rule_id             TEXT NOT NULL,
    signal_kind         TEXT NOT NULL,
    signal_ok           BOOLEAN NOT NULL,
    signal_detail       TEXT,
    action_kind         TEXT NOT NULL,
    action_executed     BOOLEAN NOT NULL,
    action_exit_code    INTEGER,
    action_duration_ms  INTEGER,
    action_stdout       TEXT,
    action_stderr       TEXT,
    escalated           BOOLEAN NOT NULL DEFAULT FALSE,
    trigger_count_24h   INTEGER,
    fireclaw_version    TEXT,
    raw_jsonl           JSONB
);

CREATE INDEX IF NOT EXISTS fireclaw_incidents_ts_idx
    ON fireclaw_incidents (ts DESC);

CREATE INDEX IF NOT EXISTS fireclaw_incidents_rule_idx
    ON fireclaw_incidents (rule_id, ts DESC);

-- Convenience view: incidents in the last 24h
CREATE OR REPLACE VIEW fireclaw_recent_incidents AS
SELECT id, ts, rule_id, signal_detail, action_kind,
       action_exit_code, escalated, trigger_count_24h
FROM fireclaw_incidents
WHERE ts > now() - INTERVAL '24 hours'
ORDER BY ts DESC;

-- Convenience view: open alerts (escalated, not yet acknowledged elsewhere)
CREATE OR REPLACE VIEW fireclaw_open_alerts AS
SELECT id, ts, rule_id, signal_detail, action_kind,
       action_exit_code, action_stderr
FROM fireclaw_incidents
WHERE escalated = TRUE
  AND ts > now() - INTERVAL '7 days'
ORDER BY ts DESC;
