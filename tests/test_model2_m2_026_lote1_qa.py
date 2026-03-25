# tests/test_model2_m2_026_lote1_qa.py
import pytest
import yaml
from datetime import datetime, timedelta
import os

# Módulos e classes a serem criados/modificados pelo engenheiro
from risk.circuit_breaker import CircuitBreaker, CircuitBreakerState
from monitoring.events import EventRecorder, CircuitBreakerTransition
from management.logging import LogRotationManager, LogFile

# --- M2-026.2: Observabilidade de circuit_breaker ---
@pytest.fixture
def event_recorder():
    return EventRecorder(append_only=True)

def test_m2_026_2_records_transition_event_on_breaker_open(event_recorder):
    """Deve registrar um evento de transição quando o circuit breaker abre."""
    breaker = CircuitBreaker(event_recorder=event_recorder)
    breaker.trip(reason="FAILURE_THRESHOLD_EXCEEDED")
    assert len(event_recorder.get_events()) == 1
    event = event_recorder.get_events()[0]
    assert isinstance(event, CircuitBreakerTransition)
    assert event.to_state == CircuitBreakerState.OPEN

def test_m2_026_2_transition_event_is_immutable(event_recorder):
    """O evento de transição registrado deve ser imutável."""
    breaker = CircuitBreaker(event_recorder=event_recorder)
    breaker.trip(reason="TEST")
    event = event_recorder.get_events()[0]
    with pytest.raises(Exception): # FrozenInstanceError or AttributeError
        event.reason = "CHANGED"

# --- M2-026.5: Governança de logs ---
@pytest.fixture
def log_rotation_manager():
    policy = yaml.safe_load("""retention_days:
  CRITICAL: 365
  INFO: 7""")
    return LogRotationManager(policy)

def test_m2_026_5_manager_identifies_info_log_for_deletion(log_rotation_manager):
    """Logs de nível INFO com mais de 7 dias devem ser marcados para exclusão."""
    old_log = LogFile("p.log", "INFO", datetime.now() - timedelta(days=8))
    actions = log_rotation_manager.plan_retention_actions([old_log])
    assert actions[0]["action"] == "DELETE"

def test_m2_026_5_manager_keeps_critical_log(log_rotation_manager):
    """Logs de nível CRITICAL devem ser mantidos por mais de 7 dias."""
    old_log = LogFile("p.log", "CRITICAL", datetime.now() - timedelta(days=100))
    actions = log_rotation_manager.plan_retention_actions([old_log])
    assert actions[0]["action"] == "KEEP"

def test_m2_026_5_manager_loads_config_from_file():
    """O gerenciador deve carregar sua política de um arquivo YAML centralizado."""
    # Create a dummy config file for the test
    config_path = "config/logging_retention_policy.yaml"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        f.write("""retention_days:
  CRITICAL: 365
  INFO: 7""")

    manager = LogRotationManager.from_config_file(config_path)
    assert manager.policy["retention_days"]["CRITICAL"] == 365
