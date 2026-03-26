-- Migração 0013: Criar tabela audit_decision_execution para M2-026.3
-- Auditoria imutável de correlação decision_id ↔ execution_id ↔ signal_id
-- INSERT-only: sem UPDATE ou DELETE permitidos pela lógica de aplicação

CREATE TABLE IF NOT EXISTS audit_decision_execution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL,
    execution_id INTEGER NOT NULL,
    signal_id INTEGER NOT NULL,
    timestamp_utc TEXT NOT NULL,
    decision_status TEXT NOT NULL,
    execution_status TEXT NOT NULL,
    error_reason TEXT,
    additional_context TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_decision_id
    ON audit_decision_execution (decision_id);

CREATE INDEX IF NOT EXISTS idx_audit_execution_id
    ON audit_decision_execution (execution_id);

CREATE INDEX IF NOT EXISTS idx_audit_signal_id
    ON audit_decision_execution (signal_id);
