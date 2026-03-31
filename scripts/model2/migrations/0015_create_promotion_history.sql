-- M2-028.2: trilha auditavel para promocao/reversao paper->live
CREATE TABLE IF NOT EXISTS promotion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL UNIQUE,
    evaluated_at TEXT NOT NULL,
    go_no_go TEXT NOT NULL CHECK (go_no_go IN ('GO', 'NO_GO')),
    reasons TEXT NOT NULL,
    sharpe_ratio REAL NOT NULL,
    reconciliation_rate REAL NOT NULL,
    critical_errors INTEGER NOT NULL,
    manual_approved INTEGER NOT NULL CHECK (manual_approved IN (0, 1)),
    approver_id TEXT,
    approval_justification TEXT,
    rollback_to_paper INTEGER NOT NULL DEFAULT 0
        CHECK (rollback_to_paper IN (0, 1)),
    event_type TEXT NOT NULL DEFAULT 'EVALUATION'
        CHECK (event_type IN ('EVALUATION', 'ROLLBACK_EVENT')),
    created_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_promotion_history_evaluated_at
    ON promotion_history (evaluated_at DESC);

CREATE INDEX IF NOT EXISTS idx_promotion_history_event_type
    ON promotion_history (event_type);
