-- BE-021: strengthen data_gaps constraints
-- Deduplicate overlapping open gaps: keep the earliest-created row per symbol/timeframe
-- when ranges overlap, and delete later duplicates.

DELETE FROM data_gaps a
USING data_gaps b
WHERE a.status = 'open'
  AND b.status = 'open'
  AND a.symbol = b.symbol
  AND a.timeframe = b.timeframe
  AND a.id > b.id
  AND a.start_ts <= b.end_ts
  AND b.start_ts <= a.end_ts;

-- FK to catalog (symbols may live in app.symbols after V005).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'app' AND table_name = 'symbols'
    ) THEN
        -- Drop orphan gaps that reference unknown symbols before adding FK.
        DELETE FROM data_gaps g
        WHERE NOT EXISTS (
            SELECT 1 FROM app.symbols s WHERE s.symbol = g.symbol
        );
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'data_gaps_symbol_fkey'
        ) THEN
            ALTER TABLE data_gaps
                ADD CONSTRAINT data_gaps_symbol_fkey
                FOREIGN KEY (symbol) REFERENCES app.symbols (symbol);
        END IF;
    END IF;
END $$;

ALTER TABLE data_gaps
    DROP CONSTRAINT IF EXISTS data_gaps_status_check;
ALTER TABLE data_gaps
    ADD CONSTRAINT data_gaps_status_check
    CHECK (status IN ('open', 'resolved'));

-- At most one open gap per exact (symbol, timeframe, start_ts, end_ts).
CREATE UNIQUE INDEX IF NOT EXISTS uq_data_gaps_open_exact
    ON data_gaps (symbol, timeframe, start_ts, end_ts)
    WHERE status = 'open';
