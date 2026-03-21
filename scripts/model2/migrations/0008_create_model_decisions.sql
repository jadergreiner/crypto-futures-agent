CREATE TABLE IF NOT EXISTS model_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_timestamp INTEGER NOT NULL CHECK (decision_timestamp > 0),
    symbol TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('OPEN_LONG', 'OPEN_SHORT', 'HOLD', 'REDUCE', 'CLOSE')),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    size_fraction REAL NOT NULL CHECK (size_fraction >= 0.0 AND size_fraction <= 1.0),
    sl_target REAL,
    tp_target REAL,
    model_version TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    inference_latency_ms INTEGER NOT NULL CHECK (inference_latency_ms >= 0),
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL CHECK (created_at > 0)
);

CREATE INDEX IF NOT EXISTS idx_model_decisions_symbol_ts
    ON model_decisions (symbol, decision_timestamp);

CREATE INDEX IF NOT EXISTS idx_model_decisions_model_version
    ON model_decisions (model_version);

ALTER TABLE signal_executions
    ADD COLUMN decision_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_signal_executions_decision_id
    ON signal_executions (decision_id);
