"""Testes RED — BLID-087: healthcheck operacional para anomalias M2.

Cobre:
- 5 categorias de anomalia com severity (CRITICAL, HIGH, WARN, OK)
- Persistencia em m2_healthchecks
- Deteccao de episode stagnation, timestamp inconsistency, candle gaps,
  permanent lock state, deferred reward timeout

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

_SCHEMA_SIGNAL_EXECUTIONS = """
CREATE TABLE IF NOT EXISTS signal_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
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


def _make_db(schemas: str = "") -> tuple[str, sqlite3.Connection]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.executescript(
        _SCHEMA_TRAINING_EPISODES + _SCHEMA_SIGNAL_EXECUTIONS + schemas
    )
    conn.commit()
    return tmp.name, conn


# ---------------------------------------------------------------------------
# Classe 1 — Stagnacao de episodios
# ---------------------------------------------------------------------------

class TestEpisodeStagnation:
    """Detectar quando nenhum episodio foi criado nos ultimos N minutos."""

    def test_stagnation_returns_warn_when_no_recent_episodes(self) -> None:
        """Sem episodios recentes: severity WARN."""
        from core.model2.healthcheck import check_episode_stagnation

        db_path, conn = _make_db()
        # Inserir episodio antigo (2 horas atras)
        old_ts = int(time.time() * 1000) - 7_200_000
        conn.execute(
            "INSERT INTO training_episodes VALUES (1,'ep:1','run',1,'BTCUSDT','H4',"
            "'FILLED',?,  'win', 0.05,'pnl_realized',NULL,'{}','{}',?)",
            (old_ts, old_ts),
        )
        conn.commit()
        conn.close()

        result = check_episode_stagnation(db_path, stagnation_minutes=30)

        assert result["severity"] in ("WARN", "HIGH", "CRITICAL")
        assert "stagnation" in result["code"]

    def test_stagnation_returns_ok_when_recent_episode_exists(self) -> None:
        """Com episodio recente: severity OK."""
        from core.model2.healthcheck import check_episode_stagnation

        db_path, conn = _make_db()
        now_ms = int(time.time() * 1000)
        conn.execute(
            "INSERT INTO training_episodes VALUES (1,'ep:1','run',1,'BTCUSDT','H4',"
            "'FILLED',?,  'win', 0.05,'pnl_realized',NULL,'{}','{}',?)",
            (now_ms, now_ms),
        )
        conn.commit()
        conn.close()

        result = check_episode_stagnation(db_path, stagnation_minutes=30)

        assert result["severity"] == "OK"

    def test_stagnation_returns_critical_when_threshold_exceeded(self) -> None:
        """Estagnacao > 4h: severity CRITICAL."""
        from core.model2.healthcheck import check_episode_stagnation

        db_path, conn = _make_db()
        # Episodio muito antigo (5h atras)
        old_ts = int(time.time() * 1000) - 18_000_000
        conn.execute(
            "INSERT INTO training_episodes VALUES (1,'ep:1','run',1,'BTCUSDT','H4',"
            "'FILLED',?,'win',0.05,'pnl_realized',NULL,'{}','{}',?)",
            (old_ts, old_ts),
        )
        conn.commit()
        conn.close()

        result = check_episode_stagnation(db_path, stagnation_minutes=30)

        assert result["severity"] == "CRITICAL"


# ---------------------------------------------------------------------------
# Classe 2 — Deferred reward timeout
# ---------------------------------------------------------------------------

class TestDeferredRewardTimeout:
    """Detectar episodios com reward_lookup_at_ms vencido sem reward preenchido."""

    def test_detects_expired_deferred_reward(self) -> None:
        """Episodio com lookup_at no passado e reward NULL: HIGH."""
        from core.model2.healthcheck import check_deferred_reward_timeout

        db_path, conn = _make_db()
        now_ms = int(time.time() * 1000)
        expired_lookup = now_ms - 3_600_000  # 1h atras

        conn.execute(
            "INSERT INTO training_episodes VALUES (1,'ep:1','run',1,'BTCUSDT','H4',"
            "'BLOCKED',?,  'pending',NULL,'none',?,  '{}','{}',?)",
            (now_ms - 7_200_000, expired_lookup, now_ms - 7_200_000),
        )
        conn.commit()
        conn.close()

        result = check_deferred_reward_timeout(db_path, timeout_minutes=30)

        assert result["severity"] in ("HIGH", "CRITICAL")
        assert result.get("expired_count", 0) >= 1

    def test_no_violation_when_rewards_filled(self) -> None:
        """Episodio com reward preenchido: OK."""
        from core.model2.healthcheck import check_deferred_reward_timeout

        db_path, conn = _make_db()
        now_ms = int(time.time() * 1000)
        conn.execute(
            "INSERT INTO training_episodes VALUES (1,'ep:1','run',1,'BTCUSDT','H4',"
            "'BLOCKED',?,  'win',0.05,'counterfactual',?,  '{}','{}',?)",
            (now_ms, now_ms + 1000, now_ms),
        )
        conn.commit()
        conn.close()

        result = check_deferred_reward_timeout(db_path, timeout_minutes=30)

        assert result["severity"] == "OK"


# ---------------------------------------------------------------------------
# Classe 3 — Permanent lock (signal stuck in ENTRY_SENT)
# ---------------------------------------------------------------------------

class TestPermanentLockState:
    """Detectar signal_executions presas em ENTRY_SENT por muito tempo."""

    def test_detects_stuck_entry_sent(self) -> None:
        """ENTRY_SENT ha > 30min: HIGH."""
        from core.model2.healthcheck import check_permanent_lock

        db_path, conn = _make_db()
        stuck_ts = int(time.time() * 1000) - 3_600_000

        conn.execute(
            "INSERT INTO signal_executions VALUES (1,'BTCUSDT','ENTRY_SENT',?,?)",
            (stuck_ts, stuck_ts),
        )
        conn.commit()
        conn.close()

        result = check_permanent_lock(db_path, lock_minutes=30)

        assert result["severity"] in ("HIGH", "CRITICAL")
        assert result.get("stuck_count", 0) >= 1

    def test_no_violation_when_no_stuck_signals(self) -> None:
        """Sem sinais presos: OK."""
        from core.model2.healthcheck import check_permanent_lock

        db_path, conn = _make_db()
        conn.close()

        result = check_permanent_lock(db_path, lock_minutes=30)

        assert result["severity"] == "OK"


# ---------------------------------------------------------------------------
# Classe 4 — run_healthcheck orquestrador
# ---------------------------------------------------------------------------

class TestRunHealthcheck:
    """run_healthcheck executa todos os checks e persiste em m2_healthchecks."""

    def test_run_healthcheck_returns_summary_with_checks(self) -> None:
        """run_healthcheck deve retornar dict com lista de checks."""
        from core.model2.healthcheck import run_healthcheck

        db_path, conn = _make_db()
        conn.close()

        result = run_healthcheck(
            model2_db_path=db_path,
            stagnation_minutes=30,
            lock_minutes=30,
            deferred_timeout_minutes=30,
        )

        assert "checks" in result
        assert isinstance(result["checks"], list)
        assert len(result["checks"]) >= 3
        assert "overall_severity" in result
        assert result["overall_severity"] in ("OK", "WARN", "HIGH", "CRITICAL")

    def test_run_healthcheck_persists_to_m2_healthchecks(self) -> None:
        """run_healthcheck deve gravar resultado em m2_healthchecks."""
        from core.model2.healthcheck import run_healthcheck

        db_path, conn = _make_db()
        conn.close()

        run_healthcheck(
            model2_db_path=db_path,
            stagnation_minutes=30,
            lock_minutes=30,
            deferred_timeout_minutes=30,
        )

        with sqlite3.connect(db_path) as c:
            row = c.execute(
                "SELECT COUNT(*) FROM m2_healthchecks"
            ).fetchone()
        assert row is not None and row[0] >= 1

    def test_run_healthcheck_overall_severity_is_worst_check(self) -> None:
        """overall_severity e o pior severity entre todos os checks."""
        from core.model2.healthcheck import run_healthcheck

        db_path, conn = _make_db()
        # Criar episodio muito antigo para disparar CRITICAL
        old_ts = int(time.time() * 1000) - 18_000_000
        conn.execute(
            "INSERT INTO training_episodes VALUES (1,'ep:1','run',1,'BTCUSDT','H4',"
            "'FILLED',?,  'win',0.05,'pnl_realized',NULL,'{}','{}',?)",
            (old_ts, old_ts),
        )
        conn.commit()
        conn.close()

        result = run_healthcheck(
            model2_db_path=db_path,
            stagnation_minutes=30,
            lock_minutes=30,
            deferred_timeout_minutes=30,
        )

        assert result["overall_severity"] in ("WARN", "HIGH", "CRITICAL")
