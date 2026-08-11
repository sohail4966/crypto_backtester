-- BE-L2-001: swap backtest_runs.user_id FK action from ON DELETE SET NULL (V008)
-- to ON DELETE CASCADE. V017 made user_id NOT NULL, so SET NULL now aborts every
-- DELETE FROM app.users. This mirrors the ownership-cascade already used by
-- app.replay_sessions (V011), app.scan_runs (V016), app.ai_clarify_sessions (V013)
-- and app.watchlists (V012). See docs/runbooks/V017_backfill.md for the
-- destructive semantics that V017 introduced.

ALTER TABLE app.backtest_runs
    DROP CONSTRAINT backtest_runs_user_id_fkey;

ALTER TABLE app.backtest_runs
    ADD CONSTRAINT backtest_runs_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES app.users (id)
    ON DELETE CASCADE;
