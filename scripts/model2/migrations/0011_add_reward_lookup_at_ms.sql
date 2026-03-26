-- Migration 0011: adiciona coluna reward_lookup_at_ms em training_episodes
-- Idempotente: recria a tabela com a nova coluna via staging + rename
-- (SQLite nao suporta IF NOT EXISTS em ALTER TABLE)
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
    reward_source TEXT NOT NULL DEFAULT 'none',
    features_json TEXT NOT NULL,
    target_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS training_episodes_new (
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
    reward_source TEXT NOT NULL DEFAULT 'none',
    reward_lookup_at_ms INTEGER,
    features_json TEXT NOT NULL,
    target_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
INSERT OR IGNORE INTO training_episodes_new
    (id, episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
     event_timestamp, label, reward_proxy, reward_source, reward_lookup_at_ms,
     features_json, target_json, created_at)
    SELECT id, episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
           event_timestamp, label, reward_proxy, reward_source, NULL,
           features_json, target_json, created_at
    FROM training_episodes;
DROP TABLE IF EXISTS training_episodes;
ALTER TABLE training_episodes_new RENAME TO training_episodes;
CREATE INDEX IF NOT EXISTS idx_training_episodes_lookup
    ON training_episodes(reward_lookup_at_ms)
    WHERE reward_lookup_at_ms IS NOT NULL;
