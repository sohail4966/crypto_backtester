CREATE TABLE IF NOT EXISTS app.scan_runs (
    scan_id          UUID PRIMARY KEY,
    timeframes       TEXT[]           NOT NULL,
    symbols          TEXT[]           NOT NULL,
    start_ts         BIGINT           NOT NULL,
    end_ts           BIGINT           NOT NULL,
    condition_config JSONB            NOT NULL,
    alert_trigger    TEXT             NOT NULL DEFAULT 'edge',
    matches          JSONB            NOT NULL DEFAULT '[]',
    alert_count      INT              NOT NULL DEFAULT 0,
    duration_ms      INT              NOT NULL DEFAULT 0,
    status           TEXT             NOT NULL DEFAULT 'completed',
    error_message    TEXT,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_runs_created
    ON app.scan_runs (created_at DESC);
