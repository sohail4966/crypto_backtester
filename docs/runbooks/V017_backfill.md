# Runbook: V017 backtest-runs owner backfill

**Migration:** `backend/data/migrations/sql/V017__backtest_run_owner_not_null.sql`

**Companion migration:** `V018__backtest_runs_fk_cascade.sql` (BE-L2-001) — swap the
`backtest_runs.user_id` FK from `ON DELETE SET NULL` (V008) to `ON DELETE CASCADE`
so `DELETE /users/{id}` no longer aborts on V017's `NOT NULL` constraint.

## What V017 does

- `DELETE FROM app.backtest_runs WHERE user_id IS NULL;`
- `ALTER TABLE app.backtest_runs ALTER COLUMN user_id SET NOT NULL;`

Both statements run inside the standard migrator transaction. Any pre-ownership
rows (backfilled runs, imports, or rows created before Phase 11 auth landed) are
deleted before the constraint is added.

**This is intentional and destructive.** V017 formalises the ownership-only
model that already applies to scans, replay sessions, and watchlists.

## Who is affected

- Environments that ran the app before Phase 11 (auth) landed.
- Environments that imported backtest history from CSV / another instance
  without setting `user_id`.
- Environments that manually inserted rows for QA / demos without a matching
  `app.users` record.

Fresh environments (created after Phase 11) never had orphan rows and are
unaffected.

## Pre-flight archive (recommended)

Run **before** applying V017 in any environment where orphan runs must survive:

```bash
psql "$DATABASE_URL" -f backend/ops/scripts/archive_orphan_backtests.sql
```

The script:

1. Creates `app.backtest_runs_archive` (same shape as `app.backtest_runs`) if
   it does not exist.
2. Inserts every row where `user_id IS NULL` into the archive, preserving
   original ids and timestamps.
3. Prints how many rows were archived so ops can sanity-check.

After the archive, apply migrations normally (`python -m backend.data.migrations`
or a service restart that triggers `run_migrations_on_startup`).

## Post-fact recovery (V017 already applied)

If V017 has already run in your environment and you need historical rows back:

1. Locate the most recent Postgres logical backup that predates the V017 cutover.
2. Restore that backup into a scratch database.
3. Export the orphan rows into a CSV:

   ```sql
   \copy (
       SELECT * FROM app.backtest_runs WHERE user_id IS NULL
   ) TO 'orphan_backtests.csv' WITH CSV HEADER
   ```
4. Load into `app.backtest_runs_archive` in the live database:

   ```sql
   \copy app.backtest_runs_archive FROM 'orphan_backtests.csv' WITH CSV HEADER
   ```

No production read paths query the archive; it is a compliance-only landing
zone. Re-attribution requires an operator with an owning `user_id`.

## Interaction with V018

V018 (`ON DELETE CASCADE`) was introduced as part of BE-L2-001 because V017's
`NOT NULL` constraint made `DELETE FROM app.users` fail against V008's
`ON DELETE SET NULL`. With V018 applied, cascading a user delete now removes all
of that user's `backtest_runs` transactionally. Ops runbooks that rely on
soft-deleting users (rare) should archive first, then delete.
