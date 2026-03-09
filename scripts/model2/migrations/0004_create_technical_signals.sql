CREATE TABLE IF NOT EXISTS technical_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_side TEXT NOT NULL CHECK (signal_side IN ('LONG', 'SHORT')),
    entry_type TEXT NOT NULL,
    entry_price REAL NOT NULL,
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    signal_timestamp INTEGER NOT NULL CHECK (signal_timestamp > 0),
    status TEXT NOT NULL CHECK (status IN ('CREATED', 'CONSUMED', 'CANCELLED')),
    rule_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL CHECK (created_at > 0),
    updated_at INTEGER NOT NULL CHECK (updated_at >= created_at),
    UNIQUE (opportunity_id),
    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_technical_signals_status
    ON technical_signals (status);

CREATE INDEX IF NOT EXISTS idx_technical_signals_symbol_timeframe
    ON technical_signals (symbol, timeframe);

CREATE INDEX IF NOT EXISTS idx_technical_signals_timestamp
    ON technical_signals (signal_timestamp);
