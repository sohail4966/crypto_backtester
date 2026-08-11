ALTER TABLE app.users
    ADD COLUMN IF NOT EXISTS password_hash TEXT;
