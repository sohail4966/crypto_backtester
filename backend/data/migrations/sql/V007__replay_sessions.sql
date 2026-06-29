CREATE TABLE IF NOT EXISTS app.replay_sessions (
    session_id      UUID PRIMARY KEY,
    symbol          TEXT             NOT NULL REFERENCES app.symbols (symbol),
    timeframe       TEXT             NOT NULL,
    step_timeframe  TEXT             NOT NULL,
    start_anchor    BIGINT           NOT NULL,
    cursor_ts       BIGINT           NOT NULL,
    indicators      JSONB            NOT NULL DEFAULT '[]',
    speed           DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    state           TEXT             NOT NULL,
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_replay_sessions_updated_at ON app.replay_sessions (updated_at);
