"""
Native SQL for the candles table (TimescaleDB).

All database statements for this POC live here — analogous to @Query(nativeQuery = true)
in a Spring Data JPA repository. Application code must import from this module, not
embed SQL strings elsewhere.
"""

# DDL for candles lives in data/migrations/sql/ (applied on startup). This file is DML only.

# --- DML ---

UPSERT_CANDLE = """
INSERT INTO candles (symbol, timeframe, ts, open, high, low, close, volume)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (symbol, timeframe, ts) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume;
"""

# Sync path: keep already-stored closed candles untouched (overwrite_closed_candles=false).
INSERT_CANDLE_IGNORE = """
INSERT INTO candles (symbol, timeframe, ts, open, high, low, close, volume)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (symbol, timeframe, ts) DO NOTHING;
"""

SELECT_CANDLES_BY_RANGE = """
SELECT ts, open, high, low, close, volume
FROM candles
WHERE symbol = %s
  AND timeframe = %s
  AND ts >= %s::timestamptz
  AND ts <= %s::timestamptz
ORDER BY ts ASC
"""

# Derived candles are aggregated from canonical stored 1m rows.
SELECT_DERIVED_CANDLES_BY_RANGE = """
WITH source AS (
    SELECT ts, open, high, low, close, volume
    FROM candles
    WHERE symbol = %s
      AND timeframe = '1m'
      AND ts >= %s::timestamptz
      AND ts <= %s::timestamptz
), bucketed AS (
    SELECT
        time_bucket(%s::interval, ts) AS bucket_ts,
        ts,
        open,
        high,
        low,
        close,
        volume
    FROM source
)
SELECT
    bucket_ts AS ts,
    (array_agg(open ORDER BY ts ASC))[1] AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    (array_agg(close ORDER BY ts DESC))[1] AS close,
    SUM(volume) AS volume
FROM bucketed
GROUP BY bucket_ts
ORDER BY bucket_ts ASC
"""

COUNT_CANDLES = """
SELECT COUNT(*) FROM candles
WHERE symbol = %s AND timeframe = %s
"""

# Lightweight timestamp-only read used by gap detection over large 1m ranges.
SELECT_TS_BY_RANGE = """
SELECT ts
FROM candles
WHERE symbol = %s
  AND timeframe = %s
  AND ts >= %s::timestamptz
  AND ts <= %s::timestamptz
ORDER BY ts ASC
"""

# Drives incremental sync: fetch resumes from the latest stored closed candle (OQ-04).
SELECT_MAX_TS = """
SELECT MAX(ts) FROM candles
WHERE symbol = %s AND timeframe = %s
"""

# --- data_gaps DML ---

INSERT_GAP = """
INSERT INTO data_gaps (symbol, timeframe, start_ts, end_ts, status)
VALUES (%s, %s, %s::timestamptz, %s::timestamptz, 'open')
RETURNING id
"""

SELECT_OPEN_GAPS = """
SELECT id, symbol, timeframe, start_ts, end_ts, status, retry_count
FROM data_gaps
WHERE symbol = %s AND timeframe = %s AND status = 'open'
ORDER BY start_ts ASC
"""

RESOLVE_GAP = """
UPDATE data_gaps
SET status = 'resolved', resolved_at = NOW(), last_checked_at = NOW()
WHERE id = %s
"""

RECORD_GAP_RETRY = """
UPDATE data_gaps
SET retry_count = retry_count + 1, last_checked_at = NOW(), last_error = %s
WHERE id = %s
"""
