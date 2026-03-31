import sqlite3
import time
import uuid

import pytest
from pytest import MonkeyPatch

from core.model2.live_service import Model2LiveExecutionService
from core.model2.model_degradation_monitor import (
    ModelDegradationMonitor,
    ModelDegradationThresholds,
)

@pytest.fixture
def memory_db() -> sqlite3.Connection:
    """Fornece banco em memoria com episodios e decisoes do modelo."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
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
            reward_lookup_at_ms INTEGER,
            features_json TEXT NOT NULL,
            target_json TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE model_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT 'HOLD',
            confidence REAL NOT NULL,
            size_fraction REAL NOT NULL DEFAULT 0.0,
            sl_target REAL,
            tp_target REAL,
            model_version TEXT NOT NULL DEFAULT 'rl-v1',
            reason_code TEXT NOT NULL DEFAULT 'RL_MODEL',
            inference_latency_ms INTEGER NOT NULL DEFAULT 0,
            input_json TEXT NOT NULL DEFAULT '{}',
            output_json TEXT NOT NULL DEFAULT '{}',
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def insert_episode(
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    *,
    reward: float | None = None,
    label: str = "pending",
) -> None:
    ts = int(time.time() * 1000)
    unique_key = f"ep_{uuid.uuid4().hex}_{symbol}_{label}"
    conn.execute(
        """
        INSERT INTO training_episodes (
            episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
            event_timestamp, label, reward_proxy, features_json, target_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (unique_key, "run", 1, symbol, timeframe, "BLOCKED", ts, label, reward, "{}", "{}", ts)
    )
    conn.commit()


def insert_model_decision(
    conn: sqlite3.Connection,
    symbol: str,
    *,
    confidence: float,
) -> None:
    ts = int(time.time() * 1000)
    conn.execute(
        """
        INSERT INTO model_decisions (
            decision_timestamp,
            symbol,
            confidence,
            created_at
        ) VALUES (?, ?, ?, ?)
        """,
        (ts, symbol, confidence, ts),
    )
    conn.commit()


def test_model_degradation_monitor_flags_low_recent_hit_rate(
    memory_db: sqlite3.Connection,
) -> None:
    """
    Valida degradacao quando a janela recente fica abaixo do hit rate minimo.
    """
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.010, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.005, label="loss")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.002, label="loss")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.001, label="loss")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=None, label="pending")

    monitor = ModelDegradationMonitor(db_conn=memory_db, symbol="BTCUSDT", timeframe="M5")
    result = monitor.evaluate(
        ModelDegradationThresholds(
            min_avg_confidence=0.30,
            min_hit_rate=0.40,
            min_hit_rate_delta=-0.20,
            evaluation_window=4,
            min_samples=3,
        )
    )

    assert result.is_degraded is True
    assert result.reason_code == "MODEL_DEGRADATION"
    assert result.trigger_reason == "hit_rate_below_threshold"
    assert result.recent_hit_rate == 0.25


def test_model_degradation_monitor_flags_low_confidence_with_symbol_threshold(
    memory_db: sqlite3.Connection,
) -> None:
    """
    Valida degradacao por confianca media baixa com threshold especifico do simbolo.
    """
    insert_model_decision(memory_db, "ETHUSDT", confidence=0.41)
    insert_model_decision(memory_db, "ETHUSDT", confidence=0.39)
    insert_model_decision(memory_db, "ETHUSDT", confidence=0.38)

    monitor = ModelDegradationMonitor(db_conn=memory_db, symbol="ETHUSDT", timeframe="M5")
    result = monitor.evaluate(
        ModelDegradationThresholds(
            min_avg_confidence=0.45,
            min_hit_rate=0.20,
            min_hit_rate_delta=-0.30,
            evaluation_window=3,
            min_samples=3,
        )
    )

    assert result.is_degraded is True
    assert result.trigger_reason == "confidence_below_threshold"
    assert result.avg_confidence == pytest.approx(0.393333, rel=1e-4)


def test_model_degradation_monitor_flags_regression_between_windows(
    memory_db: sqlite3.Connection,
) -> None:
    """
    Valida degradacao quando a janela recente regrede materialmente ante a anterior.
    """
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.010, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.005, label="hold_correct")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.002, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.001, label="win")

    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.010, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.005, label="loss")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.004, label="loss")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.003, label="loss")

    monitor = ModelDegradationMonitor(db_conn=memory_db, symbol="BTCUSDT", timeframe="M5")
    result = monitor.evaluate(
        ModelDegradationThresholds(
            min_avg_confidence=0.20,
            min_hit_rate=0.20,
            min_hit_rate_delta=-0.30,
            evaluation_window=4,
            min_samples=3,
        )
    )

    assert result.is_degraded is True
    assert result.trigger_reason == "hit_rate_regression"
    assert result.recent_hit_rate == 0.25
    assert result.previous_hit_rate == 1.0
    assert result.hit_rate_delta == -0.75


def test_model_degradation_monitor_identifies_healthy_state(
    memory_db: sqlite3.Connection,
) -> None:
    """
    Nao deve sinalizar degradacao quando confianca e hit rate permanecem saudaveis.
    """
    insert_model_decision(memory_db, "BTCUSDT", confidence=0.79)
    insert_model_decision(memory_db, "BTCUSDT", confidence=0.76)
    insert_model_decision(memory_db, "BTCUSDT", confidence=0.73)
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.010, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.005, label="hold_correct")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.002, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.001, label="loss")

    monitor = ModelDegradationMonitor(db_conn=memory_db, symbol="BTCUSDT", timeframe="M5")
    result = monitor.evaluate(
        ModelDegradationThresholds(
            min_avg_confidence=0.55,
            min_hit_rate=0.40,
            min_hit_rate_delta=-0.30,
            evaluation_window=4,
            min_samples=3,
        )
    )

    assert result.is_degraded is False
    assert result.trigger_reason == "healthy"


def test_live_service_emits_alert_and_priority_flag_without_blocking(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    Validar que o live_service registra prioridade de retreino e emite alerta
    MODEL_DEGRADATION sem bloquear a admissao.
    """
    from core.model2.repository import Model2ThesisRepository
    from core.model2.live_execution import LiveExecutionConfig

    repository = Model2ThesisRepository(":memory:")
    config = LiveExecutionConfig(
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        authorized_symbols=("BTCUSDT",),
        short_only=False,
        max_daily_entries=10,
        max_margin_per_position_usd=10.0,
        max_signal_age_ms=240 * 60_000,
        symbol_cooldown_ms=60_000,
        funding_rate_max_for_short=0.0005,
        leverage=5,
    )
    service = Model2LiveExecutionService(repository=repository, config=config)

    monkeypatch.setattr(
        service,
        "_check_model_degradation",
        lambda *args, **kwargs: {
            "is_degraded": True,
            "reason_code": "MODEL_DEGRADATION",
            "trigger_reason": "confidence_below_threshold",
            "recent_hit_rate": 0.20,
            "previous_hit_rate": 0.65,
            "hit_rate_delta": -0.45,
            "avg_confidence": 0.33,
            "thresholds": {
                "min_avg_confidence": 0.45,
                "min_hit_rate": 0.40,
                "min_hit_rate_delta": -0.20,
                "evaluation_window": 6,
                "min_samples": 3,
            },
        },
    )

    alertas: list[tuple[str, dict[str, object]]] = []
    auditoria: list[dict[str, object]] = []
    mark_failed_chamado = False

    def _mock_alerta(event_type: str, details: dict[str, object]) -> None:
        alertas.append((event_type, details))

    def _mock_auditoria(**kwargs: object) -> None:
        auditoria.append(kwargs)

    def _mock_mark_failed(*args: object, **kwargs: object) -> None:
        nonlocal mark_failed_chamado
        mark_failed_chamado = True
        raise AssertionError("nao deve bloquear execucao por MODEL_DEGRADATION")

    monkeypatch.setattr(service, "_emit_operational_alert", _mock_alerta)
    monkeypatch.setattr(service, "_record_training_audit", _mock_auditoria)
    monkeypatch.setattr(service.repository, "mark_signal_execution_failed", _mock_mark_failed)
    monkeypatch.setattr(service, "_ensure_live_exchange", lambda *args: None)
    monkeypatch.setattr(service, "_fetch_available_balance_with_retry", lambda *args: 1000.0)
    monkeypatch.setattr(service, "_snapshot_guardrail_state", lambda *args: {
        "risk_gate_status": "open",
        "risk_gate_allows_order": True,
        "circuit_breaker_state": "closed",
        "circuit_breaker_allows_trading": True,
    })
    test_execution = {
        "id": 123,
        "symbol": "BTCUSDT",
        "decision_id": 456,
        "timeframe": "M5",
    }

    result = service._enforce_guardrails_before_order(test_execution, 123456789)

    assert result is None
    assert mark_failed_chamado is False
    assert len(alertas) == 1
    assert alertas[0][0] == "MODEL_DEGRADATION"
    assert alertas[0][1]["symbol"] == "BTCUSDT"
    assert alertas[0][1]["reason_code"] == "MODEL_DEGRADATION"
    assert len(auditoria) == 1
    assert auditoria[0]["trigger_reason"] == "model_degradation_priority"
    assert auditoria[0]["status"] == "priority_requested"

