"""
Native SQL for app schema tables (users, symbols, watchlists).
"""

SELECT_SYMBOLS = """
SELECT symbol, base, quote, is_active, sort_order, created_at,
       exchange, tick_size, lot_size, asset_type
FROM app.symbols
WHERE (%s = FALSE OR is_active = TRUE)
ORDER BY sort_order ASC, symbol ASC
"""

SELECT_SYMBOLS_SEARCH = """
SELECT symbol, base, quote, is_active, sort_order, created_at,
       exchange, tick_size, lot_size, asset_type
FROM app.symbols
WHERE (symbol ILIKE %s OR base ILIKE %s)
  AND (%s = FALSE OR is_active = TRUE)
ORDER BY sort_order ASC, symbol ASC
"""

SELECT_SYMBOL_BY_NAME = """
SELECT symbol, base, quote, is_active, sort_order, created_at,
       exchange, tick_size, lot_size, asset_type
FROM app.symbols
WHERE symbol = %s
"""

INSERT_USER = """
INSERT INTO app.users (name, email)
VALUES (%s, %s)
RETURNING id, name, email, created_at, updated_at
"""

SELECT_USERS = """
SELECT id, name, email, created_at, updated_at
FROM app.users
ORDER BY created_at ASC
LIMIT %s OFFSET %s
"""

SELECT_USER_BY_ID = """
SELECT id, name, email, created_at, updated_at
FROM app.users
WHERE id = %s
"""

UPDATE_USER = """
UPDATE app.users
SET name = COALESCE(%s, name),
    email = COALESCE(%s, email),
    updated_at = NOW()
WHERE id = %s
RETURNING id, name, email, created_at, updated_at
"""

DELETE_USER = """
DELETE FROM app.users WHERE id = %s
"""

INSERT_WATCHLIST = """
INSERT INTO app.watchlists (user_id, name, is_default, sort_order)
VALUES (%s, %s, %s, %s)
RETURNING id, user_id, name, is_default, sort_order, created_at
"""

SELECT_WATCHLISTS_BY_USER = """
SELECT id, user_id, name, is_default, sort_order, created_at
FROM app.watchlists
WHERE user_id = %s
ORDER BY sort_order ASC, created_at ASC
"""

SELECT_WATCHLIST_BY_ID = """
SELECT id, user_id, name, is_default, sort_order, created_at
FROM app.watchlists
WHERE id = %s AND user_id = %s
"""

UPDATE_WATCHLIST = """
UPDATE app.watchlists
SET name = COALESCE(%s, name),
    is_default = COALESCE(%s, is_default),
    sort_order = COALESCE(%s, sort_order)
WHERE id = %s AND user_id = %s
RETURNING id, user_id, name, is_default, sort_order, created_at
"""

DELETE_WATCHLIST = """
DELETE FROM app.watchlists WHERE id = %s AND user_id = %s
"""

CLEAR_DEFAULT_WATCHLISTS = """
UPDATE app.watchlists SET is_default = FALSE WHERE user_id = %s
"""

SELECT_WATCHLIST_SYMBOLS = """
SELECT symbol
FROM app.watchlist_symbols
WHERE watchlist_id = %s
ORDER BY sort_order ASC, symbol ASC
"""

DELETE_WATCHLIST_SYMBOLS = """
DELETE FROM app.watchlist_symbols WHERE watchlist_id = %s
"""

INSERT_WATCHLIST_SYMBOL = """
INSERT INTO app.watchlist_symbols (watchlist_id, symbol, sort_order)
VALUES (%s, %s, %s)
"""
