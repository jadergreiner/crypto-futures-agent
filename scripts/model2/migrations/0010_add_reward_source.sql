-- Migration 0010: adiciona coluna reward_source em training_episodes
-- Idempotente: ALTER TABLE ignora erro se coluna ja existir (SQLite nao suporta IF NOT EXISTS)
-- Executar via: migrate.py up
CREATE TABLE IF NOT EXISTS training_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_key TEXT NOT NULL UNIQUE,
    cycle_run_id TEXT NOT NULL,
    execution_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    status TEXT NOT NULL,
    event_timestamp INTEGER NOT NULL,
    label TEXT NOT NULL,
    reward_proxy REAL,
    features_json TEXT NOT NULL,
    target_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
ALTER TABLE training_episodes ADD COLUMN reward_source TEXT NOT NULL DEFAULT 'none';
