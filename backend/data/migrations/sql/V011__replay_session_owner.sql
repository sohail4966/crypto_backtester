-- BE-006 / G-007: bind replay sessions to owning user (NOT NULL)
ALTER TABLE app.replay_sessions
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES app.users (id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_replay_sessions_user_id
    ON app.replay_sessions (user_id);

-- Orphan sessions (pre-auth) are not usable once ownership is enforced.
DELETE FROM app.replay_sessions WHERE user_id IS NULL;

ALTER TABLE app.replay_sessions
    ALTER COLUMN user_id SET NOT NULL;
