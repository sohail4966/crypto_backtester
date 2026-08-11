-- G2-002: parity with replay/scan — backtest runs must always have an owner.
-- Pre-ownership / orphan rows cannot be attributed; drop so GET cannot leak them.
--
-- WARNING (BE-L2-016): this migration is destructive. It deletes any
-- backtest_runs whose ``user_id`` is NULL (pre-ownership orphans). Historical
-- backtest analytics attributable to already-deleted users vanish once this
-- runs. Environments that need to preserve orphan runs MUST execute
-- ``ops/scripts/archive_orphan_backtests.sql`` BEFORE deploying this migration.
-- See ``docs/runbooks/V017_backfill.md`` for the full pre-flight procedure.
--
-- Pair with V018 (``ON DELETE CASCADE`` on backtest_runs.user_id) so
-- ``DELETE /users/{id}`` no longer aborts on this NOT NULL constraint.
DELETE FROM app.backtest_runs WHERE user_id IS NULL;

ALTER TABLE app.backtest_runs
    ALTER COLUMN user_id SET NOT NULL;
