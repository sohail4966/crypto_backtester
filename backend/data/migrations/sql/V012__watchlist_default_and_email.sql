-- BE-014: one default watchlist per user
-- BE-015 / G-005: case-insensitive unique emails (safe collision dedupe)

-- Deduplicate multiple defaults: keep oldest as default.
UPDATE app.watchlists w
SET is_default = FALSE
WHERE w.is_default = TRUE
  AND w.id <> (
      SELECT w2.id
      FROM app.watchlists w2
      WHERE w2.user_id = w.user_id
        AND w2.is_default = TRUE
      ORDER BY w2.created_at ASC
      LIMIT 1
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_watchlists_one_default_per_user
    ON app.watchlists (user_id)
    WHERE is_default;

-- Resolve lower(email) collisions before unique index: keep oldest row's
-- lower(email); rename later rows to lower(email)||'+dupN' (ops cleanup).
WITH ranked AS (
    SELECT
        id,
        lower(email) AS email_lower,
        ROW_NUMBER() OVER (
            PARTITION BY lower(email)
            ORDER BY created_at ASC, id ASC
        ) AS rn
    FROM app.users
)
UPDATE app.users u
SET email = ranked.email_lower || '+dup' || ranked.rn::text
FROM ranked
WHERE u.id = ranked.id
  AND ranked.rn > 1;

-- Normalize remaining emails to lowercase.
UPDATE app.users
SET email = lower(email)
WHERE email <> lower(email);

-- Drop case-sensitive unique if present and recreate on lower(email).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_email_key'
          AND conrelid = 'app.users'::regclass
    ) THEN
        ALTER TABLE app.users DROP CONSTRAINT users_email_key;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower
    ON app.users (lower(email));
