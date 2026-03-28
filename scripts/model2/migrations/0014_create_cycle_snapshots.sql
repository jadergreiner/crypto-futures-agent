-- M2-025.10: snapshot unico por cycle_id para candle, decisao, episodio e treino
CREATE TABLE IF NOT EXISTS cycle_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL UNIQUE,
    candle_json TEXT NOT NULL DEFAULT '{}',
    decisao_json TEXT NOT NULL DEFAULT '{}',
    episodio_json TEXT NOT NULL DEFAULT '{}',
    treino_json TEXT NOT NULL DEFAULT '{}',
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cycle_snapshots_updated_at
    ON cycle_snapshots (updated_at DESC);
