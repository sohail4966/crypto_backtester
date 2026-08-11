-- G-004: bind scan runs to owning user for IDOR-safe GET
ALTER TABLE app.scan_runs
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES app.users (id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_scan_runs_user_id
    ON app.scan_runs (user_id);

-- Pre-ownership rows cannot be attributed; drop so GET cannot leak them.
DELETE FROM app.scan_runs WHERE user_id IS NULL;

ALTER TABLE app.scan_runs
    ALTER COLUMN user_id SET NOT NULL;
