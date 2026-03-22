"""
Fixtures Compartilhadas para Testes QA-TDD

Este arquivo (conftest.py) centraliza fixtures pytest que podem ser reutilizadas
em múltiplas suites de testes. Coloque este arquivo em `tests/conftest.py`
no raiz da pasta tests/

Padrão pytest: conftest.py é automaticamente descoberto e carregado antes dos testes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any


# ============================================================================
# MOCKS DE SEGURANÇA (Risk Guardrails)
# ============================================================================

@pytest.fixture
def mock_risk_gate():
    """
    Mock do componente risk_gate (NÃO deve ser desabilitado).

    Use em testes que precisam validar chamada a risk_gate,
    mas sem desabilitar seu funcionamento.
    """
    with patch('core.risk.risk_gate.RiskGate') as mock:
        gate = Mock()
        gate.validate_order.return_value = True  # ATIVO
        gate.validate_position_size.return_value = True
        gate.check_leverage.return_value = True
        mock.return_value = gate
        yield gate


@pytest.fixture
def mock_circuit_breaker():
    """
    Mock do componente circuit_breaker (NÃO deve ser desabilitado).

    Use em testes que precisam validar estado do circuit_breaker,
    mas sem contornar sua proteção.
    """
    with patch('core.risk.circuit_breaker.CircuitBreaker') as mock:
        breaker = Mock()
        breaker.is_open.return_value = False  # FECHADO = ATIVO
        breaker.trip.return_value = None
        breaker.reset.return_value = None
        mock.return_value = breaker
        yield breaker


@pytest.fixture
def risk_gate_failing():
    """
    Mock do risk_gate em estado de REJEIÇÃO (para testes de fail-safe).

    Use quando quer testar que sistema bloqueia operações quando risk_gate falha.
    """
    with patch('core.risk.risk_gate.RiskGate') as mock:
        gate = Mock()
        gate.validate_order.return_value = False  # REJEITADO
        gate.validate_position_size.return_value = False
        gate.check_leverage.return_value = False
        mock.return_value = gate
        yield gate


@pytest.fixture
def circuit_breaker_open():
    """
    Mock do circuit_breaker em estado ABERTO (trip, pára tudo).

    Use quando quer testar que sistema bloqueia operações quando circuit ABRE.
    """
    with patch('core.risk.circuit_breaker.CircuitBreaker') as mock:
        breaker = Mock()
        breaker.is_open.return_value = True  # ABERTO = PAROU
        mock.return_value = breaker
        yield breaker


# ============================================================================
# MOCKS DE BANCO DE DADOS
# ============================================================================

@pytest.fixture
def mock_db():
    """
    Mock de conexão com banco de dados genérico.

    Fornece métodos comuns: query, insert, update, delete, close.
    """
    db = Mock()
    db.query.return_value = []
    db.insert.return_value = True
    db.update.return_value = True
    db.delete.return_value = True
    db.close.return_value = None
    yield db
    db.close()


@pytest.fixture
def mock_db_with_existing_record():
    """
    Mock de banco já contendo um registro.

    Use para testar idempotência (retry encontra record existente).
    """
    db = Mock()
    existing_record = {
        "decision_id": "dec_20260322_001",
        "symbol": "BTCUSDT",
        "status": "CREATED",
    }
    db.query.return_value = [existing_record]  # Retorna registro existente
    db.insert.return_value = False  # INSERT falha (duplicata)
    yield db


# ============================================================================
# FIXTURES DE DADOS TEST
# ============================================================================

@pytest.fixture
def valid_signal() -> Dict[str, Any]:
    """
    Fixture: signal válido conforme contrato de OrderLayer.

    Contém todos os campos obrigatórios e valores realistas.
    """
    return {
        "status": "CREATED",
        "symbol": "BTCUSDT",
        "decision_id": "dec_20260322_001",
        "entry_price": 50000.0,
        "take_profit": 51000.0,
        "stop_loss": 49000.0,
        "quantity": 1.0,
        "side": "LONG",
        "timeframe": "1h",
    }


@pytest.fixture
def invalid_signal_no_decision_id() -> Dict[str, Any]:
    """
    Fixture: signal inválido (falta decision_id).

    Use para testar rejeição de signals incompletas.
    """
    return {
        "status": "CREATED",
        "symbol": "BTCUSDT",
        # Falta decision_id — deve ser rejeitado
        "entry_price": 50000.0,
    }


@pytest.fixture
def invalid_signal_no_symbol() -> Dict[str, Any]:
    """
    Fixture: signal inválido (falta symbol).

    Use para testar validação de instrument válido.
    """
    return {
        "status": "CREATED",
        # Falta symbol — deve ser rejeitado
        "decision_id": "dec_20260322_001",
        "entry_price": 50000.0,
    }


@pytest.fixture
def invalid_signal_bad_decision_id_format() -> Dict[str, Any]:
    """
    Fixture: signal com decision_id em format incorreto.

    Use para testar validação de pattern de decision_id.
    """
    return {
        "status": "CREATED",
        "symbol": "BTCUSDT",
        "decision_id": "INVALID_FORMAT",  # Nao segue pattern dec_YYYYMMDD_###
        "entry_price": 50000.0,
    }


@pytest.fixture
def valid_signals_batch() -> list:
    """
    Fixture: múltiplos signals válidos para testes de lote.

    Use quando testar processamento de múltiplas orders.
    """
    return [
        {
            "status": "CREATED",
            "symbol": "BTCUSDT",
            "decision_id": f"dec_20260322_{i:03d}",
            "entry_price": 50000.0 + (i * 1000),
            "take_profit": 51000.0 + (i * 1000),
            "stop_loss": 49000.0 + (i * 1000),
        }
        for i in range(5)
    ]


# ============================================================================
# FIXTURES DE CONFIGURAÇÃO
# ============================================================================

@pytest.fixture
def test_config():
    """
    Fixture: configuração padrão para testes.

    Retorna dict com settings de ambiente, timeouts, etc.
    """
    return {
        "db_path": ":memory:",  # SQLite em memória para testes
        "timeout": 5000,  # milliseconds
        "max_retries": 3,
        "log_level": "DEBUG",
    }


# ============================================================================
# FIXTURES DE LOGGER
# ============================================================================

@pytest.fixture
def capture_logs(caplog):
    """
    Fixture: captura logs durante teste para validação.

    Use para testar que mensagens corretas são logadas.

    Exemplo:
        def test_log_message(capture_logs):
            logger.warning("Important message")
            assert "Important message" in capture_logs.text
    """
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


# ============================================================================
# CLEANUP & TEARDOWN
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    Fixture automática: cleanup após cada teste.

    Remove efeitos colaterais (arquivos temp, mocks, etc).
    """
    yield  # Teste roda aqui

    # Cleanup
    import tempfile
    import shutil
    # Limpar diretórios temp se criados durante teste


# ============================================================================
# MARCADORES CUSTOMIZADOS
# ============================================================================

def pytest_configure(config):
    """Registra marcadores customizados para categorizar testes."""
    config.addinivalue_line(
        "markers",
        "integration: marca teste como integração (não apenas unitário)"
    )
    config.addinivalue_line(
        "markers",
        "risk: marca teste que valida guardrail de risco crítico"
    )
    config.addinivalue_line(
        "markers",
        "slow: marca teste que é lento (redis, db, etc)"
    )


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

"""
Exemplo de teste usando fixtures compartilhadas:

def test_order_layer_with_fixtures(valid_signal, mock_risk_gate, mock_db):
    from core.model2.order_layer import OrderLayer

    layer = OrderLayer(db=mock_db)
    result = layer.admit(valid_signal)

    assert result is True
    mock_risk_gate.validate_order.assert_called_once()


@pytest.mark.risk
def test_order_layer_fails_when_risk_gate_rejects(
    valid_signal, risk_gate_failing
):
    from core.model2.order_layer import OrderLayer

    layer = OrderLayer()
    result = layer.admit(valid_signal)

    # Fail-safe: deve rejeitar quando risk_gate falha
    assert result is False


@pytest.mark.integration
def test_order_layer_persists_to_db(valid_signal, mock_db):
    from core.model2.order_layer import OrderLayer

    layer = OrderLayer(db=mock_db)
    layer.admit(valid_signal)

    mock_db.insert.assert_called_once()
"""
