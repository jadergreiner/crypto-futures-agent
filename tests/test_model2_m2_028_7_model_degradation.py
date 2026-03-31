import sqlite3
import pytest
from typing import Any
from pytest import MonkeyPatch

# Assuming these will be implemented by the SE
from core.model2.model_degradation_monitor import ModelDegradationMonitor
from core.model2.live_service import Model2LiveExecutionService
import config.risk_params as risk_params

@pytest.fixture
def memory_db() -> sqlite3.Connection:
    """Fixture that provides an in-memory SQLite database populated with training_episodes."""
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
    conn.commit()
    return conn


def insert_episode(conn: sqlite3.Connection, symbol: str, timeframe: str, reward: float | None = None, label: str = "pending") -> None:
    import time
    ts = int(time.time() * 1000)
    conn.execute(
        """
        INSERT INTO training_episodes (
            episode_key, cycle_run_id, execution_id, symbol, timeframe, status,
            event_timestamp, label, reward_proxy, features_json, target_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (f"ep_{ts}_{symbol}_{reward}", "run", 1, symbol, timeframe, "BLOCKED", ts, label, reward, "{}", "{}", ts)
    )
    conn.commit()


def test_model_degradation_monitor_calculates_win_rate_and_flags_degradation(memory_db: sqlite3.Connection):
    """
    Validar que o monitor calcula corretamente o win rate (positivos sobre totais verificados)
    e retorna status de degradacao se estiver abaixo do limite configurado.

    Requisito: O modulo deve calcular e sinalizar degradacao caso o score global/WinRate 
               caia abaixo do threshold parametrizado em config/risk_params.py.
    """
    # Arrange -> 1 Win, 3 Losses = 25% Win Rate
    # Threashold simulado = 40%
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.010, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.005, label="loss")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.002, label="loss")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.001, label="loss")
    
    # Pendente nao conta no win rate final
    insert_episode(memory_db, "BTCUSDT", "M5", reward=None, label="pending")
    
    threshold = 0.40 # 40% min win-rate
    window_episodes = 10
    
    # Act
    monitor = ModelDegradationMonitor(db_conn=memory_db, symbol="BTCUSDT", timeframe="M5")
    is_degraded, win_rate = monitor.check_degradation(threshold=threshold, window=window_episodes)
    
    # Assert
    assert is_degraded is True, "Expected model to be flagged as degraded (25% < 40%)"
    assert win_rate == 0.25, f"Expected 0.25 win rate, got {win_rate}"


def test_model_degradation_monitor_identifies_healthy_state(memory_db: sqlite3.Connection):
    """
    Validar que o monitor retorna False (saudável) quando o win-rate está acima do limite.

    Requisito: Não bloquear operacoes se o RL estiver performando bem.
    """
    # Arrange -> 3 Wins, 1 Loss = 75% Win Rate
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.010, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.005, label="hold_correct")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=0.002, label="win")
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.001, label="loss")
    
    threshold = 0.40
    window_episodes = 10
    
    # Act
    monitor = ModelDegradationMonitor(db_conn=memory_db, symbol="BTCUSDT", timeframe="M5")
    is_degraded, win_rate = monitor.check_degradation(threshold=threshold, window=window_episodes)
    
    # Assert
    assert is_degraded is False, "Expected model to NOT be flagged as degraded (75% > 40%)"
    assert win_rate == 0.75, f"Expected 0.75 win rate, got {win_rate}"


def test_model_degradation_monitor_fallback_on_insufficient_data(memory_db: sqlite3.Connection):
    """
    Validar que o monitor adota postura fail-safe (tolerante) se houverem poucos
    episodios concluidos para formar um veredito estatistico valido.

    Requisito: Ignora ruidos de pequenos N sem estourar block falso.
    """
    # Arrange -> Apenas 1 episode loss -> 0% Win Rate, mas sample size = 1
    insert_episode(memory_db, "BTCUSDT", "M5", reward=-0.005, label="loss")
    
    threshold = 0.40
    window_episodes = 10
    min_episodes_required = 3
    
    # Act
    monitor = ModelDegradationMonitor(db_conn=memory_db, symbol="BTCUSDT", timeframe="M5")
    is_degraded, win_rate = monitor.check_degradation(
        threshold=threshold, 
        window=window_episodes, 
        min_samples=min_episodes_required
    )
    
    # Assert
    assert is_degraded is False, "Expected False because N < min_samples (fail-safe)"


def test_live_service_blocks_admission_with_model_degradation_code(monkeypatch: MonkeyPatch):
    """
    Validar que o live_service injeta a verificacao de degradacao e, se verdadeira,
    rejeita a admissão com status BLOCKED e code MODEL_DEGRADATION durante o enforce guardrails.
    """
    # Arrange
    from core.model2.repository import Model2ThesisRepository
    from core.model2.live_execution import LiveExecutionConfig
    repository = Model2ThesisRepository(":memory:")
    config = LiveExecutionConfig(execution_mode="live")
    service = Model2LiveExecutionService(repository=repository, config=config)
    
    def mock_check_degradation(*args, **kwargs):
        # returns (is_degraded, win_rate)
        return (True, 0.10)
        
    monkeypatch.setattr(service, "_check_model_degradation", mock_check_degradation)
    
    # We mock mark_signal_execution_failed to intercept
    result_reason = ""
    class MockMarkFailed:
        def __init__(self, *args, **kwargs):
            self.current_status = "BLOCKED"
            self.reason = kwargs.get("reason", "")
    
    def mock_mark_failed(*args, **kwargs):
        nonlocal result_reason
        result_reason = kwargs.get("reason", "")
        return MockMarkFailed(*args, **kwargs)
        
    monkeypatch.setattr(service.repository, "mark_signal_execution_failed", mock_mark_failed)
    
    # Bypass original guardrails methods to reach ours 
    monkeypatch.setattr(service, "_ensure_live_exchange", lambda *args: None)
    monkeypatch.setattr(service, "_fetch_available_balance_with_retry", lambda *args: 1000.0)
    monkeypatch.setattr(service, "_snapshot_guardrail_state", lambda *args: {
        "risk_gate_status": "open",
        "risk_gate_allows_order": True
    })
    service.config.execution_mode = "live"
    
    test_execution = {
        "id": 123,
        "symbol": "BTCUSDT",
        "decision_id": 456
    }
    
    # Act
    result = service._enforce_guardrails_before_order(test_execution, 123456789)
    
    # Assert
    assert result is not None, "Expected rejection dictionary"
    assert result["status"] == "BLOCKED"
    assert result_reason == "MODEL_DEGRADATION"

