"""Suite M2-025.10: snapshot unico por ciclo com candle/decisao/episodio/treino."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from core.model2.cycle_snapshot import CycleSnapshot, CycleSnapshotRepository
from core.model2.observability import Model2ObservabilityService, OperationalSnapshot


def _create_minimal_schema(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS operational_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                candle_json TEXT NOT NULL DEFAULT '{}',
                decisao_json TEXT NOT NULL DEFAULT '{}',
                episodio_json TEXT NOT NULL DEFAULT '{}',
                execucao_json TEXT NOT NULL DEFAULT '{}',
                reconciliacao_json TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS technical_signals (
                id INTEGER PRIMARY KEY,
                opportunity_id INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS signal_executions (
                id INTEGER PRIMARY KEY,
                technical_signal_id INTEGER NOT NULL,
                decision_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS model_decisions (
                id INTEGER PRIMARY KEY,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason_code TEXT NOT NULL,
                model_version TEXT NOT NULL,
                decision_timestamp INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS training_episodes (
                id INTEGER PRIMARY KEY,
                execution_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                status TEXT NOT NULL,
                reward_proxy REAL,
                reward_source TEXT NOT NULL DEFAULT 'none',
                reward_lookup_at_ms INTEGER,
                event_timestamp INTEGER NOT NULL
            );
            """
        )
        conn.commit()


def test_cycle_snapshot_is_frozen_dataclass() -> None:
    snapshot = CycleSnapshot(
        cycle_id="c1",
        candle={"close": 1.0},
        decision={},
        episode={},
        training={},
        updated_at=1,
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.cycle_id = "c2"  # type: ignore[misc]


def test_refresh_cycle_snapshot_aggregates_and_persists_by_cycle_id(tmp_path: Path) -> None:
    db_path = tmp_path / "m2.db"
    _create_minimal_schema(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO opportunities (id, metadata_json) VALUES (?, ?)",
            (1, json.dumps({"cycle_id": "CYCLE-1"})),
        )
        conn.execute("INSERT INTO technical_signals (id, opportunity_id) VALUES (?, ?)", (10, 1))
        conn.execute(
            "INSERT INTO model_decisions (id, action, confidence, reason_code, model_version, decision_timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (100, "OPEN_SHORT", 0.77, "ok", "m2-v1", 1_700_000_000_123),
        )
        conn.execute(
            "INSERT INTO signal_executions (id, technical_signal_id, decision_id) VALUES (?, ?, ?)",
            (20, 10, 100),
        )
        conn.execute(
            "INSERT INTO training_episodes "
            "(id, execution_id, label, status, reward_proxy, reward_source, reward_lookup_at_ms, event_timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (30, 20, "win", "FILLED", 1.25, "reconciliation_fill", 1_700_000_001_000, 1_700_000_000_900),
        )
        conn.execute(
            "INSERT INTO operational_snapshots "
            "(cycle_id, candle_json, decisao_json, episodio_json, execucao_json, reconciliacao_json, created_at) "
            "VALUES (?, ?, ?, ?, '{}', '{}', ?)",
            (
                "CYCLE-1",
                json.dumps({"close": 101.2, "timestamp": 1_700_000_000_000}),
                json.dumps({"allow": True}),
                json.dumps({"episode_id": 30, "execution_id": 20}),
                1_700_000_000_111,
            ),
        )
        conn.commit()

    repo = CycleSnapshotRepository(str(db_path))
    consolidated = repo.refresh_cycle_snapshot(cycle_id="CYCLE-1", now_ms=1_700_000_002_000)

    assert consolidated.cycle_id == "CYCLE-1"
    assert consolidated.candle["close"] == 101.2
    assert consolidated.decision["decision_id"] == 100
    assert consolidated.episode["execution_id"] == 20
    assert consolidated.training["episode_id"] == 30
    assert consolidated.training["reward_source"] == "reconciliation_fill"

    loaded = repo.get_cycle_snapshot("CYCLE-1")
    assert loaded is not None
    assert loaded.training["label"] == "win"
    assert loaded.updated_at == 1_700_000_002_000


def test_refresh_cycle_snapshot_upserts_single_row_per_cycle_id(tmp_path: Path) -> None:
    db_path = tmp_path / "m2.db"
    _create_minimal_schema(db_path)
    repo = CycleSnapshotRepository(str(db_path))

    _ = repo.refresh_cycle_snapshot(
        cycle_id="CYCLE-UNIQUE",
        candle={"close": 10.0},
        now_ms=100,
    )
    _ = repo.refresh_cycle_snapshot(
        cycle_id="CYCLE-UNIQUE",
        candle={"close": 11.0},
        now_ms=200,
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*), candle_json, updated_at FROM cycle_snapshots WHERE cycle_id = ?",
            ("CYCLE-UNIQUE",),
        ).fetchone()
    assert row is not None
    assert int(row[0]) == 1
    assert json.loads(str(row[1]))["close"] == 11.0
    assert int(row[2]) == 200


def test_observability_record_cycle_snapshot_keeps_consolidated_cycle_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "m2.db"
    _create_minimal_schema(db_path)

    service = Model2ObservabilityService(db_path=str(db_path))
    service.record_cycle_snapshot(
        OperationalSnapshot(
            cycle_id="CYCLE-OBS",
            candle_fresco={"close": 120.5, "symbol": "BTCUSDT"},
            decisao={"action": "OPEN_SHORT", "confidence": 0.61},
            episodio={"episode_id": 7},
            execucao={"execution_id": 70},
            reconciliacao={"status": "ok"},
        )
    )

    repo = CycleSnapshotRepository(str(db_path))
    consolidated = repo.get_cycle_snapshot("CYCLE-OBS")
    assert consolidated is not None
    assert consolidated.candle["symbol"] == "BTCUSDT"
    assert consolidated.decision["action"] == "OPEN_SHORT"
    assert consolidated.episode["episode_id"] == 7
