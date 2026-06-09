-- Audit table for missing 1m candle ranges so sync can retry and resolve them.
-- Gaps are detected from candle continuity (Step 4); this table only records them.
CREATE TABLE IF NOT EXISTS data_gaps (
    id              BIGSERIAL   PRIMARY KEY,
    symbol          TEXT        NOT NULL,
    timeframe       TEXT        NOT NULL,
    start_ts        TIMESTAMPTZ NOT NULL,
    end_ts          TIMESTAMPTZ NOT NULL,
    status          TEXT        NOT NULL, -- open | resolved
    retry_count     INT         NOT NULL DEFAULT 0,
    last_checked_at TIMESTAMPTZ,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);

-- Sync repeatedly looks up still-open gaps per symbol/timeframe to retry them.
CREATE INDEX IF NOT EXISTS idx_data_gaps_open
    ON data_gaps (symbol, timeframe, status);
