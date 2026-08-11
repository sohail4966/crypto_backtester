-- BE-L2-015: enforce non-overlapping open data_gap ranges at the DB level.
--
-- V014 added a unique index on (symbol, timeframe, start_ts, end_ts) WHERE
-- status='open' which stops exact duplicates. Distinct-but-overlapping ranges
-- still race between concurrent reconcile_gaps callers. This migration adds a
-- gist EXCLUDE constraint using btree_gist for the equality columns and
-- tstzrange for the timestamp overlap check.
--
-- Overlap semantics match app-level ``_ranges_overlap``: two ranges overlap if
-- ``a.start <= b.end AND b.start <= a.end`` (inclusive endpoints). ``tstzrange``
-- with the ``'[]'`` bounds encodes exactly this.
--
-- Requires ``btree_gist`` (Timescale Cloud + stock Postgres 13+ ship with it).

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Pre-clean any residual overlapping open rows so ADD CONSTRAINT succeeds.
-- (V014 already dedup'd exact duplicates; this handles the wider overlap case.)
DELETE FROM data_gaps a
USING data_gaps b
WHERE a.status = 'open'
  AND b.status = 'open'
  AND a.symbol = b.symbol
  AND a.timeframe = b.timeframe
  AND a.id > b.id
  AND a.start_ts <= b.end_ts
  AND b.start_ts <= a.end_ts;

ALTER TABLE data_gaps
    DROP CONSTRAINT IF EXISTS data_gaps_no_open_overlap;

ALTER TABLE data_gaps
    ADD CONSTRAINT data_gaps_no_open_overlap
    EXCLUDE USING gist (
        symbol WITH =,
        timeframe WITH =,
        tstzrange(start_ts, end_ts, '[]') WITH &&
    ) WHERE (status = 'open');
