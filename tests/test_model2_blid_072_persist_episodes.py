"""Testes de integracao e unidade para BLID-072.

Garante que persist_training_episodes captura episodios com fills,
calcula reward_proxy corretamente e persiste de forma idempotente.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.model2.persist_training_episodes import (
    _ensure_training_episodes_table,
    _reward_label,
    run_persist_training_episodes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_source_db(path: Path) -> None:
    """Cria banco fonte minimo (sem candles) para testes de persist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlcv_h4 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL
            )
            """
        )
        conn.commit()


def _criar_model2_db_com_execucao(
    path: Path,
    *,
    symbol: str = "BTCUSDT",
    side: str = "LONG",
    entry_price: float = 50000.0,
    exit_price: float | None = 55000.0,
    status: str = "CLOSED",
    updated_at_ms: int = 1_700_000_001_000,
) -> int:
    """Cria banco modelo2 com sinal + execucao pre-populados.

    Retorna o ID da execucao criada.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'IDENTIFICADA'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS technical_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_side TEXT NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                signal_timestamp INTEGER,
                status TEXT NOT NULL DEFAULT 'CREATED'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signal_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                technical_signal_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_side TEXT NOT NULL,
                status TEXT NOT NULL,
                entry_filled_at INTEGER,
                exited_at INTEGER,
                exit_price REAL,
                payload_json TEXT,
                updated_at INTEGER NOT NULL
            )
            """
        )
        cur = conn.execute(
            """
            INSERT INTO technical_signals
                (symbol, timeframe, signal_side, entry_price, stop_loss, take_profit, signal_timestamp)
            VALUES (?, 'H4', ?, ?, ?, ?, ?)
            """,
            (symbol, side, entry_price, entry_price * 0.97, entry_price * 1.06, updated_at_ms - 3600_000),
        )
        signal_id = cur.lastrowid

        cur2 = conn.execute(
            """
            INSERT INTO signal_executions
                (technical_signal_id, symbol, timeframe, signal_side, status,
                 entry_filled_at, exited_at, exit_price, payload_json, updated_at)
            VALUES (?, ?, 'H4', ?, ?, ?, ?, ?, '{}', ?)
            """,
            (
                signal_id,
                symbol,
                side,
                status,
                updated_at_ms - 1800_000,
                updated_at_ms if exit_price is not None else None,
                exit_price,
                updated_at_ms,
            ),
        )
        execution_id = cur2.lastrowid
        conn.commit()
    return int(execution_id)


# ---------------------------------------------------------------------------
# Testes de _reward_label
# ---------------------------------------------------------------------------


class TestRewardLabel:
    def test_long_win(self) -> None:
        reward, label = _reward_label("LONG", 100.0, 110.0)
        assert label == "win"
        assert reward == pytest.approx(0.1)

    def test_long_loss(self) -> None:
        reward, label = _reward_label("LONG", 100.0, 90.0)
        assert label == "loss"
        assert reward == pytest.approx(-0.1)

    def test_long_breakeven(self) -> None:
        reward, label = _reward_label("LONG", 100.0, 100.0)
        assert label == "breakeven"
        assert reward == pytest.approx(0.0)

    def test_short_win(self) -> None:
        reward, label = _reward_label("SHORT", 100.0, 90.0)
        assert label == "win"
        assert reward == pytest.approx(0.1)

    def test_short_loss(self) -> None:
        reward, label = _reward_label("SHORT", 100.0, 110.0)
        assert label == "loss"
        assert reward == pytest.approx(-0.1)

    def test_short_breakeven(self) -> None:
        reward, label = _reward_label("SHORT", 100.0, 100.0)
        assert label == "breakeven"
        assert reward == pytest.approx(0.0)

    def test_pending_sem_exit_price(self) -> None:
        reward, label = _reward_label("LONG", 100.0, None)
        assert label == "pending"
        assert reward is None

    def test_pending_sem_entry_price(self) -> None:
        reward, label = _reward_label("LONG", None, 110.0)
        assert label == "pending"
        assert reward is None

    def test_pending_entry_zero(self) -> None:
        reward, label = _reward_label("LONG", 0.0, 110.0)
        assert label == "pending"
        assert reward is None

    def test_side_case_insensitive(self) -> None:
        reward_l, label_l = _reward_label("long", 100.0, 110.0)
        reward_s, label_s = _reward_label("short", 100.0, 90.0)
        assert label_l == "win"
        assert label_s == "win"


# ---------------------------------------------------------------------------
# Testes de _ensure_training_episodes_table
# ---------------------------------------------------------------------------


class TestEnsureTrainingEpisodesTable:
    def test_cria_tabela(self, tmp_path: Path) -> None:
        db = tmp_path / "modelo2.db"
        with sqlite3.connect(db) as conn:
            _ensure_training_episodes_table(conn)
            tabelas = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "training_episodes" in tabelas

    def test_idempotente_segunda_chamada(self, tmp_path: Path) -> None:
        db = tmp_path / "modelo2.db"
        with sqlite3.connect(db) as conn:
            _ensure_training_episodes_table(conn)
            # Nao deve lancar excecao na segunda chamada
            _ensure_training_episodes_table(conn)
        with sqlite3.connect(db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM training_episodes"
            ).fetchone()[0]
        assert count == 0


# ---------------------------------------------------------------------------
# Testes de integracao de run_persist_training_episodes
# ---------------------------------------------------------------------------


class TestRunPersistTrainingEpisodesIntegracao:
    def test_episodio_win_persistido(self, tmp_path: Path) -> None:
        source_db = tmp_path / "source.db"
        model2_db = tmp_path / "modelo2.db"
        output_dir = tmp_path / "runtime"

        _criar_source_db(source_db)
        _criar_model2_db_com_execucao(
            model2_db,
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50_000.0,
            exit_price=55_000.0,
            status="CLOSED",
        )

        summary = run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        assert summary["status"] == "ok"
        assert summary["execution_episodes_persisted"] >= 1

        with sqlite3.connect(model2_db) as conn:
            row = conn.execute(
                "SELECT label, reward_proxy FROM training_episodes WHERE symbol = 'BTCUSDT' AND label = 'win'"
            ).fetchone()
        assert row is not None
        assert row[0] == "win"
        assert float(row[1]) == pytest.approx(0.1)

    def test_episodio_pending_sem_exit_price(self, tmp_path: Path) -> None:
        source_db = tmp_path / "source.db"
        model2_db = tmp_path / "modelo2.db"
        output_dir = tmp_path / "runtime"

        _criar_source_db(source_db)
        _criar_model2_db_com_execucao(
            model2_db,
            symbol="ETHUSDT",
            side="LONG",
            entry_price=3_000.0,
            exit_price=None,
            status="OPEN",
        )

        summary = run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["ETHUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        assert summary["status"] == "ok"
        assert summary["execution_episodes_persisted"] >= 1

        with sqlite3.connect(model2_db) as conn:
            row = conn.execute(
                "SELECT label, reward_proxy FROM training_episodes WHERE symbol = 'ETHUSDT' AND label = 'pending'"
            ).fetchone()
        assert row is not None
        assert row[1] is None

    def test_idempotencia_sem_duplicatas(self, tmp_path: Path) -> None:
        source_db = tmp_path / "source.db"
        model2_db = tmp_path / "modelo2.db"
        output_dir = tmp_path / "runtime"

        _criar_source_db(source_db)
        _criar_model2_db_com_execucao(
            model2_db,
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50_000.0,
            exit_price=55_000.0,
            status="CLOSED",
        )

        run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )
        run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        with sqlite3.connect(model2_db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM training_episodes WHERE symbol = 'BTCUSDT' AND label = 'win'"
            ).fetchone()[0]
        assert count == 1

    def test_gera_jsonl_e_summary(self, tmp_path: Path) -> None:
        source_db = tmp_path / "source.db"
        model2_db = tmp_path / "modelo2.db"
        output_dir = tmp_path / "runtime"

        _criar_source_db(source_db)
        _criar_model2_db_com_execucao(
            model2_db,
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50_000.0,
            exit_price=55_000.0,
            status="CLOSED",
        )

        summary = run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        assert Path(summary["jsonl_file"]).exists()
        assert Path(summary["output_file"]).exists()
        summary_content = json.loads(Path(summary["output_file"]).read_text(encoding="utf-8"))
        assert summary_content["status"] == "ok"

    def test_sem_candle_nao_falha(self, tmp_path: Path) -> None:
        """Com banco fonte sem dados OHLCV, persist continua e usa latest_candle=None."""
        source_db = tmp_path / "source.db"
        model2_db = tmp_path / "modelo2.db"
        output_dir = tmp_path / "runtime"

        _criar_source_db(source_db)  # tabela ohlcv_h4 existe mas vazia
        _criar_model2_db_com_execucao(
            model2_db,
            symbol="BTCUSDT",
            side="SHORT",
            entry_price=50_000.0,
            exit_price=45_000.0,
            status="CLOSED",
        )

        summary = run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        assert summary["status"] == "ok"
        assert summary["execution_episodes_persisted"] >= 1

    def test_features_json_valido(self, tmp_path: Path) -> None:
        """features_json deve ser JSON valido em todos os registros inseridos."""
        source_db = tmp_path / "source.db"
        model2_db = tmp_path / "modelo2.db"
        output_dir = tmp_path / "runtime"

        _criar_source_db(source_db)
        _criar_model2_db_com_execucao(
            model2_db,
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50_000.0,
            exit_price=55_000.0,
            status="CLOSED",
        )

        run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        with sqlite3.connect(model2_db) as conn:
            rows = conn.execute(
                "SELECT features_json, target_json FROM training_episodes WHERE symbol = 'BTCUSDT'"
            ).fetchall()

        assert rows, "Deve haver ao menos um episodio para BTCUSDT"
        for features_json, target_json in rows:
            parsed_f = json.loads(features_json)
            parsed_t = json.loads(target_json)
            assert isinstance(parsed_f, dict)
            assert isinstance(parsed_t, dict)
