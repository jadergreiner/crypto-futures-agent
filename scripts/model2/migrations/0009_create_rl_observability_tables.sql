-- Migration 0009: Criar tabelas de suporte para observabilidade RL
-- Propósito: Suportar coleta de métricas de treino e episódios para cycle_report

CREATE TABLE rl_training_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episodes_used INTEGER NOT NULL,
    avg_reward REAL,
    completed_at TEXT NOT NULL,
    model_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rl_training_log_completed_at_desc
    ON rl_training_log (completed_at DESC);

CREATE TABLE rl_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    decision TEXT NOT NULL,
    reward REAL NOT NULL,
    state_json TEXT,
    outcome_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_rl_episodes_created_at
    ON rl_episodes (created_at);

CREATE INDEX idx_rl_episodes_symbol
    ON rl_episodes (symbol);
