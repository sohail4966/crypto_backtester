CREATE TABLE IF NOT EXISTS candles (
    symbol     TEXT             NOT NULL,
    timeframe  TEXT             NOT NULL,
    ts         TIMESTAMPTZ      NOT NULL,
    open       DOUBLE PRECISION NOT NULL,
    high       DOUBLE PRECISION NOT NULL,
    low        DOUBLE PRECISION NOT NULL,
    close      DOUBLE PRECISION NOT NULL,
    volume     DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (symbol, timeframe, ts)
);
