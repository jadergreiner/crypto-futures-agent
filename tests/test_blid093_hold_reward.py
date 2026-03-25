"""Testes RED — BLID-093: hold reward counterfactual em training_episodes.

Cobre todas as classes de requisitos do handoff SA:
- _reward_counterfactual: calculo counterfactual de reward para episodios BLOCKED
- _ms_per_candle: milissegundos por candle por timeframe
- _lookup_at_ms: timestamp de lookup counterfactual
- Migration 0011: ADD COLUMN reward_lookup_at_ms
- persist_blocked_episode: insercao de episodio BLOCKED com episode_key hold:*
- flush_deferred_rewards: preenchimento diferido de reward counterfactual
- collect_training_info: conta episodios counterfactual como treinaveis

Todos os testes devem FALHAR (RED) antes da implementacao.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Helpers de fixture compartilhadas
# ---------------------------------------------------------------------------

_SCHEMA_BASE = """
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

_SCHEMA_TRAINING_EPISODES = """
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
    reward_lookup_at_ms INTEGER,
    features_json TEXT NOT NULL,
    target_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
"""

_SCHEMA_OHLCV_H4 = """
CREATE TABLE IF NOT EXISTS ohlcv_h4 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL
);
"""

_SCHEMA_OHLCV_H1 = """
CREATE TABLE IF NOT EXISTS ohlcv_h1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL
);
"""

_SCHEMA_OHLCV_D1 = """
CREATE TABLE IF NOT EXISTS ohlcv_d1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL
);
"""


def _make_model2_db(path: str) -> sqlite3.Connection:
    """Cria schema completo do modelo2.db com coluna reward_lookup_at_ms."""
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA_BASE + _SCHEMA_TRAINING_EPISODES)
    conn.commit()
    return conn


def _make_source_db(path: str, symbol: str = "BTCUSDT") -> None:
    """Cria DB OHLCV com candles H4, H1, D1."""
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA_OHLCV_H4 + _SCHEMA_OHLCV_H1 + _SCHEMA_OHLCV_D1)
    # Candle base: T=1_700_000_000_000, close=42000
    conn.execute(
        "INSERT INTO ohlcv_h4 (symbol, timestamp, open, high, low, close, volume) "
        "VALUES (?, 1700000000000, 42000.0, 43000.0, 41000.0, 42000.0, 1000.0)",
        (symbol,),
    )
    # Candle t+N (H4, N=4): T + 4*14400000 = 1700057600000, close=44000
    conn.execute(
        "INSERT INTO ohlcv_h4 (symbol, timestamp, open, high, low, close, volume) "
        "VALUES (?, 1700057600000, 44000.0, 45000.0, 43000.0, 44000.0, 500.0)",
        (symbol,),
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
            kwargs.get("status", "BLOCKED"),
            kwargs.get("updated_at", 1700001000000),
            kwargs.get("entry_filled_at", None),
            kwargs.get("exited_at", None),
            kwargs.get("exit_price", None),
            kwargs.get("payload_json", "{}"),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def _insert_episode(conn: sqlite3.Connection, **kwargs: Any) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO training_episodes
            (episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
             event_timestamp, label, reward_proxy, reward_source, reward_lookup_at_ms,
             features_json, target_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            kwargs["episode_key"],
            kwargs.get("cycle_run_id", "run1"),
            kwargs.get("execution_id", 1),
            kwargs.get("symbol", "BTCUSDT"),
            kwargs.get("timeframe", "H4"),
            kwargs.get("status", "BLOCKED"),
            kwargs.get("event_timestamp", 1700000000000),
            kwargs.get("label", "pending"),
            kwargs.get("reward_proxy", None),
            kwargs.get("reward_source", "none"),
            kwargs.get("reward_lookup_at_ms", None),
            kwargs.get("features_json", "{}"),
            kwargs.get("target_json", "{}"),
            kwargs.get("created_at", 1700000000000),
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Classe TestRewardCounterfactual
# ---------------------------------------------------------------------------

class TestRewardCounterfactual:
    """Testa _reward_counterfactual(side, close_t, close_tN) -> (reward, label, source)."""

    def test_long_mercado_subiu_hold_opportunity_missed(self) -> None:
        """LONG bloqueado, mercado subiu: perdeu oportunidade => reward<0, hold_opportunity_missed.

        A logica e: bloqueou LONG mas o mercado subiu, entao o hold foi oportunidade perdida.
        reward = (close_tN - close_t) / close_t * direcao onde direcao=-1 (blocked LONG = hold).
        """
        # Arrange
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        side = "LONG"
        close_t = 42000.0
        close_tN = 44000.0  # mercado subiu

        # Act
        reward, label, reward_source = _reward_counterfactual(side, close_t, close_tN)

        # Assert — LONG bloqueado e mercado subiu = oportunidade perdida
        assert reward is not None
        assert reward < 0, f"Esperado reward<0 (oportunidade perdida), obtido: {reward}"
        assert label == "hold_opportunity_missed"
        assert reward_source == "counterfactual"

    def test_long_mercado_caiu_hold_correto(self) -> None:
        """LONG bloqueado, mercado caiu: hold foi correto => reward>0, hold_correct.

        Bloqueou LONG, mercado caiu: a decisao de bloquear foi certa.
        """
        # Arrange
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        side = "LONG"
        close_t = 42000.0
        close_tN = 40000.0  # mercado caiu

        # Act
        reward, label, reward_source = _reward_counterfactual(side, close_t, close_tN)

        # Assert
        assert reward is not None
        assert reward > 0, f"Esperado reward>0 (hold correto), obtido: {reward}"
        assert label == "hold_correct"
        assert reward_source == "counterfactual"

    def test_short_mercado_caiu_hold_opportunity_missed(self) -> None:
        """SHORT bloqueado, mercado caiu: perdeu oportunidade => reward<0, hold_opportunity_missed."""
        # Arrange
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        side = "SHORT"
        close_t = 42000.0
        close_tN = 40000.0  # mercado caiu

        # Act
        reward, label, reward_source = _reward_counterfactual(side, close_t, close_tN)

        # Assert
        assert reward is not None
        assert reward < 0, f"Esperado reward<0 (oportunidade perdida), obtido: {reward}"
        assert label == "hold_opportunity_missed"
        assert reward_source == "counterfactual"

    def test_short_mercado_subiu_hold_correto(self) -> None:
        """SHORT bloqueado, mercado subiu: hold foi correto => reward>0, hold_correct."""
        # Arrange
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        side = "SHORT"
        close_t = 42000.0
        close_tN = 44000.0  # mercado subiu

        # Act
        reward, label, reward_source = _reward_counterfactual(side, close_t, close_tN)

        # Assert
        assert reward is not None
        assert reward > 0, f"Esperado reward>0 (hold correto), obtido: {reward}"
        assert label == "hold_correct"
        assert reward_source == "counterfactual"

    def test_close_tN_none_retorna_pending(self) -> None:
        """close_tN=None (candle futuro indisponivel) => (None, 'pending', 'none')."""
        # Arrange
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        # Act
        reward, label, reward_source = _reward_counterfactual("LONG", 42000.0, None)

        # Assert
        assert reward is None
        assert label == "pending"
        assert reward_source == "none"

    def test_close_t_zero_retorna_pending(self) -> None:
        """close_t=0 (divisao por zero) => (None, 'pending', 'none') — fail-safe."""
        # Arrange
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        # Act
        reward, label, reward_source = _reward_counterfactual("LONG", 0.0, 44000.0)

        # Assert
        assert reward is None
        assert label == "pending"
        assert reward_source == "none"


# ---------------------------------------------------------------------------
# Classe TestMsPerCandle
# ---------------------------------------------------------------------------

class TestMsPerCandle:
    """Testa _ms_per_candle(timeframe) -> int."""

    def test_h4_retorna_14400000(self) -> None:
        """H4 = 4h * 3600s * 1000ms = 14_400_000 ms."""
        from scripts.model2.persist_training_episodes import _ms_per_candle

        assert _ms_per_candle("H4") == 14_400_000

    def test_h1_retorna_3600000(self) -> None:
        """H1 = 1h * 3600s * 1000ms = 3_600_000 ms."""
        from scripts.model2.persist_training_episodes import _ms_per_candle

        assert _ms_per_candle("H1") == 3_600_000

    def test_d1_retorna_86400000(self) -> None:
        """D1 = 24h * 3600s * 1000ms = 86_400_000 ms."""
        from scripts.model2.persist_training_episodes import _ms_per_candle

        assert _ms_per_candle("D1") == 86_400_000


# ---------------------------------------------------------------------------
# Classe TestLookupAtMs
# ---------------------------------------------------------------------------

class TestLookupAtMs:
    """Testa _lookup_at_ms(event_timestamp_ms, timeframe) -> int."""

    def test_h4_n4_correto(self) -> None:
        """H4, N=4: lookup = event_ts + 4 * 14_400_000."""
        from scripts.model2.persist_training_episodes import _lookup_at_ms

        event_ts = 1_700_000_000_000
        expected = event_ts + 4 * 14_400_000

        result = _lookup_at_ms(event_ts, "H4")

        assert result == expected, f"Esperado {expected}, obtido {result}"

    def test_h1_n24_correto(self) -> None:
        """H1, N=24: lookup = event_ts + 24 * 3_600_000."""
        from scripts.model2.persist_training_episodes import _lookup_at_ms

        event_ts = 1_700_000_000_000
        expected = event_ts + 24 * 3_600_000

        result = _lookup_at_ms(event_ts, "H1")

        assert result == expected, f"Esperado {expected}, obtido {result}"


# ---------------------------------------------------------------------------
# Classe TestMigration0011
# ---------------------------------------------------------------------------

class TestMigration0011:
    """Testa migration 0011_add_reward_lookup_at_ms.sql."""

    _MIGRATION_PATH = (
        Path(__file__).resolve().parents[1]
        / "scripts" / "model2" / "migrations"
        / "0011_add_reward_lookup_at_ms.sql"
    )

    def test_arquivo_existe(self) -> None:
        """Arquivo 0011_add_reward_lookup_at_ms.sql deve existir no repositorio."""
        assert self._MIGRATION_PATH.exists(), (
            f"Migration nao encontrada: {self._MIGRATION_PATH}"
        )

    def test_coluna_criada_em_db_novo(self) -> None:
        """Aplicar migration em DB sem a coluna cria reward_lookup_at_ms."""
        sql = self._MIGRATION_PATH.read_text(encoding="utf-8")

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        conn = sqlite3.connect(db_path)
        # Schema sem reward_lookup_at_ms
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
                reward_source TEXT NOT NULL DEFAULT 'none',
                features_json TEXT NOT NULL,
                target_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
        conn.executescript(sql)
        conn.commit()

        cols = {row[1] for row in conn.execute("PRAGMA table_info(training_episodes)").fetchall()}
        conn.close()

        assert "reward_lookup_at_ms" in cols, (
            f"Coluna reward_lookup_at_ms ausente apos migration. Colunas: {cols}"
        )

    def test_idempotente(self) -> None:
        """Executar migration 2x nao lanca excecao (idempotente via IF NOT EXISTS)."""
        sql = self._MIGRATION_PATH.read_text(encoding="utf-8")

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
                reward_source TEXT NOT NULL DEFAULT 'none',
                features_json TEXT NOT NULL,
                target_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
        # Executa 2x — nao deve lancar erro
        try:
            conn.executescript(sql)
            conn.commit()
            conn.executescript(sql)
            conn.commit()
        except Exception as exc:
            pytest.fail(f"Migration nao e idempotente — lancou: {exc}")
        finally:
            conn.close()

    def test_coluna_aceita_null(self) -> None:
        """INSERT sem reward_lookup_at_ms deve aceitar NULL (coluna nullable)."""
        sql = self._MIGRATION_PATH.read_text(encoding="utf-8")

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
                reward_source TEXT NOT NULL DEFAULT 'none',
                features_json TEXT NOT NULL,
                target_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
        conn.executescript(sql)
        conn.commit()

        conn.execute(
            """
            INSERT INTO training_episodes
                (episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
                 event_timestamp, label, reward_proxy, reward_source,
                 features_json, target_json, created_at)
            VALUES ('k1','r1',1,'BTCUSDT','H4','BLOCKED',1700000000000,'pending',
                    NULL,'none','{}','{}',1700000000000)
            """
        )
        conn.commit()

        row = conn.execute(
            "SELECT reward_lookup_at_ms FROM training_episodes WHERE episode_key='k1'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] is None, f"Esperado NULL, obtido: {row[0]}"


# ---------------------------------------------------------------------------
# Classe TestPersistBlockedEpisode
# ---------------------------------------------------------------------------

class TestPersistBlockedEpisode:
    """Testa insercao de episodios BLOCKED com episode_key hold:* e reward_lookup_at_ms."""

    def test_blocked_episode_inserido_com_lookup_at_ms(self, tmp_path: Path) -> None:
        """Execucao BLOCKED deve gerar episodio com episode_key 'hold:*' e reward_lookup_at_ms NOT NULL."""
        from scripts.model2.persist_training_episodes import run_persist_training_episodes

        source_db = str(tmp_path / "source.db")
        model2_db = str(tmp_path / "model2.db")
        output_dir = str(tmp_path / "output")

        _make_source_db(source_db)
        m2_conn = _make_model2_db(model2_db)
        sig_id = _insert_signal(m2_conn, symbol="BTCUSDT", timeframe="H4", signal_side="LONG")
        _insert_execution(
            m2_conn, sig_id,
            symbol="BTCUSDT", timeframe="H4",
            signal_side="LONG", status="BLOCKED",
            updated_at=1700000000000,
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
            "SELECT episode_key, reward_lookup_at_ms, label, reward_source "
            "FROM training_episodes "
            "WHERE status='BLOCKED' AND symbol='BTCUSDT' LIMIT 1"
        ).fetchone()
        conn.close()

        assert row is not None, "Episodio BLOCKED nao foi inserido"
        episode_key, reward_lookup_at_ms, label, reward_source = row
        assert episode_key.startswith("hold:"), (
            f"episode_key deve comecar com 'hold:', obtido: {episode_key}"
        )
        assert reward_lookup_at_ms is not None, "reward_lookup_at_ms deve ser NOT NULL para BLOCKED"

    def test_blocked_episode_label_pending_antes_do_flush(self, tmp_path: Path) -> None:
        """Episodio BLOCKED inserido antes do flush deve ter reward_proxy=NULL e label='pending'."""
        from scripts.model2.persist_training_episodes import run_persist_training_episodes

        source_db = str(tmp_path / "source.db")
        model2_db = str(tmp_path / "model2.db")
        output_dir = str(tmp_path / "output")

        _make_source_db(source_db)
        m2_conn = _make_model2_db(model2_db)
        sig_id = _insert_signal(m2_conn, symbol="BTCUSDT", timeframe="H4", signal_side="LONG")
        _insert_execution(
            m2_conn, sig_id,
            symbol="BTCUSDT", timeframe="H4",
            signal_side="LONG", status="BLOCKED",
            updated_at=1700000000000,
        )
        m2_conn.close()

        # Act — sem flush, so insercao inicial
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
            "SELECT reward_proxy, label FROM training_episodes "
            "WHERE status='BLOCKED' AND symbol='BTCUSDT' LIMIT 1"
        ).fetchone()
        conn.close()

        assert row is not None
        reward_proxy, label = row
        assert reward_proxy is None, "Antes do flush reward_proxy deve ser NULL"
        assert label == "pending", f"Antes do flush label deve ser 'pending', obtido: {label}"

    def test_episode_key_unico_idempotente(self, tmp_path: Path) -> None:
        """Inserir mesmo episodio BLOCKED 2x via INSERT OR IGNORE nao duplica."""
        from scripts.model2.persist_training_episodes import run_persist_training_episodes

        source_db = str(tmp_path / "source.db")
        model2_db = str(tmp_path / "model2.db")
        output_dir = str(tmp_path / "output")

        _make_source_db(source_db)
        m2_conn = _make_model2_db(model2_db)
        sig_id = _insert_signal(m2_conn, symbol="BTCUSDT", timeframe="H4", signal_side="LONG")
        _insert_execution(
            m2_conn, sig_id,
            symbol="BTCUSDT", timeframe="H4",
            signal_side="LONG", status="BLOCKED",
            updated_at=1700000000000,
        )
        m2_conn.close()

        # Act — executa 2x
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

        # Assert — exatamente 1 episodio BLOCKED
        conn = sqlite3.connect(model2_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM training_episodes WHERE status='BLOCKED' AND symbol='BTCUSDT'"
        ).fetchone()[0]
        conn.close()

        assert count == 1, f"Esperado 1 episodio BLOCKED (idempotente), obtido: {count}"


# ---------------------------------------------------------------------------
# Classe TestFlushDeferredRewards
# ---------------------------------------------------------------------------

class TestFlushDeferredRewards:
    """Testa flush_deferred_rewards(model2_db_path, source_db_path, now_ms) -> dict."""

    def _setup_dbs(self, tmp_path: Path, close_tN: float | None = 44000.0) -> tuple[str, str]:
        """Cria DBs de source e model2 com episodio BLOCKED pendente."""
        source_db = str(tmp_path / "source.db")
        model2_db = str(tmp_path / "model2.db")

        # Source DB com candle em T e T+N
        conn_src = sqlite3.connect(source_db)
        conn_src.executescript(_SCHEMA_OHLCV_H4)
        conn_src.execute(
            "INSERT INTO ohlcv_h4 (symbol, timestamp, open, high, low, close, volume) "
            "VALUES ('BTCUSDT', 1700000000000, 42000.0, 43000.0, 41000.0, 42000.0, 1000.0)"
        )
        if close_tN is not None:
            # Candle T+N = T + 4 * 14_400_000 = 1_700_057_600_000
            conn_src.execute(
                "INSERT INTO ohlcv_h4 (symbol, timestamp, open, high, low, close, volume) "
                "VALUES ('BTCUSDT', 1700057600000, ?, ?, ?, ?, 500.0)",
                (close_tN, close_tN + 500, close_tN - 500, close_tN),
            )
        conn_src.commit()
        conn_src.close()

        # Model2 DB com episodio BLOCKED pendente
        conn_m2 = _make_model2_db(model2_db)
        _insert_episode(
            conn_m2,
            episode_key="hold:1:1700000000000",
            execution_id=1,
            symbol="BTCUSDT",
            timeframe="H4",
            status="BLOCKED",
            event_timestamp=1_700_000_000_000,
            label="pending",
            reward_proxy=None,
            reward_source="none",
            reward_lookup_at_ms=1_700_057_600_000,  # T + 4*H4
            created_at=1_700_000_000_000,
        )
        conn_m2.close()

        return source_db, model2_db

    def test_flush_preenche_reward_quando_candle_disponivel(self, tmp_path: Path) -> None:
        """flush_deferred_rewards preenche reward_proxy quando candle T+N disponivel."""
        from scripts.model2.persist_training_episodes import flush_deferred_rewards

        source_db, model2_db = self._setup_dbs(tmp_path, close_tN=44000.0)
        now_ms = 1_700_057_600_001  # apos o lookup

        # Act
        result = flush_deferred_rewards(
            model2_db_path=model2_db,
            source_db_path=source_db,
            now_ms=now_ms,
        )

        # Assert
        conn = sqlite3.connect(model2_db)
        row = conn.execute(
            "SELECT reward_proxy FROM training_episodes WHERE episode_key='hold:1:1700000000000'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] is not None, "reward_proxy deve ser preenchido apos flush"

    def test_flush_mantem_null_quando_candle_indisponivel(self, tmp_path: Path) -> None:
        """flush_deferred_rewards mantem reward_proxy=NULL quando candle T+N ausente."""
        from scripts.model2.persist_training_episodes import flush_deferred_rewards

        source_db, model2_db = self._setup_dbs(tmp_path, close_tN=None)
        now_ms = 1_700_057_600_001

        # Act
        flush_deferred_rewards(
            model2_db_path=model2_db,
            source_db_path=source_db,
            now_ms=now_ms,
        )

        # Assert
        conn = sqlite3.connect(model2_db)
        row = conn.execute(
            "SELECT reward_proxy FROM training_episodes WHERE episode_key='hold:1:1700000000000'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] is None, "Sem candle T+N reward_proxy deve permanecer NULL"

    def test_flush_atualiza_label_hold_correct_ou_missed(self, tmp_path: Path) -> None:
        """Apos flush com candle disponivel, label deve ser hold_correct ou hold_opportunity_missed."""
        from scripts.model2.persist_training_episodes import flush_deferred_rewards

        # close_tN > close_t => LONG blocked + mercado subiu => hold_opportunity_missed
        source_db, model2_db = self._setup_dbs(tmp_path, close_tN=44000.0)
        now_ms = 1_700_057_600_001

        # Precisamos que o episodio tenha signal_side registrado nas features
        # Para este teste inserimos o side no features_json
        conn_m2 = sqlite3.connect(model2_db)
        conn_m2.execute(
            "UPDATE training_episodes SET features_json=? WHERE episode_key=?",
            ('{"signal_side": "LONG", "close_t": 42000.0}', "hold:1:1700000000000"),
        )
        conn_m2.commit()
        conn_m2.close()

        flush_deferred_rewards(
            model2_db_path=model2_db,
            source_db_path=source_db,
            now_ms=now_ms,
        )

        conn = sqlite3.connect(model2_db)
        row = conn.execute(
            "SELECT label FROM training_episodes WHERE episode_key='hold:1:1700000000000'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] in ("hold_correct", "hold_opportunity_missed"), (
            f"label deve ser hold_correct ou hold_opportunity_missed, obtido: {row[0]}"
        )

    def test_flush_atualiza_reward_source_para_counterfactual(self, tmp_path: Path) -> None:
        """Apos flush bem-sucedido, reward_source deve ser 'counterfactual'."""
        from scripts.model2.persist_training_episodes import flush_deferred_rewards

        source_db, model2_db = self._setup_dbs(tmp_path, close_tN=44000.0)
        now_ms = 1_700_057_600_001

        conn_m2 = sqlite3.connect(model2_db)
        conn_m2.execute(
            "UPDATE training_episodes SET features_json=? WHERE episode_key=?",
            ('{"signal_side": "LONG", "close_t": 42000.0}', "hold:1:1700000000000"),
        )
        conn_m2.commit()
        conn_m2.close()

        flush_deferred_rewards(
            model2_db_path=model2_db,
            source_db_path=source_db,
            now_ms=now_ms,
        )

        conn = sqlite3.connect(model2_db)
        row = conn.execute(
            "SELECT reward_source FROM training_episodes WHERE episode_key='hold:1:1700000000000'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "counterfactual", (
            f"reward_source deve ser 'counterfactual', obtido: {row[0]}"
        )

    def test_flush_nao_reprocessa_episodios_ja_com_reward(self, tmp_path: Path) -> None:
        """Episodio com reward_proxy ja preenchido nao e retocado pelo flush."""
        from scripts.model2.persist_training_episodes import flush_deferred_rewards

        source_db, model2_db = self._setup_dbs(tmp_path, close_tN=44000.0)
        now_ms = 1_700_057_600_001

        # Pre-preencher reward
        conn_m2 = sqlite3.connect(model2_db)
        conn_m2.execute(
            "UPDATE training_episodes SET reward_proxy=0.999, reward_source='counterfactual', "
            "label='hold_correct' WHERE episode_key='hold:1:1700000000000'"
        )
        conn_m2.commit()
        conn_m2.close()

        # Act
        flush_deferred_rewards(
            model2_db_path=model2_db,
            source_db_path=source_db,
            now_ms=now_ms,
        )

        # Assert — reward_proxy nao alterado
        conn = sqlite3.connect(model2_db)
        row = conn.execute(
            "SELECT reward_proxy FROM training_episodes WHERE episode_key='hold:1:1700000000000'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert abs(row[0] - 0.999) < 1e-9, (
            f"reward_proxy nao deve ser alterado se ja preenchido, obtido: {row[0]}"
        )


# ---------------------------------------------------------------------------
# Classe TestCollectTrainingInfoComHold
# ---------------------------------------------------------------------------

class TestCollectTrainingInfoComHold:
    """Testa collect_training_info contando corretamente episodios counterfactual."""

    def _setup_db(self, db_path: str) -> None:
        conn = sqlite3.connect(db_path)
        conn.executescript(
            _SCHEMA_TRAINING_EPISODES + """
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
        conn.close()

    def test_conta_episodios_counterfactual_como_treinavel(self, tmp_path: Path) -> None:
        """Episodio BLOCKED com reward_source='counterfactual' e reward_proxy NOT NULL e contado."""
        from core.model2.cycle_report import collect_training_info

        db_path = str(tmp_path / "train.db")
        self._setup_db(db_path)

        conn = sqlite3.connect(db_path)
        # Episodio counterfactual pronto
        conn.execute(
            """
            INSERT INTO training_episodes
                (episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
                 event_timestamp, label, reward_proxy, reward_source, reward_lookup_at_ms,
                 features_json, target_json, created_at)
            VALUES ('hold:1:1000','r1',1,'BTCUSDT','H4','BLOCKED',1000,
                    'hold_correct',0.05,'counterfactual',2000,'{}','{}',1000)
            """
        )
        conn.commit()
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending >= 1, (
            f"Episodio counterfactual com reward_proxy deve ser contado, pending={pending}"
        )

    def test_nao_conta_hold_pendente_sem_reward(self, tmp_path: Path) -> None:
        """Episodio BLOCKED com reward_proxy=NULL nao e contado como treinavel."""
        from core.model2.cycle_report import collect_training_info

        db_path = str(tmp_path / "train2.db")
        self._setup_db(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO training_episodes
                (episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
                 event_timestamp, label, reward_proxy, reward_source, reward_lookup_at_ms,
                 features_json, target_json, created_at)
            VALUES ('hold:2:1000','r1',2,'BTCUSDT','H4','BLOCKED',1000,
                    'pending',NULL,'none',2000,'{}','{}',1000)
            """
        )
        conn.commit()
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending == 0, (
            f"Episodio BLOCKED sem reward_proxy nao deve ser contado, pending={pending}"
        )

    def test_nao_conta_cycle_context(self, tmp_path: Path) -> None:
        """CYCLE_CONTEXT nao e contado — teste de regressao."""
        from core.model2.cycle_report import collect_training_info

        db_path = str(tmp_path / "train3.db")
        self._setup_db(db_path)

        conn = sqlite3.connect(db_path)
        # 1 counterfactual valido
        conn.execute(
            """
            INSERT INTO training_episodes
                (episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
                 event_timestamp, label, reward_proxy, reward_source, reward_lookup_at_ms,
                 features_json, target_json, created_at)
            VALUES ('hold:3:1000','r1',3,'BTCUSDT','H4','BLOCKED',1000,
                    'hold_correct',0.03,'counterfactual',2000,'{}','{}',1000)
            """
        )
        # 1 CYCLE_CONTEXT — nao deve contar
        conn.execute(
            """
            INSERT INTO training_episodes
                (episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
                 event_timestamp, label, reward_proxy, reward_source, reward_lookup_at_ms,
                 features_json, target_json, created_at)
            VALUES ('context:r1:BTCUSDT','r1',0,'BTCUSDT','H4','CYCLE_CONTEXT',1000,
                    'context',NULL,'none',NULL,'{}','{}',1000)
            """
        )
        conn.commit()
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending == 1, (
            f"Apenas o episodio counterfactual deve ser contado (nao CYCLE_CONTEXT), pending={pending}"
        )
