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

SELECT_CANDLES_BY_RANGE = """
SELECT ts, open, high, low, close, volume
FROM candles
WHERE symbol = %s
  AND timeframe = %s
  AND ts >= %s::timestamptz
  AND ts <= %s::timestamptz
ORDER BY ts ASC
"""

COUNT_CANDLES = """
SELECT COUNT(*) FROM candles
WHERE symbol = %s AND timeframe = %s
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
