CREATE TABLE IF NOT EXISTS app.backtest_runs (
    run_id           UUID PRIMARY KEY,
    symbol           TEXT             NOT NULL REFERENCES app.symbols (symbol),
    timeframe        TEXT             NOT NULL,
    start_ts         BIGINT           NOT NULL,
    end_ts           BIGINT           NOT NULL,
    initial_capital  DOUBLE PRECISION NOT NULL,
    strategy_name    TEXT,
    strategy_config  JSONB            NOT NULL,
    backtest_config  JSONB            NOT NULL,
    metrics          JSONB            NOT NULL,
    trades           JSONB            NOT NULL DEFAULT '[]',
    signals          JSONB            NOT NULL DEFAULT '[]',
    equity           JSONB            NOT NULL DEFAULT '[]',
    status           TEXT             NOT NULL DEFAULT 'completed',
    error_message    TEXT,
    user_id          UUID             REFERENCES app.users (id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_symbol_created
    ON app.backtest_runs (symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_user_id
    ON app.backtest_runs (user_id);
