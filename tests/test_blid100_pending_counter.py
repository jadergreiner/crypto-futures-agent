"""Testes RED — BLID-100: corrigir contador de episodios pendentes apos retreino.

Cobre:
- collect_training_info retorna pending=0 apos rl_training_log registrar retreino
- train_ppo_incremental.record_training_log grava completed_at_ms em milissegundos
- Novos episodios apos retreino incrementam o contador corretamente
- Fallback para conversao inline quando completed_at_ms ausente

Todos os testes devem FALHAR (RED) antes da implementacao.
"""
from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Schemas de fixture
# ---------------------------------------------------------------------------

_SCHEMA_RL_TRAINING_LOG = """
CREATE TABLE IF NOT EXISTS rl_training_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episodes_used INTEGER NOT NULL,
    avg_reward REAL,
    completed_at TEXT NOT NULL,
    completed_at_ms INTEGER,
    status TEXT,
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
    features_json TEXT NOT NULL DEFAULT '{}',
    target_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL
);
"""


def _make_db(extra_sql: str = "") -> tuple[str, sqlite3.Connection]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.executescript(_SCHEMA_RL_TRAINING_LOG + _SCHEMA_TRAINING_EPISODES + extra_sql)
    conn.commit()
    return tmp.name, conn


def _insert_episode(conn: sqlite3.Connection, created_at_ms: int, key: str = "ep:1") -> None:
    conn.execute(
        """INSERT INTO training_episodes (
            episode_key, cycle_run_id, execution_id, symbol, timeframe,
            status, event_timestamp, label, reward_proxy, reward_source,
            features_json, target_json, created_at
        ) VALUES (?, 'run', 1, 'BTCUSDT', 'H4', 'FILLED', ?, 'win', 0.05,
                  'pnl_realized', '{}', '{}', ?)""",
        (key, created_at_ms, created_at_ms),
    )
    conn.commit()


def _insert_training_log(
    conn: sqlite3.Connection,
    completed_at: str,
    completed_at_ms: int | None = None,
) -> None:
    if completed_at_ms is not None:
        try:
            conn.execute("ALTER TABLE rl_training_log ADD COLUMN completed_at_ms INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        conn.execute(
            "INSERT INTO rl_training_log (completed_at, completed_at_ms, episodes_used, status) "
            "VALUES (?, ?, ?, 'ok')",
            (completed_at, completed_at_ms, 1),
        )
    else:
        conn.execute(
            "INSERT INTO rl_training_log (completed_at, episodes_used, status) VALUES (?, ?, 'ok')",
            (completed_at, 1),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Classe 1 — collect_training_info retorna 0 apos retreino
# ---------------------------------------------------------------------------

class TestPendingCounterResetsAfterRetrain:
    """pending deve ser 0 logo apos rl_training_log registrar retreino."""

    def test_pending_zero_after_retrain_with_completed_at_ms(self) -> None:
        """Com completed_at_ms gravado, pending deve ser 0 apos retreino."""
        from core.model2.cycle_report import collect_training_info

        db_path, conn = _make_db()
        now_ms = int(time.time() * 1000)

        # Episodio criado ANTES do retreino
        _insert_episode(conn, created_at_ms=now_ms - 10_000, key="ep:1")

        # Retreino registrado DEPOIS do episodio
        _insert_training_log(conn, "2026-03-26 12:00:00", completed_at_ms=now_ms)
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending == 0, (
            f"Esperado pending=0 apos retreino, obtido {pending}"
        )

    def test_pending_increments_after_retrain_for_new_episodes(self) -> None:
        """Episodios criados APOS retreino devem incrementar o contador."""
        from core.model2.cycle_report import collect_training_info

        db_path, conn = _make_db()
        now_ms = int(time.time() * 1000)
        train_ms = now_ms - 5_000  # retreino ha 5s

        # Retreino
        _insert_training_log(conn, "2026-03-26 12:00:00", completed_at_ms=train_ms)

        # Episodio criado APOS retreino
        _insert_episode(conn, created_at_ms=now_ms, key="ep:after")
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending == 1, (
            f"Episodio apos retreino deve contar como pendente, obtido {pending}"
        )

    def test_pending_zero_with_inline_fallback_no_completed_at_ms(self) -> None:
        """Sem coluna completed_at_ms, fallback via strftime deve funcionar."""
        from core.model2.cycle_report import collect_training_info

        db_path, conn = _make_db()
        now_ms = int(time.time() * 1000)

        # Episodio criado com created_at em ms (ex: 2026-03-26 00:00:00 UTC)
        # Usar timestamp ANTES de 2026-03-26 12:00:00
        episode_ts = 1743033600000  # 2026-03-26 08:00:00 UTC em ms (approx)
        _insert_episode(conn, created_at_ms=episode_ts, key="ep:old")

        # Retreino SEM completed_at_ms — apenas string ISO
        conn.execute(
            "INSERT INTO rl_training_log (completed_at, episodes_used) "
            "VALUES ('2026-03-26 12:00:00', 1)"
        )
        conn.commit()
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending == 0, (
            f"Fallback inline deve retornar pending=0 apos retreino, obtido {pending}"
        )

    def test_pending_includes_hold_decision_episodes(self) -> None:
        """Episodios HOLD_DECISION apos retreino devem ser contados como pendentes."""
        from core.model2.cycle_report import collect_training_info

        db_path, conn = _make_db()
        now_ms = int(time.time() * 1000)
        train_ms = now_ms - 5_000

        _insert_training_log(conn, "2026-03-26 12:00:00", completed_at_ms=train_ms)

        # Episodio HOLD_DECISION criado apos retreino
        conn.execute(
            """INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, reward_source,
                features_json, target_json, created_at
            ) VALUES (?, 'run', 0, 'BTCUSDT', 'H4', 'HOLD_DECISION', ?, 'hold_correct',
                      0.02, 'counterfactual', '{}', '{}', ?)""",
            ("hold_decision:1:1000", now_ms, now_ms),
        )
        conn.commit()
        conn.close()

        _, pending = collect_training_info(db_path)

        assert pending >= 1, (
            f"Episodio HOLD_DECISION apos retreino deve ser contado, obtido {pending}"
        )


# ---------------------------------------------------------------------------
# Classe 2 — record_training_log grava completed_at_ms
# ---------------------------------------------------------------------------

class TestRecordTrainingLogStoresMs:
    """record_training_log deve gravar completed_at_ms em milissegundos."""

    def test_record_training_log_adds_completed_at_ms_column(self) -> None:
        """Apos record_training_log, rl_training_log deve ter completed_at_ms."""
        from scripts.model2.train_ppo_incremental import PPOTrainer

        db_path, conn = _make_db()
        conn.executescript(_SCHEMA_TRAINING_EPISODES)
        conn.commit()
        conn.close()

        trainer = PPOTrainer(model2_db_path=Path(db_path), timeframe="H4")
        result = trainer.record_training_log(episodes_used=5, status="ok")

        assert result.get("status") == "ok"

        with sqlite3.connect(db_path) as c:
            # Verificar que coluna existe
            cols = [r[1] for r in c.execute("PRAGMA table_info(rl_training_log)").fetchall()]
            assert "completed_at_ms" in cols, (
                f"Coluna completed_at_ms deve existir em rl_training_log, colunas: {cols}"
            )

            # Verificar que valor e inteiro positivo
            row = c.execute(
                "SELECT completed_at_ms FROM rl_training_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert row is not None and row[0] is not None
            assert row[0] > 1_700_000_000_000, (
                f"completed_at_ms deve ser timestamp em ms, obtido {row[0]}"
            )

    def test_record_training_log_completed_at_ms_after_episode_created_at(self) -> None:
        """completed_at_ms deve ser >= created_at do episodio recente."""
        from scripts.model2.train_ppo_incremental import PPOTrainer

        db_path, conn = _make_db()

        # Criar episodio
        ep_ts = int(time.time() * 1000) - 1000
        _insert_episode(conn, created_at_ms=ep_ts, key="ep:before")
        conn.close()

        trainer = PPOTrainer(model2_db_path=Path(db_path), timeframe="H4")
        trainer.record_training_log(episodes_used=1, status="ok")

        with sqlite3.connect(db_path) as c:
            row = c.execute(
                "SELECT completed_at_ms FROM rl_training_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert row is not None and row[0] is not None
            assert row[0] >= ep_ts, (
                f"completed_at_ms={row[0]} deve ser >= ep_ts={ep_ts}"
            )
