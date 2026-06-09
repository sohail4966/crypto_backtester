CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.symbols (
    symbol      TEXT PRIMARY KEY,
    base        TEXT             NOT NULL,
    quote       TEXT             NOT NULL,
    is_active   BOOLEAN          NOT NULL DEFAULT TRUE,
    sort_order  INTEGER          NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

INSERT INTO app.symbols (symbol, base, quote, sort_order)
VALUES
    ('BTC/USDT', 'BTC', 'USDT', 1),
    ('ETH/USDT', 'ETH', 'USDT', 2),
    ('SOL/USDT', 'SOL', 'USDT', 3)
ON CONFLICT (symbol) DO NOTHING;

CREATE TABLE IF NOT EXISTS app.users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT             NOT NULL,
    email       TEXT             NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.watchlists (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID             NOT NULL REFERENCES app.users (id) ON DELETE CASCADE,
    name        TEXT             NOT NULL,
    is_default  BOOLEAN          NOT NULL DEFAULT FALSE,
    sort_order  INTEGER          NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.watchlist_symbols (
    watchlist_id UUID NOT NULL REFERENCES app.watchlists (id) ON DELETE CASCADE,
    symbol       TEXT NOT NULL REFERENCES app.symbols (symbol),
    sort_order   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (watchlist_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON app.watchlists (user_id);
