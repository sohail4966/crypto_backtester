CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    description TEXT             NOT NULL,
    applied_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);
