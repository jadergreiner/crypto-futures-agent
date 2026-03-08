CREATE TABLE IF NOT EXISTS opportunity_dashboard_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    snapshot_timestamp INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('IDENTIFICADA', 'MONITORANDO', 'VALIDADA', 'INVALIDADA', 'EXPIRADA')),
    opportunity_count INTEGER NOT NULL CHECK (opportunity_count >= 0),
    avg_resolution_ms REAL,
    avg_resolution_ms_overall REAL,
    created_at INTEGER NOT NULL,
    CHECK (snapshot_timestamp > 0),
    CHECK (created_at > 0)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_run_status
    ON opportunity_dashboard_snapshots (run_id, status);

CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_ts
    ON opportunity_dashboard_snapshots (snapshot_timestamp);

CREATE TABLE IF NOT EXISTS opportunity_audit_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    snapshot_timestamp INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    opportunity_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT CHECK (
        from_status IS NULL OR
        from_status IN ('IDENTIFICADA', 'MONITORANDO', 'VALIDADA', 'INVALIDADA', 'EXPIRADA')
    ),
    to_status TEXT NOT NULL CHECK (to_status IN ('IDENTIFICADA', 'MONITORANDO', 'VALIDADA', 'INVALIDADA', 'EXPIRADA')),
    event_timestamp INTEGER NOT NULL,
    rule_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    CHECK (snapshot_timestamp > 0),
    CHECK (event_timestamp > 0),
    CHECK (created_at > 0)
);

CREATE INDEX IF NOT EXISTS idx_audit_snapshot_run
    ON opportunity_audit_snapshots (run_id, event_timestamp DESC, event_id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_snapshot_ts
    ON opportunity_audit_snapshots (snapshot_timestamp);

CREATE INDEX IF NOT EXISTS idx_audit_snapshot_opportunity
    ON opportunity_audit_snapshots (opportunity_id, event_timestamp DESC);
