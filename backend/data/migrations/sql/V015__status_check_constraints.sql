-- BE-022: CHECK constraints on status/state columns
-- Allowed literals mirror application constants.

-- Replay sessions
ALTER TABLE app.replay_sessions
    DROP CONSTRAINT IF EXISTS replay_sessions_state_check;
ALTER TABLE app.replay_sessions
    ADD CONSTRAINT replay_sessions_state_check
    CHECK (state IN ('idle', 'playing', 'paused', 'completed'));

-- Backtest runs
ALTER TABLE app.backtest_runs
    DROP CONSTRAINT IF EXISTS backtest_runs_status_check;
ALTER TABLE app.backtest_runs
    ADD CONSTRAINT backtest_runs_status_check
    CHECK (status IN ('completed', 'failed', 'running'));

-- Scan runs
ALTER TABLE app.scan_runs
    DROP CONSTRAINT IF EXISTS scan_runs_status_check;
ALTER TABLE app.scan_runs
    ADD CONSTRAINT scan_runs_status_check
    CHECK (status IN ('completed', 'failed', 'running'));
