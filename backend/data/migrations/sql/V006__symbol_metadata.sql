-- Phase 4b: structured symbol metadata for frontend (D-86)

ALTER TABLE app.symbols
    ADD COLUMN IF NOT EXISTS exchange TEXT NOT NULL DEFAULT 'binance',
    ADD COLUMN IF NOT EXISTS tick_size NUMERIC NOT NULL DEFAULT 0.01,
    ADD COLUMN IF NOT EXISTS lot_size NUMERIC NOT NULL DEFAULT 0.0001,
    ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'spot';

UPDATE app.symbols
SET tick_size = 0.01,
    lot_size = 0.00001,
    exchange = 'binance',
    asset_type = 'spot'
WHERE symbol = 'BTC/USDT';

UPDATE app.symbols
SET tick_size = 0.01,
    lot_size = 0.0001,
    exchange = 'binance',
    asset_type = 'spot'
WHERE symbol = 'ETH/USDT';

UPDATE app.symbols
SET tick_size = 0.01,
    lot_size = 0.01,
    exchange = 'binance',
    asset_type = 'spot'
WHERE symbol = 'SOL/USDT';
