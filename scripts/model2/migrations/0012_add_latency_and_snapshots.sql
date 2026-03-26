-- M2-024.6: Telemetria de latencia por simbolo e etapa
CREATE TABLE IF NOT EXISTS execution_latencies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    stage       TEXT    NOT NULL,
    result_code TEXT    NOT NULL DEFAULT 'ok',
    latency_ms  INTEGER NOT NULL,
    created_at  INTEGER NOT NULL
);

-- M2-024.9: Snapshot operacional unico por ciclo
CREATE TABLE IF NOT EXISTS operational_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id        TEXT,
    candle_json     TEXT    NOT NULL DEFAULT '{}',
    decisao_json    TEXT    NOT NULL DEFAULT '{}',
    episodio_json   TEXT    NOT NULL DEFAULT '{}',
    execucao_json   TEXT    NOT NULL DEFAULT '{}',
    reconciliacao_json TEXT NOT NULL DEFAULT '{}',
    created_at      INTEGER NOT NULL
);
