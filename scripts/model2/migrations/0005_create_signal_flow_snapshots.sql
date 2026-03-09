CREATE TABLE IF NOT EXISTS signal_flow_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    snapshot_timestamp INTEGER NOT NULL CHECK (snapshot_timestamp > 0),
    created_count INTEGER NOT NULL CHECK (created_count >= 0),
    consumed_count INTEGER NOT NULL CHECK (consumed_count >= 0),
    cancelled_count INTEGER NOT NULL CHECK (cancelled_count >= 0),
    exported_count INTEGER NOT NULL CHECK (exported_count >= 0),
    consumed_not_exported_count INTEGER NOT NULL CHECK (consumed_not_exported_count >= 0),
    export_error_count INTEGER NOT NULL CHECK (export_error_count >= 0),
    export_rate REAL,
    avg_created_to_consumed_ms REAL,
    avg_consumed_to_exported_ms REAL,
    avg_created_to_exported_ms REAL,
    created_at INTEGER NOT NULL CHECK (created_at > 0)
);

CREATE INDEX IF NOT EXISTS idx_signal_flow_snapshots_run
    ON signal_flow_snapshots (run_id, snapshot_timestamp);

CREATE INDEX IF NOT EXISTS idx_signal_flow_snapshots_ts
    ON signal_flow_snapshots (snapshot_timestamp);
