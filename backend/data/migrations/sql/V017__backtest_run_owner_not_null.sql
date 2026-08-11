-- G2-002: parity with replay/scan — backtest runs must always have an owner.
-- Pre-ownership / orphan rows cannot be attributed; drop so GET cannot leak them.
DELETE FROM app.backtest_runs WHERE user_id IS NULL;

ALTER TABLE app.backtest_runs
    ALTER COLUMN user_id SET NOT NULL;
