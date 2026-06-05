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
