-- Pre-flight archive helper for V017__backtest_run_owner_not_null.sql (BE-L2-016).
--
-- Copy this script into your ops pipeline and run it BEFORE V017 lands in any
-- environment where pre-ownership backtest_runs must survive. See
-- docs/runbooks/V017_backfill.md for the full procedure.
--
-- Usage:
--     psql "$DATABASE_URL" -f backend/ops/scripts/archive_orphan_backtests.sql
--
-- Idempotent: safe to run multiple times. If V017 has already applied,
-- no rows will be archived (there are no NULL user_ids left) and the script
-- exits cleanly.

BEGIN;

CREATE TABLE IF NOT EXISTS app.backtest_runs_archive (
    LIKE app.backtest_runs INCLUDING DEFAULTS INCLUDING CONSTRAINTS
);

-- Drop any inherited FK back to app.users; archived rows are intentionally
-- unattributed and must survive even when the owning user is gone.
ALTER TABLE app.backtest_runs_archive
    DROP CONSTRAINT IF EXISTS backtest_runs_user_id_fkey;

-- Widen user_id back to nullable in the archive so orphans can land.
ALTER TABLE app.backtest_runs_archive
    ALTER COLUMN user_id DROP NOT NULL;

INSERT INTO app.backtest_runs_archive
SELECT * FROM app.backtest_runs
WHERE user_id IS NULL
ON CONFLICT (run_id) DO NOTHING;

-- Emit an operator-visible summary of what was archived this run.
DO $$
DECLARE
    archived_count BIGINT;
BEGIN
    SELECT COUNT(*) INTO archived_count FROM app.backtest_runs WHERE user_id IS NULL;
    RAISE NOTICE 'archive_orphan_backtests: % orphan row(s) present in app.backtest_runs (see app.backtest_runs_archive for copies)', archived_count;
END $$;

COMMIT;
