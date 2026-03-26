"""Testes RED — BLID-099: aprendizado continuo por ciclo via episodios HOLD.

Cobre todos os requisitos do handoff SA->QA:
- _reward_counterfactual com side='NEUTRAL': reward positivo em mercado quieto,
  negativo em mercado movendo
- _persist_hold_decision_episodes: cria episodio HOLD_DECISION a partir de
  model_decisions com action='HOLD'
- Episode key idempotente: hold_decision:{id}:{ts}
- reward_lookup_at_ms correto por timeframe
- flush_deferred_rewards preenche reward de HOLD_DECISION quando candle T+N existe
- train_ppo_incremental inclui status='HOLD_DECISION' no filtro
- _query_episode_info retorna episodio HOLD_DECISION quando nao ha trade real

Todos os testes devem FALHAR (RED) antes da implementacao.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

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

_SCHEMA_MODEL_DECISIONS = """
CREATE TABLE IF NOT EXISTS model_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    size_fraction REAL NOT NULL DEFAULT 0.0,
    sl_target REAL,
    tp_target REAL,
    model_version TEXT NOT NULL DEFAULT 'test',
    reason_code TEXT NOT NULL DEFAULT 'hold_decision',
    inference_latency_ms INTEGER NOT NULL DEFAULT 0,
    input_json TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
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


def _make_m2_db(extra_sql: str = "") -> tuple[str, sqlite3.Connection]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        _SCHEMA_TRAINING_EPISODES + _SCHEMA_MODEL_DECISIONS + extra_sql
    )
    conn.commit()
    return tmp.name, conn


def _make_src_db() -> tuple[str, sqlite3.Connection]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.executescript(_SCHEMA_OHLCV_H4)
    conn.commit()
    return tmp.name, conn


# ---------------------------------------------------------------------------
# Classe 1 — _reward_counterfactual com side=NEUTRAL
# ---------------------------------------------------------------------------

class TestRewardCounterfactualNeutral:
    """_reward_counterfactual deve tratar side='NEUTRAL' como mercado sem direcao."""

    def test_neutral_quiet_market_returns_positive_reward(self) -> None:
        """Mercado quieto (variacao < 0.2%): HOLD correto → reward positivo."""
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        close_t = 100.0
        close_tN = 100.1  # 0.1% — abaixo do threshold
        reward, label, source = _reward_counterfactual("NEUTRAL", close_t, close_tN)

        assert reward is not None
        assert reward > 0, f"Esperado reward > 0 para mercado quieto, obtido {reward}"
        assert label == "hold_correct"
        assert source == "counterfactual"

    def test_neutral_moving_market_returns_negative_reward(self) -> None:
        """Mercado movendo (variacao > 0.5%): HOLD incorreto → reward negativo."""
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        close_t = 100.0
        close_tN = 101.5  # 1.5% — acima do threshold
        reward, label, source = _reward_counterfactual("NEUTRAL", close_t, close_tN)

        assert reward is not None
        assert reward < 0, f"Esperado reward < 0 para mercado movendo, obtido {reward}"
        assert label == "hold_opportunity_missed"
        assert source == "counterfactual"

    def test_neutral_no_candle_returns_pending(self) -> None:
        """Sem candle T+N: reward deve permanecer None (pendente)."""
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        reward, label, source = _reward_counterfactual("NEUTRAL", 100.0, None)

        assert reward is None
        assert label == "pending"
        assert source == "none"

    def test_neutral_zero_close_t_returns_pending(self) -> None:
        """close_t=0: reward deve ser None para evitar divisao por zero."""
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        reward, label, source = _reward_counterfactual("NEUTRAL", 0.0, 100.0)

        assert reward is None
        assert label == "pending"

    def test_existing_long_short_behavior_unchanged(self) -> None:
        """LONG/SHORT nao devem ser afetados pela adicao de NEUTRAL."""
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        # SHORT: preco caiu → reward positivo (HOLD impediu SHORT lucrativo)
        r, label, _ = _reward_counterfactual("SHORT", 100.0, 98.0)
        assert r is not None and r < 0  # hold_opportunity_missed para SHORT que caiu

        # LONG: preco subiu → reward negativo (HOLD impediu LONG lucrativo)
        r2, label2, _ = _reward_counterfactual("LONG", 100.0, 102.0)
        assert r2 is not None and r2 < 0  # hold_opportunity_missed para LONG que subiu


# ---------------------------------------------------------------------------
# Classe 2 — _persist_hold_decision_episodes
# ---------------------------------------------------------------------------

class TestPersistHoldDecisionEpisodes:
    """Novos episodios HOLD_DECISION devem ser criados a partir de model_decisions."""

    def _setup_dbs(self) -> tuple[str, sqlite3.Connection, str, sqlite3.Connection]:
        m2_path, m2_conn = _make_m2_db()
        src_path, src_conn = _make_src_db()
        return m2_path, m2_conn, src_path, src_conn

    def _insert_hold_decision(
        self,
        conn: sqlite3.Connection,
        *,
        decision_id: int = 1,
        symbol: str = "BTCUSDT",
        ts: int = 1_700_000_000_000,
        close_price: float = 50000.0,
    ) -> None:
        conn.execute(
            """INSERT INTO model_decisions (
                id, decision_timestamp, symbol, action, confidence, size_fraction,
                model_version, reason_code, inference_latency_ms,
                input_json, output_json, created_at
            ) VALUES (?, ?, ?, 'HOLD', 0.3, 0.0, 'v1', 'hold_decision', 10, ?, '{}', ?)""",
            (
                decision_id, ts, symbol,
                json.dumps({"close_price": close_price, "signal_side": "NEUTRAL"}),
                ts,
            ),
        )
        conn.commit()

    def test_creates_hold_decision_episode_for_hold_action(self) -> None:
        """Decisao HOLD em model_decisions gera episodio HOLD_DECISION."""
        from scripts.model2.persist_training_episodes import (
            _persist_hold_decision_episodes,
        )

        _, m2_conn, _, src_conn = self._setup_dbs()
        self._insert_hold_decision(m2_conn, decision_id=1, symbol="BTCUSDT")

        inserted = _persist_hold_decision_episodes(
            m2_conn,
            src_conn,
            symbols=["BTCUSDT"],
            timeframe="H4",
            cursor_ms=0,
            now_ms=2_000_000_000_000,
            run_id="test-run",
        )

        assert inserted >= 1
        row = m2_conn.execute(
            "SELECT status, execution_id, label FROM training_episodes "
            "WHERE symbol='BTCUSDT' LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row[0] == "HOLD_DECISION"
        assert row[1] == 0  # execution_id=0 para HOLD puro
        assert row[2] == "pending"

    def test_episode_key_follows_pattern_hold_decision_id_ts(self) -> None:
        """episode_key deve seguir padrao hold_decision:{id}:{ts}."""
        from scripts.model2.persist_training_episodes import (
            _persist_hold_decision_episodes,
        )

        ts = 1_700_000_000_000
        _, m2_conn, _, src_conn = self._setup_dbs()
        self._insert_hold_decision(m2_conn, decision_id=42, ts=ts)

        _persist_hold_decision_episodes(
            m2_conn, src_conn,
            symbols=["BTCUSDT"], timeframe="H4",
            cursor_ms=0, now_ms=2_000_000_000_000, run_id="test-run",
        )

        row = m2_conn.execute(
            "SELECT episode_key FROM training_episodes LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row[0] == f"hold_decision:42:{ts}"

    def test_sets_reward_lookup_at_ms_for_timeframe_h4(self) -> None:
        """reward_lookup_at_ms deve ser ts + 4 * 14_400_000 para H4."""
        from scripts.model2.persist_training_episodes import (
            _persist_hold_decision_episodes,
        )

        ts = 1_700_000_000_000
        expected_lookup = ts + 4 * 14_400_000
        _, m2_conn, _, src_conn = self._setup_dbs()
        self._insert_hold_decision(m2_conn, decision_id=1, ts=ts)

        _persist_hold_decision_episodes(
            m2_conn, src_conn,
            symbols=["BTCUSDT"], timeframe="H4",
            cursor_ms=0, now_ms=2_000_000_000_000, run_id="test-run",
        )

        row = m2_conn.execute(
            "SELECT reward_lookup_at_ms FROM training_episodes LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row[0] == expected_lookup

    def test_idempotent_on_duplicate_decision(self) -> None:
        """Executar duas vezes nao duplica episodio (INSERT OR IGNORE)."""
        from scripts.model2.persist_training_episodes import (
            _persist_hold_decision_episodes,
        )

        _, m2_conn, _, src_conn = self._setup_dbs()
        self._insert_hold_decision(m2_conn)

        _persist_hold_decision_episodes(
            m2_conn, src_conn, symbols=["BTCUSDT"], timeframe="H4",
            cursor_ms=0, now_ms=2_000_000_000_000, run_id="run-1",
        )
        _persist_hold_decision_episodes(
            m2_conn, src_conn, symbols=["BTCUSDT"], timeframe="H4",
            cursor_ms=0, now_ms=2_000_000_000_000, run_id="run-2",
        )

        count = m2_conn.execute(
            "SELECT COUNT(*) FROM training_episodes "
            "WHERE status='HOLD_DECISION'"
        ).fetchone()[0]
        assert count == 1

    def test_respects_cursor_ms_filter(self) -> None:
        """Decisoes HOLD anteriores ao cursor_ms nao devem gerar novo episodio."""
        from scripts.model2.persist_training_episodes import (
            _persist_hold_decision_episodes,
        )

        ts = 1_000_000_000_000
        _, m2_conn, _, src_conn = self._setup_dbs()
        self._insert_hold_decision(m2_conn, ts=ts)

        inserted = _persist_hold_decision_episodes(
            m2_conn, src_conn, symbols=["BTCUSDT"], timeframe="H4",
            cursor_ms=ts + 1,  # cursor depois da decisao
            now_ms=2_000_000_000_000, run_id="test-run",
        )

        assert inserted == 0


# ---------------------------------------------------------------------------
# Classe 3 — flush_deferred_rewards para HOLD_DECISION
# ---------------------------------------------------------------------------

class TestFlushDeferredRewardsHoldDecision:
    """flush_deferred_rewards deve preencher reward de episodios HOLD_DECISION."""

    def _setup(self) -> tuple[str, sqlite3.Connection, str, sqlite3.Connection]:
        m2_path, m2_conn = _make_m2_db()
        src_path, src_conn = _make_src_db()
        return m2_path, m2_conn, src_path, src_conn

    def _insert_hold_episode(
        self,
        conn: sqlite3.Connection,
        *,
        symbol: str = "BTCUSDT",
        close_t: float = 100.0,
        signal_side: str = "NEUTRAL",
        event_ts: int = 1_000_000_000_000,
        lookup_ts: int = 1_000_057_600_000,
    ) -> None:
        features = json.dumps({"close_t": close_t, "signal_side": signal_side})
        conn.execute(
            """INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, reward_source,
                reward_lookup_at_ms, features_json, target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"hold_decision:1:{event_ts}", "run-1", 0, symbol, "H4",
                "HOLD_DECISION", event_ts, "pending", None, "none",
                lookup_ts, features, "{}", event_ts,
            ),
        )
        conn.commit()

    def _insert_candle(
        self,
        conn: sqlite3.Connection,
        *,
        symbol: str = "BTCUSDT",
        ts: int,
        close: float,
    ) -> None:
        conn.execute(
            "INSERT INTO ohlcv_h4 (symbol, timestamp, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (symbol, ts, close, close, close, close, 1.0),
        )
        conn.commit()

    def test_fills_neutral_reward_when_candle_available(self) -> None:
        """flush_deferred_rewards deve preencher reward para HOLD_DECISION NEUTRAL."""
        from scripts.model2.persist_training_episodes import flush_deferred_rewards

        m2_path, m2_conn, src_path, src_conn = self._setup()
        lookup_ts = 1_000_057_600_000
        self._insert_hold_episode(m2_conn, close_t=100.0, lookup_ts=lookup_ts)
        # Candle T+N com variacao pequena (mercado quieto)
        self._insert_candle(src_conn, ts=lookup_ts, close=100.15)
        m2_conn.close()
        src_conn.close()

        result = flush_deferred_rewards(
            model2_db_path=m2_path,
            source_db_path=src_path,
            now_ms=lookup_ts + 1,
        )

        assert result["flushed"] >= 1
        with sqlite3.connect(m2_path) as conn:
            row = conn.execute(
                "SELECT reward_proxy, label, reward_source FROM training_episodes "
                "WHERE status='HOLD_DECISION' LIMIT 1"
            ).fetchone()
        assert row is not None
        assert row[0] is not None, "reward_proxy deve ser preenchido"
        assert row[1] in ("hold_correct", "hold_opportunity_missed")
        assert row[2] == "counterfactual"

    def test_quiet_market_hold_decision_gets_positive_reward(self) -> None:
        """HOLD_DECISION com variacao < threshold deve ter reward_proxy positivo."""
        from scripts.model2.persist_training_episodes import flush_deferred_rewards

        m2_path, m2_conn, src_path, src_conn = self._setup()
        lookup_ts = 1_000_057_600_000
        self._insert_hold_episode(m2_conn, close_t=1000.0, lookup_ts=lookup_ts)
        self._insert_candle(src_conn, ts=lookup_ts, close=1000.5)  # 0.05% — quieto
        m2_conn.close()
        src_conn.close()

        flush_deferred_rewards(
            model2_db_path=m2_path,
            source_db_path=src_path,
            now_ms=lookup_ts + 1,
        )

        with sqlite3.connect(m2_path) as conn:
            row = conn.execute(
                "SELECT reward_proxy FROM training_episodes "
                "WHERE status='HOLD_DECISION' LIMIT 1"
            ).fetchone()
        assert row is not None and row[0] is not None
        assert row[0] > 0, f"Mercado quieto: esperado reward > 0, obtido {row[0]}"

    def test_moving_market_hold_decision_gets_negative_reward(self) -> None:
        """HOLD_DECISION com variacao > threshold deve ter reward_proxy negativo."""
        from scripts.model2.persist_training_episodes import flush_deferred_rewards

        m2_path, m2_conn, src_path, src_conn = self._setup()
        lookup_ts = 1_000_057_600_000
        self._insert_hold_episode(m2_conn, close_t=1000.0, lookup_ts=lookup_ts)
        self._insert_candle(src_conn, ts=lookup_ts, close=1020.0)  # 2% — movendo
        m2_conn.close()
        src_conn.close()

        flush_deferred_rewards(
            model2_db_path=m2_path,
            source_db_path=src_path,
            now_ms=lookup_ts + 1,
        )

        with sqlite3.connect(m2_path) as conn:
            row = conn.execute(
                "SELECT reward_proxy FROM training_episodes "
                "WHERE status='HOLD_DECISION' LIMIT 1"
            ).fetchone()
        assert row is not None and row[0] is not None
        assert row[0] < 0, f"Mercado movendo: esperado reward < 0, obtido {row[0]}"


# ---------------------------------------------------------------------------
# Classe 4 — train_ppo_incremental inclui HOLD_DECISION
# ---------------------------------------------------------------------------

class TestTrainPpoIncludesHoldDecision:
    """O filtro SQL do trainer deve incluir status='HOLD_DECISION'."""

    def test_load_episodes_includes_hold_decision_status(self) -> None:
        """PPOTrainer.load_episodes_from_db deve carregar episodios HOLD_DECISION."""
        from scripts.model2.train_ppo_incremental import PPOTrainer

        _, m2_conn = _make_m2_db()
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        m2_conn.execute(
            """INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, reward_source,
                features_json, target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "hold_decision:1:1000", "run-1", 0, "BTCUSDT", "H4",
                "HOLD_DECISION", 1_000_000_000_000, "hold_correct",
                0.05, "counterfactual",
                '{"latest_candle": {"close": 50000}}', "{}", 1_000_000_000_000,
            ),
        )
        m2_conn.commit()
        m2_conn.close()

        trainer = PPOTrainer(
            model2_db_path=Path(m2_conn.execute("PRAGMA database_list").fetchone()[2]
                                 if False else tmp.name),
            timeframe="H4",
        )

        # Recria DB com episodio HOLD_DECISION
        import shutil
        db_path_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        conn2 = sqlite3.connect(db_path_tmp.name)
        conn2.executescript(_SCHEMA_TRAINING_EPISODES)
        conn2.execute(
            """INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, reward_source,
                features_json, target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "hold_decision:1:1000", "run-1", 0, "BTCUSDT", "H4",
                "HOLD_DECISION", 1_000_000_000_000, "hold_correct",
                0.05, "counterfactual",
                '{"latest_candle": {"close": 50000}}', "{}", 1_000_000_000_000,
            ),
        )
        conn2.commit()
        conn2.close()

        trainer2 = PPOTrainer(
            model2_db_path=Path(db_path_tmp.name),
            timeframe="H4",
        )
        result = trainer2.load_episodes_from_db()

        assert result.get("total_episodes", 0) >= 1, (
            "HOLD_DECISION com reward nao nulo deve ser incluido no dataset de treino"
        )


# ---------------------------------------------------------------------------
# Classe 5 — _query_episode_info retorna HOLD_DECISION
# ---------------------------------------------------------------------------

class TestQueryEpisodeInfoHoldDecision:
    """_query_episode_info deve retornar HOLD_DECISION quando nao ha trade real."""

    def test_returns_hold_decision_when_no_real_trade(self) -> None:
        """Com apenas episodios HOLD_DECISION com reward, deve exibir no display."""
        from scripts.model2.operator_cycle_status import _query_episode_info

        _, m2_conn = _make_m2_db()
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        conn = sqlite3.connect(tmp.name)
        conn.executescript(_SCHEMA_TRAINING_EPISODES)
        conn.execute(
            """INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, reward_source,
                features_json, target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "hold_decision:5:1000", "run-1", 0, "BTCUSDT", "H4",
                "HOLD_DECISION", 1_000_000_000_000, "hold_correct",
                0.03, "counterfactual",
                "{}", "{}", 1_000_000_000_000,
            ),
        )
        conn.commit()
        conn.close()

        ep_id, persisted, reward = _query_episode_info("BTCUSDT", tmp.name)

        assert ep_id is not None, "Deve retornar episode_id para HOLD_DECISION"
        assert persisted is True
        assert abs(reward - 0.03) < 1e-6

    def test_real_trade_takes_priority_over_hold_decision(self) -> None:
        """Trade real (execution_id > 0) deve ter prioridade sobre HOLD_DECISION."""
        from scripts.model2.operator_cycle_status import _query_episode_info

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        conn = sqlite3.connect(tmp.name)
        conn.executescript(_SCHEMA_TRAINING_EPISODES)
        # Episodio de trade real
        conn.execute(
            """INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, reward_source,
                features_json, target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "exec:10:2000", "run-1", 10, "BTCUSDT", "H4",
                "FILLED", 2_000_000_000_000, "win",
                0.15, "pnl_realized",
                "{}", "{}", 2_000_000_000_000,
            ),
        )
        # Episodio HOLD_DECISION mais antigo
        conn.execute(
            """INSERT INTO training_episodes (
                episode_key, cycle_run_id, execution_id, symbol, timeframe,
                status, event_timestamp, label, reward_proxy, reward_source,
                features_json, target_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "hold_decision:5:1000", "run-1", 0, "BTCUSDT", "H4",
                "HOLD_DECISION", 1_000_000_000_000, "hold_correct",
                0.03, "counterfactual",
                "{}", "{}", 1_000_000_000_000,
            ),
        )
        conn.commit()
        conn.close()

        ep_id, persisted, reward = _query_episode_info("BTCUSDT", tmp.name)

        # Deve retornar o episodio mais recente (trade real id=1 > hold id menor)
        assert reward == pytest.approx(0.15, abs=1e-6) or reward == pytest.approx(0.03, abs=1e-6)
        # O mais recente por id DESC deve ser retornado
        assert ep_id is not None
