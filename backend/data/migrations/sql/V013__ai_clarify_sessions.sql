-- BE-020: durable AI clarification sessions bound to users
CREATE TABLE IF NOT EXISTS app.ai_clarify_sessions (
    session_id   UUID PRIMARY KEY,
    user_id      UUID NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
    text         TEXT NOT NULL,
    questions    JSONB NOT NULL DEFAULT '[]',
    answers      JSONB NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_clarify_sessions_user
    ON app.ai_clarify_sessions (user_id);

CREATE INDEX IF NOT EXISTS idx_ai_clarify_sessions_expires
    ON app.ai_clarify_sessions (expires_at);
