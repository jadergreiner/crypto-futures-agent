"""Testes RED — BLID-091: reward_source em training_episodes.

Cobre R1-R5 conforme handoff SA. Todos os testes devem FALHAR antes
da implementacao (fase RED do ciclo TDD).
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _make_model2_db(path: str) -> sqlite3.Connection:
    """Cria schema minimo do modelo2.db em memoria ou arquivo."""
    conn = sqlite3.connect(path)
    conn.executescript(
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
            status TEXT NOT NULL DEFAULT 'CREATED',
            created_at INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS signal_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            technical_signal_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            signal_side TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            entry_filled_at INTEGER,
            exited_at INTEGER,
            exit_price REAL,
            payload_json TEXT
        );

        CREATE TABLE IF NOT EXISTS rl_training_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episodes_used INTEGER NOT NULL,
            avg_reward REAL,
            completed_at TEXT NOT NULL,
            model_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    return conn


def _make_source_db(path: str) -> None:
    """Cria schema minimo do crypto_agent.db (OHLCV)."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ohlcv_h4 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL
        );
        INSERT INTO ohlcv_h4 (symbol, timestamp, open, high, low, close, volume)
        VALUES ('BTCUSDT', 1700000000000, 42000.0, 43000.0, 41000.0, 42500.0, 1000.0);
        """
    )
    conn.commit()
    conn.close()


def _insert_signal(conn: sqlite3.Connection, **kwargs: Any) -> int:
    cur = conn.execute(
        """
        INSERT INTO technical_signals
            (symbol, timeframe, signal_side, entry_price, stop_loss, take_profit,
             signal_timestamp, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            kwargs.get("symbol", "BTCUSDT"),
            kwargs.get("timeframe", "H4"),
            kwargs.get("signal_side", "LONG"),
            kwargs.get("entry_price", 42000.0),
            kwargs.get("stop_loss", 41000.0),
            kwargs.get("take_profit", 44000.0),
            kwargs.get("signal_timestamp", 1700000000000),
            kwargs.get("status", "CONSUMED"),
            kwargs.get("created_at", 1700000000000),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def _insert_execution(conn: sqlite3.Connection, signal_id: int, **kwargs: Any) -> int:
    cur = conn.execute(
        """
        INSERT INTO signal_executions
            (technical_signal_id, symbol, timeframe, signal_side, status,
             updated_at, entry_filled_at, exited_at, exit_price, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal_id,
            kwargs.get("symbol", "BTCUSDT"),
            kwargs.get("timeframe", "H4"),
            kwargs.get("signal_side", "LONG"),
            kwargs.get("status", "EXITED"),
            kwargs.get("updated_at", 1700001000000),
            kwargs.get("entry_filled_at", 1700000500000),
            kwargs.get("exited_at", 1700001000000),
            kwargs.get("exit_price", 43500.0),
            kwargs.get("payload_json", "{}"),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


# ---------------------------------------------------------------------------
# R3 — _reward_label calcula reward_source correto
# ---------------------------------------------------------------------------

class TestRewardLabel:
    """R3: _reward_label retorna reward_source correto para LONG e SHORT."""

    def test_reward_label_long_profit_returns_pnl_realized(self) -> None:
        """R3-LONG: entry=100, exit=110 => reward=0.1, reward_source='pnl_realized'."""
        from scripts.model2.persist_training_episodes import _reward_label

        # Arrange
        side = "LONG"
        entry_price = 100.0
        exit_price = 110.0

        # Act
        reward, label, reward_source = _reward_label(side, entry_price, exit_price)

        # Assert
        assert reward is not None
        assert abs(reward - 0.10) < 1e-9, f"Esperado 0.10, obtido {reward}"
        assert label == "win"
        assert reward_source == "pnl_realized"

    def test_reward_label_short_profit_returns_pnl_realized(self) -> None:
        """R3-SHORT: entry=100, exit=90 => reward=0.1, reward_source='pnl_realized'."""
        from scripts.model2.persist_training_episodes import _reward_label

        # Arrange
        side = "SHORT"
        entry_price = 100.0
        exit_price = 90.0

        # Act
        reward, label, reward_source = _reward_label(side, entry_price, exit_price)

        # Assert
        assert reward is not None
        assert abs(reward - 0.10) < 1e-9, f"Esperado 0.10, obtido {reward}"
        assert label == "win"
        assert reward_source == "pnl_realized"

    def test_reward_label_long_loss_returns_pnl_realized(self) -> None:
        """R3-LONG loss: exit < entry => reward negativo, reward_source='pnl_realized'."""
        from scripts.model2.persist_training_episodes import _reward_label

        reward, label, reward_source = _reward_label("LONG", 100.0, 90.0)

        assert reward is not None
        assert reward < 0
        assert label == "loss"
        assert reward_source == "pnl_realized"

    def test_reward_label_missing_exit_returns_none_reward_source(self) -> None:
        """R3-pending: exit=None => reward=None, reward_source='none'."""
        from scripts.model2.persist_training_episodes import _reward_label

        reward, label, reward_source = _reward_label("LONG", 100.0, None)

        assert reward is None
        assert label == "pending"
        assert reward_source == "none"

    def test_reward_label_missing_entry_returns_none_reward_source(self) -> None:
        """R3-pending: entry=None => reward=None, reward_source='none'."""
        from scripts.model2.persist_training_episodes import _reward_label

        reward, label, reward_source = _reward_label("LONG", None, 110.0)

        assert reward is None
        assert reward_source == "none"

    def test_reward_label_zero_entry_returns_none_reward_source(self) -> None:
        """R3-pending: entry=0 (invalido) => reward=None, reward_source='none'."""
        from scripts.model2.persist_training_episodes import _reward_label

        reward, label, reward_source = _reward_label("LONG", 0.0, 110.0)

        assert reward is None
        assert reward_source == "none"


# ---------------------------------------------------------------------------
# R5 — Migração 0010 adiciona coluna reward_source
# ---------------------------------------------------------------------------

class TestMigration0010:
    """R5: migration 0010 ADD COLUMN reward_source com DEFAULT 'none'."""

    def test_migration_0010_file_exists(self) -> None:
        """R5: arquivo 0010_add_reward_source.sql deve existir."""
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "scripts" / "model2" / "migrations"
            / "0010_add_reward_source.sql"
        )
        assert migration_path.exists(), f"Migration nao encontrada: {migration_path}"

    def test_migration_0010_adds_reward_source_column(self) -> None:
        """R5: ao executar migration, coluna reward_source aparece na tabela."""
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "scripts" / "model2" / "migrations"
            / "0010_add_reward_source.sql"
        )
        sql = migration_path.read_text(encoding="utf-8")

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        # Schema inicial SEM reward_source
        conn.execute(
            """
            CREATE TABLE training_episodes (
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
            )
            """
        )
        conn.commit()
        # Executar migração
        conn.executescript(sql)
        conn.commit()

        # Verificar coluna existe
        cols = {row[1] for row in conn.execute("PRAGMA table_info(training_episodes)").fetchall()}
        assert "reward_source" in cols, f"Coluna reward_source ausente. Colunas: {cols}"
        conn.close()

    def test_migration_0010_existing_rows_get_default_none(self) -> None:
        """R5: episodios existentes recebem DEFAULT 'none' sem invalidade."""
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "scripts" / "model2" / "migrations"
            / "0010_add_reward_source.sql"
        )
        sql = migration_path.read_text(encoding="utf-8")

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE training_episodes (
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
            )
            """
        )
        # Inserir episodio pre-migracao
        conn.execute(
            """
            INSERT INTO training_episodes
                (episode_key, cycle_run_id, execution_id, symbol, timeframe,
                 status, event_timestamp, label, reward_proxy, features_json,
                 target_json, created_at)
            VALUES ('key1','run1',1,'BTCUSDT','H4','EXITED',1000,'win',0.05,'{}','{}',1000)
            """
        )
        conn.commit()
        # Migrar
        conn.executescript(sql)
        conn.commit()

        row = conn.execute(
            "SELECT reward_source FROM training_episodes WHERE episode_key='key1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "none", f"DEFAULT esperado 'none', obtido: {row[0]}"
        conn.close()


# ---------------------------------------------------------------------------
# R1 — INSERT com reward_source = "pnl_realized" para EXITED
# ---------------------------------------------------------------------------

class TestPersistEpisodeRewardSource:
    """R1/R2: persist_training_episodes grava reward_source correto no INSERT."""

    def test_insert_exited_episode_has_reward_source_pnl_realized(self, tmp_path: Path) -> None:
        """R1: execucao EXITED com exit_price => reward_source='pnl_realized'."""
        from scripts.model2.persist_training_episodes import run_persist_training_episodes

        source_db = str(tmp_path / "source.db")
        model2_db = str(tmp_path / "model2.db")
        output_dir = str(tmp_path / "output")

        _make_source_db(source_db)
        m2_conn = _make_model2_db(model2_db)
        sig_id = _insert_signal(m2_conn, symbol="BTCUSDT", entry_price=42000.0)
        _insert_execution(
            m2_conn, sig_id,
            symbol="BTCUSDT", status="EXITED",
            exit_price=43500.0, updated_at=1700001000000,
        )
        m2_conn.close()

        # Act
        run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        # Assert
        conn = sqlite3.connect(model2_db)
        row = conn.execute(
            "SELECT reward_proxy, reward_source FROM training_episodes "
            "WHERE execution_id > 0 AND symbol='BTCUSDT' LIMIT 1"
        ).fetchone()
        conn.close()

        assert row is not None, "Episodio de execucao nao foi inserido"
        reward_proxy, reward_source = row
        assert reward_proxy is not None, "reward_proxy deve ser != NULL para EXITED"
        assert reward_source == "pnl_realized", f"Esperado 'pnl_realized', obtido: {reward_source}"

    def test_insert_cycle_context_episode_has_reward_source_none(self, tmp_path: Path) -> None:
        """R2: episodio CYCLE_CONTEXT tem reward_proxy=NULL e reward_source='none'."""
        from scripts.model2.persist_training_episodes import run_persist_training_episodes

        source_db = str(tmp_path / "source.db")
        model2_db = str(tmp_path / "model2.db")
        output_dir = str(tmp_path / "output")

        _make_source_db(source_db)
        _make_model2_db(model2_db).close()

        # Act — sem execucoes, apenas CYCLE_CONTEXT sera gerado
        run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        # Assert
        conn = sqlite3.connect(model2_db)
        row = conn.execute(
            "SELECT execution_id, reward_proxy, reward_source FROM training_episodes "
            "WHERE status='CYCLE_CONTEXT' AND symbol='BTCUSDT' LIMIT 1"
        ).fetchone()
        conn.close()

        assert row is not None, "Episodio CYCLE_CONTEXT nao foi inserido"
        execution_id, reward_proxy, reward_source = row
        assert execution_id == 0, "CYCLE_CONTEXT deve ter execution_id=0"
        assert reward_proxy is None, "CYCLE_CONTEXT deve ter reward_proxy=NULL"
        assert reward_source == "none", f"Esperado 'none', obtido: {reward_source}"

    def test_insert_open_execution_has_reward_source_none(self, tmp_path: Path) -> None:
        """R1-edge: execucao OPEN (sem exit_price) deve ter reward_source='none'."""
        from scripts.model2.persist_training_episodes import run_persist_training_episodes

        source_db = str(tmp_path / "source.db")
        model2_db = str(tmp_path / "model2.db")
        output_dir = str(tmp_path / "output")

        _make_source_db(source_db)
        m2_conn = _make_model2_db(model2_db)
        sig_id = _insert_signal(m2_conn, symbol="BTCUSDT", entry_price=42000.0)
        _insert_execution(
            m2_conn, sig_id,
            symbol="BTCUSDT", status="OPEN",
            exit_price=None, updated_at=1700001000000,
        )
        m2_conn.close()

        # Act
        run_persist_training_episodes(
            source_db_path=source_db,
            model2_db_path=model2_db,
            symbols=["BTCUSDT"],
            timeframe="H4",
            output_dir=output_dir,
        )

        # Assert
        conn = sqlite3.connect(model2_db)
        row = conn.execute(
            "SELECT reward_proxy, reward_source FROM training_episodes "
            "WHERE execution_id > 0 AND symbol='BTCUSDT' LIMIT 1"
        ).fetchone()
        conn.close()

        assert row is not None
        reward_proxy, reward_source = row
        assert reward_proxy is None, "OPEN sem exit_price nao deve ter reward_proxy"
        assert reward_source == "none", f"Esperado 'none', obtido: {reward_source}"


# ---------------------------------------------------------------------------
# R1 — _ensure_training_episodes_table inclui coluna reward_source
# ---------------------------------------------------------------------------

class TestEnsureTrainingEpisodesTable:
    """R1/R5: _ensure_training_episodes_table deve criar coluna reward_source."""

    def test_ensure_table_creates_reward_source_column(self, tmp_path: Path) -> None:
        """_ensure_training_episodes_table deve criar coluna reward_source."""
        from scripts.model2.persist_training_episodes import _ensure_training_episodes_table

        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        _ensure_training_episodes_table(conn)
        conn.commit()

        cols = {row[1] for row in conn.execute("PRAGMA table_info(training_episodes)").fetchall()}
        conn.close()

        assert "reward_source" in cols, f"reward_source ausente. Colunas: {cols}"

    def test_ensure_table_reward_source_default_is_none_string(self, tmp_path: Path) -> None:
        """reward_source deve ter DEFAULT 'none' (literal string)."""
        from scripts.model2.persist_training_episodes import _ensure_training_episodes_table

        db_path = str(tmp_path / "test2.db")
        conn = sqlite3.connect(db_path)
        _ensure_training_episodes_table(conn)

        # Inserir linha sem especificar reward_source
        conn.execute(
            """
            INSERT INTO training_episodes
                (episode_key, cycle_run_id, execution_id, symbol, timeframe,
                 status, event_timestamp, label, reward_proxy, features_json,
                 target_json, created_at)
            VALUES ('k','r',1,'BTCUSDT','H4','EXITED',1,'win',0.1,'{}','{}',1)
            """
        )
        conn.commit()

        row = conn.execute("SELECT reward_source FROM training_episodes").fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "none", f"DEFAULT esperado 'none', obtido: {row[0]}"


# ---------------------------------------------------------------------------
# R4 — collect_training_info nao conta CYCLE_CONTEXT nem reward_proxy=NULL
# ---------------------------------------------------------------------------

class TestCollectTrainingInfo:
    """R4: collect_training_info filtra corretamente episodios prontos."""

    def _setup_training_db(self, db_path: str) -> None:
        conn = sqlite3.connect(db_path)
        conn.executescript(
            """
            CREATE TABLE training_episodes (
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

            CREATE TABLE rl_training_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episodes_used INTEGER NOT NULL,
                avg_reward REAL,
                completed_at TEXT NOT NULL,
                model_version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
        conn.close()

    def test_collect_training_info_excludes_cycle_context_episodes(self, tmp_path: Path) -> None:
        """R4: episodios CYCLE_CONTEXT nao contam como prontos para treino."""
        from core.model2.cycle_report import collect_training_info

        db_path = str(tmp_path / "train.db")
        self._setup_training_db(db_path)

        conn = sqlite3.connect(db_path)
        # 1 episodio valido
        conn.execute(
            "INSERT INTO training_episodes VALUES (NULL,'k1','r',1,'BTC','H4','EXITED',1,'win',0.05,'pnl_realized','{}','{}',1)"
        )
        # 1 CYCLE_CONTEXT (nao deve contar)
        conn.execute(
            "INSERT INTO training_episodes VALUES (NULL,'k2','r',0,'BTC','H4','CYCLE_CONTEXT',1,'context',NULL,'none','{}','{}',1)"
        )
        conn.commit()
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending == 1, f"Esperado 1 episodio pronto, obtido: {pending}"

    def test_collect_training_info_excludes_null_reward_proxy(self, tmp_path: Path) -> None:
        """R4: episodios com reward_proxy=NULL nao contam como prontos para treino."""
        from core.model2.cycle_report import collect_training_info

        db_path = str(tmp_path / "train2.db")
        self._setup_training_db(db_path)

        conn = sqlite3.connect(db_path)
        # 1 episodio valido
        conn.execute(
            "INSERT INTO training_episodes VALUES (NULL,'k1','r',1,'BTC','H4','EXITED',1,'win',0.05,'pnl_realized','{}','{}',1)"
        )
        # 1 com reward_proxy=NULL (nao deve contar)
        conn.execute(
            "INSERT INTO training_episodes VALUES (NULL,'k3','r',2,'BTC','H4','OPEN',1,'pending',NULL,'none','{}','{}',1)"
        )
        conn.commit()
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending == 1, f"Esperado 1 episodio pronto, obtido: {pending}"

    def test_collect_training_info_counts_only_ready_episodes(self, tmp_path: Path) -> None:
        """R4: apenas episodios com reward_proxy != NULL e status != CYCLE_CONTEXT contam."""
        from core.model2.cycle_report import collect_training_info

        db_path = str(tmp_path / "train3.db")
        self._setup_training_db(db_path)

        conn = sqlite3.connect(db_path)
        rows = [
            "INSERT INTO training_episodes VALUES (NULL,'k1','r',1,'BTC','H4','EXITED',1,'win',0.05,'pnl_realized','{}','{}',1)",
            "INSERT INTO training_episodes VALUES (NULL,'k2','r',2,'BTC','H4','EXITED',1,'loss',-0.02,'pnl_realized','{}','{}',1)",
            "INSERT INTO training_episodes VALUES (NULL,'k3','r',0,'BTC','H4','CYCLE_CONTEXT',1,'context',NULL,'none','{}','{}',1)",
            "INSERT INTO training_episodes VALUES (NULL,'k4','r',3,'BTC','H4','OPEN',1,'pending',NULL,'none','{}','{}',1)",
        ]
        for row in rows:
            conn.execute(row)
        conn.commit()
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending == 2, f"Esperado 2 episodios prontos, obtido: {pending}"
