"""Suite RED — M2-020.7: reward para operar e nao operar.

Objetivo: formalizar contrato de reward deterministico para:
- operar (EXECUTED/EXITED) com PnL liquido de custo operacional
- nao operar (HOLD) com diferenciacao counterfactual
- penalidades de overtrading e risco excessivo no consumo de treino
- exibicao operacional sem vies cronico para reward neutro

Esta suite e RED por design: falhas iniciais sao esperadas antes do GREEN.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pytest


_ROUNDTRIP_OPERATIONAL_COST = 0.002  # 20 bps


def _expected_net_reward(raw_reward: float) -> float:
    return float(raw_reward - _ROUNDTRIP_OPERATIONAL_COST)


def _create_training_episodes_schema(conn: sqlite3.Connection) -> None:
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
            features_json TEXT,
            target_json TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def _insert_episode(
    conn: sqlite3.Connection,
    *,
    episode_key: str,
    status: str,
    reward_proxy: float,
    label: str = "win",
    features: dict[str, Any] | None = None,
    timeframe: str = "H4",
) -> None:
    conn.execute(
        """
        INSERT INTO training_episodes (
            episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
            event_timestamp, label, reward_proxy, features_json, target_json, created_at
        ) VALUES (?, 'run-m2-020-7', 1, 'BTCUSDT', ?, ?, 1700000000000, ?, ?, ?, '{}', 1700000000000)
        """,
        (
            episode_key,
            timeframe,
            status,
            label,
            reward_proxy,
            json.dumps(features or {}, ensure_ascii=True, sort_keys=True),
        ),
    )
    conn.commit()


class TestRewardLabelNetCostContract:
    """Unitarios: reward de operar precisa ser PnL liquido de custo operacional."""

    def test_reward_label_long_win_applies_operational_cost(self) -> None:
        """LONG win deve descontar custo operacional roundtrip."""
        from scripts.model2.persist_training_episodes import _reward_label

        reward, label, source = _reward_label("LONG", 100.0, 110.0, apply_operational_cost=True)
        assert label == "win"
        assert source == "pnl_realized"
        assert reward is not None
        assert reward == pytest.approx(_expected_net_reward(0.10), abs=1e-9)

    def test_reward_label_short_win_applies_operational_cost(self) -> None:
        """SHORT win deve descontar custo operacional roundtrip."""
        from scripts.model2.persist_training_episodes import _reward_label

        reward, label, source = _reward_label("SHORT", 100.0, 90.0, apply_operational_cost=True)
        assert label == "win"
        assert source == "pnl_realized"
        assert reward is not None
        assert reward == pytest.approx(_expected_net_reward(0.10), abs=1e-9)

    def test_reward_label_long_loss_includes_operational_cost(self) -> None:
        """LONG loss deve ficar mais negativo apos custo operacional."""
        from scripts.model2.persist_training_episodes import _reward_label

        reward, label, source = _reward_label("LONG", 100.0, 90.0, apply_operational_cost=True)
        assert label == "loss"
        assert source == "pnl_realized"
        assert reward is not None
        assert reward == pytest.approx(_expected_net_reward(-0.10), abs=1e-9)

    def test_reward_label_short_loss_includes_operational_cost(self) -> None:
        """SHORT loss deve ficar mais negativo apos custo operacional."""
        from scripts.model2.persist_training_episodes import _reward_label

        reward, label, source = _reward_label("SHORT", 100.0, 110.0, apply_operational_cost=True)
        assert label == "loss"
        assert source == "pnl_realized"
        assert reward is not None
        assert reward == pytest.approx(_expected_net_reward(-0.10), abs=1e-9)


class TestRewardPenaltiesContract:
    """Unitarios: overtrading/risco precisam penalizar reward no consumo de treino."""

    def test_incremental_compute_reward_penalizes_overtrading(self) -> None:
        from scripts.model2.train_ppo_incremental import PPOTrainer

        trainer = PPOTrainer(model2_db_path=Path("db/modelo2.db"))
        episode = {"reward_proxy": 0.30, "label": "win"}
        features = {"ops_flags": {"overtrading": True}}

        reward = trainer._compute_reward(episode, features)  # pylint: disable=protected-access
        assert reward < 0.30

    def test_incremental_compute_reward_penalizes_risk_gate_blocked(self) -> None:
        from scripts.model2.train_ppo_incremental import PPOTrainer

        trainer = PPOTrainer(model2_db_path=Path("db/modelo2.db"))
        episode = {"reward_proxy": 0.30, "label": "win"}
        features = {"risk_state": {"risk_gate_status": "BLOCKED"}}

        reward = trainer._compute_reward(episode, features)  # pylint: disable=protected-access
        assert reward < 0.30

    def test_lstm_compute_reward_penalizes_overtrading_and_risk(self) -> None:
        from scripts.model2.train_ppo_lstm import PPOLstmTrainer

        trainer = PPOLstmTrainer(model2_db_path=Path("db/modelo2.db"), policy_type="mlp")
        episode = {"reward_proxy": 0.30, "label": "win"}
        features = {
            "ops_flags": {"overtrading": True},
            "risk_state": {"risk_gate_status": "BLOCKED"},
        }

        reward = trainer._compute_reward(episode, features)  # pylint: disable=protected-access
        assert reward <= 0.0

    def test_compute_reward_penalizes_circuit_breaker_tripped(self) -> None:
        from scripts.model2.train_ppo_incremental import PPOTrainer

        trainer = PPOTrainer(model2_db_path=Path("db/modelo2.db"))
        episode = {"reward_proxy": 0.25, "label": "win"}
        features = {"risk_state": {"circuit_breaker_state": "OPEN"}}

        reward = trainer._compute_reward(episode, features)  # pylint: disable=protected-access
        assert reward <= 0.0


class TestRewardIntegrationContract:
    """Integracao: pipeline de treino deve consumir penalidades de forma consistente."""

    def test_incremental_dataset_applies_episode_penalties(self, tmp_path: Path) -> None:
        from scripts.model2.train_ppo_incremental import PPOTrainer

        db_path = tmp_path / "m2_020_7_incremental.db"
        with sqlite3.connect(db_path) as conn:
            _create_training_episodes_schema(conn)
            _insert_episode(
                conn,
                episode_key="exec:1:1000",
                status="EXECUTED",
                reward_proxy=0.30,
                features={
                    "latest_candle": {"close": 50000.0, "volume": 100.0},
                    "signal_snapshot": {"rsi": 50.0, "direction": "long"},
                    "volatility": 0.01,
                },
            )
            _insert_episode(
                conn,
                episode_key="exec:2:1000",
                status="EXECUTED",
                reward_proxy=0.30,
                features={
                    "latest_candle": {"close": 51000.0, "volume": 100.0},
                    "signal_snapshot": {"rsi": 55.0, "direction": "long"},
                    "volatility": 0.01,
                    "ops_flags": {"overtrading": True},
                    "risk_state": {"risk_gate_status": "BLOCKED"},
                },
            )

        trainer = PPOTrainer(model2_db_path=db_path, timeframe="H4")
        load_result = trainer.load_episodes_from_db()
        assert load_result["total_episodes"] == 2
        dataset_result = trainer.episodes_to_training_dataset()
        assert dataset_result["status"] == "ok"
        assert trainer.rewards_data is not None
        assert float(trainer.rewards_data[1]) < float(trainer.rewards_data[0])

    def test_lstm_dataset_applies_episode_penalties(self, tmp_path: Path) -> None:
        from scripts.model2.train_ppo_lstm import PPOLstmTrainer

        db_path = tmp_path / "m2_020_7_lstm.db"
        with sqlite3.connect(db_path) as conn:
            _create_training_episodes_schema(conn)
            _insert_episode(
                conn,
                episode_key="exec:1:1000",
                status="EXECUTED",
                reward_proxy=0.30,
                features={"latest_candle": {"close": 50000.0}},
            )
            _insert_episode(
                conn,
                episode_key="exec:2:1000",
                status="EXECUTED",
                reward_proxy=0.30,
                features={
                    "latest_candle": {"close": 51000.0},
                    "ops_flags": {"overtrading": True},
                    "risk_state": {"risk_gate_status": "BLOCKED"},
                },
            )

        trainer = PPOLstmTrainer(model2_db_path=db_path, timeframe="H4", policy_type="mlp")
        load_result = trainer.load_episodes_from_db()
        assert load_result["total_episodes"] == 2
        dataset_result = trainer.episodes_to_training_dataset()
        assert dataset_result["status"] == "ok"
        assert trainer.rewards_data is not None
        assert float(trainer.rewards_data[1]) < float(trainer.rewards_data[0])

    def test_operator_cycle_status_prefers_non_zero_reward_over_latest_zero(self, tmp_path: Path) -> None:
        from scripts.model2.operator_cycle_status import _query_episode_info

        db_path = tmp_path / "m2_020_7_operator.db"
        with sqlite3.connect(db_path) as conn:
            _create_training_episodes_schema(conn)
            _insert_episode(
                conn,
                episode_key="hold:1:1000",
                status="HOLD_DECISION",
                reward_proxy=0.03,
                features={},
            )
            _insert_episode(
                conn,
                episode_key="hold:2:1000",
                status="HOLD_DECISION",
                reward_proxy=0.0,
                features={},
            )

        episode_id, persisted, reward = _query_episode_info("BTCUSDT", str(db_path))
        assert episode_id is not None
        assert persisted is True
        assert reward > 0.0

    def test_hold_counterfactual_labels_remain_deterministic(self) -> None:
        from scripts.model2.persist_training_episodes import _reward_counterfactual

        reward, label, source = _reward_counterfactual("NEUTRAL", 100.0, 102.0)
        assert reward is not None
        assert reward < 0.0
        assert label == "hold_opportunity_missed"
        assert source == "counterfactual"


class TestRiskRegressionContract:
    """Regressao/risk: contratos de risco e idempotencia devem permanecer ativos."""

    def test_incremental_compute_reward_penalizes_duplicate_decision_context(self) -> None:
        from scripts.model2.train_ppo_incremental import PPOTrainer

        trainer = PPOTrainer(model2_db_path=Path("db/modelo2.db"))
        episode = {"reward_proxy": 0.20, "label": "win"}
        features = {"decision_context": {"duplicate_decision_id": True}}

        reward = trainer._compute_reward(episode, features)  # pylint: disable=protected-access
        assert reward < 0.0

    def test_compute_reward_fail_safe_with_missing_metadata(self) -> None:
        from scripts.model2.train_ppo_incremental import PPOTrainer

        trainer = PPOTrainer(model2_db_path=Path("db/modelo2.db"))
        episode = {"reward_proxy": 0.15, "label": "win"}

        reward = trainer._compute_reward(episode, {})  # pylint: disable=protected-access
        assert isinstance(reward, float)
        assert reward == pytest.approx(0.15, abs=1e-9)

    def test_lstm_compute_reward_fail_safe_with_missing_metadata(self) -> None:
        from scripts.model2.train_ppo_lstm import PPOLstmTrainer

        trainer = PPOLstmTrainer(model2_db_path=Path("db/modelo2.db"), policy_type="mlp")
        episode = {"reward_proxy": 0.15, "label": "win"}

        reward = trainer._compute_reward(episode, {})  # pylint: disable=protected-access
        assert isinstance(reward, float)
        assert reward == pytest.approx(0.15, abs=1e-9)
