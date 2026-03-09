CREATE TABLE IF NOT EXISTS signal_execution_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    snapshot_timestamp INTEGER NOT NULL CHECK (snapshot_timestamp > 0),
    ready_count INTEGER NOT NULL CHECK (ready_count >= 0),
    blocked_count INTEGER NOT NULL CHECK (blocked_count >= 0),
    entry_sent_count INTEGER NOT NULL CHECK (entry_sent_count >= 0),
    entry_filled_count INTEGER NOT NULL CHECK (entry_filled_count >= 0),
    protected_count INTEGER NOT NULL CHECK (protected_count >= 0),
    exited_count INTEGER NOT NULL CHECK (exited_count >= 0),
    failed_count INTEGER NOT NULL CHECK (failed_count >= 0),
    cancelled_count INTEGER NOT NULL CHECK (cancelled_count >= 0),
    unprotected_filled_count INTEGER NOT NULL CHECK (unprotected_filled_count >= 0),
    stale_entry_sent_count INTEGER NOT NULL CHECK (stale_entry_sent_count >= 0),
    open_position_mismatches_count INTEGER NOT NULL CHECK (open_position_mismatches_count >= 0),
    avg_signal_to_entry_sent_ms REAL,
    avg_entry_sent_to_filled_ms REAL,
    avg_filled_to_protected_ms REAL,
    created_at INTEGER NOT NULL CHECK (created_at > 0)
);

CREATE INDEX IF NOT EXISTS idx_signal_execution_snapshots_run
    ON signal_execution_snapshots (run_id, snapshot_timestamp);

CREATE INDEX IF NOT EXISTS idx_signal_execution_snapshots_ts
    ON signal_execution_snapshots (snapshot_timestamp);
