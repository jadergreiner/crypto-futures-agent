CREATE TABLE IF NOT EXISTS signal_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technical_signal_id INTEGER NOT NULL UNIQUE,
    opportunity_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_side TEXT NOT NULL CHECK (signal_side IN ('LONG', 'SHORT')),
    execution_mode TEXT NOT NULL CHECK (execution_mode IN ('shadow', 'live')),
    status TEXT NOT NULL CHECK (status IN ('READY', 'BLOCKED', 'ENTRY_SENT', 'ENTRY_FILLED', 'PROTECTED', 'EXITED', 'FAILED', 'CANCELLED')),
    entry_order_type TEXT NOT NULL CHECK (entry_order_type IN ('MARKET')),
    gate_reason TEXT,
    exchange_order_id TEXT,
    client_order_id TEXT,
    requested_qty REAL,
    filled_qty REAL,
    filled_price REAL,
    stop_order_id TEXT,
    take_profit_order_id TEXT,
    entry_sent_at INTEGER,
    entry_filled_at INTEGER,
    protected_at INTEGER,
    exited_at INTEGER,
    exit_reason TEXT,
    exit_price REAL,
    failure_reason TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL CHECK (created_at > 0),
    updated_at INTEGER NOT NULL CHECK (updated_at >= created_at),
    CHECK (requested_qty IS NULL OR requested_qty > 0),
    CHECK (filled_qty IS NULL OR filled_qty > 0),
    CHECK (filled_price IS NULL OR filled_price > 0),
    CHECK (entry_sent_at IS NULL OR entry_sent_at > 0),
    CHECK (entry_filled_at IS NULL OR entry_filled_at > 0),
    CHECK (protected_at IS NULL OR protected_at > 0),
    CHECK (exited_at IS NULL OR exited_at > 0),
    FOREIGN KEY (technical_signal_id)
        REFERENCES technical_signals(id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,
    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_signal_executions_status
    ON signal_executions (status);

CREATE INDEX IF NOT EXISTS idx_signal_executions_symbol_status
    ON signal_executions (symbol, status);

CREATE INDEX IF NOT EXISTS idx_signal_executions_updated_at
    ON signal_executions (updated_at);

CREATE INDEX IF NOT EXISTS idx_signal_executions_mode_status
    ON signal_executions (execution_mode, status);

CREATE TABLE IF NOT EXISTS signal_execution_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_execution_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT CHECK (
        from_status IS NULL OR
        from_status IN ('READY', 'BLOCKED', 'ENTRY_SENT', 'ENTRY_FILLED', 'PROTECTED', 'EXITED', 'FAILED', 'CANCELLED')
    ),
    to_status TEXT CHECK (
        to_status IS NULL OR
        to_status IN ('READY', 'BLOCKED', 'ENTRY_SENT', 'ENTRY_FILLED', 'PROTECTED', 'EXITED', 'FAILED', 'CANCELLED')
    ),
    event_timestamp INTEGER NOT NULL CHECK (event_timestamp > 0),
    rule_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (signal_execution_id)
        REFERENCES signal_executions(id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_signal_execution_events_execution_ts
    ON signal_execution_events (signal_execution_id, event_timestamp);

CREATE INDEX IF NOT EXISTS idx_signal_execution_events_type
    ON signal_execution_events (event_type);
