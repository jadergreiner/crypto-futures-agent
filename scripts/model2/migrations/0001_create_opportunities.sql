CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    thesis_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('IDENTIFICADA', 'MONITORANDO', 'VALIDADA', 'INVALIDADA', 'EXPIRADA')),
    zone_low REAL NOT NULL,
    zone_high REAL NOT NULL,
    trigger_price REAL NOT NULL,
    invalidation_price REAL NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    resolved_at INTEGER,
    resolution_reason TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    CHECK (zone_low < zone_high),
    CHECK (updated_at >= created_at),
    CHECK (expires_at >= created_at),
    CHECK (resolved_at IS NULL OR resolved_at >= created_at)
);

CREATE INDEX IF NOT EXISTS idx_opportunities_status
    ON opportunities (status);

CREATE INDEX IF NOT EXISTS idx_opportunities_symbol_status
    ON opportunities (symbol, status);

CREATE INDEX IF NOT EXISTS idx_opportunities_created_at
    ON opportunities (created_at);
