CREATE TABLE IF NOT EXISTS opportunity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    event_timestamp INTEGER NOT NULL,
    rule_id TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    CHECK (
        from_status IS NULL OR
        from_status IN ('IDENTIFICADA', 'MONITORANDO', 'VALIDADA', 'INVALIDADA', 'EXPIRADA')
    ),
    CHECK (
        to_status IN ('IDENTIFICADA', 'MONITORANDO', 'VALIDADA', 'INVALIDADA', 'EXPIRADA')
    ),
    CHECK (event_timestamp > 0),
    FOREIGN KEY (opportunity_id)
        REFERENCES opportunities(id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_events_opportunity_ts
    ON opportunity_events (opportunity_id, event_timestamp);

CREATE INDEX IF NOT EXISTS idx_events_event_type
    ON opportunity_events (event_type);
