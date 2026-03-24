# -*- coding: utf-8 -*-
"""Testes para o módulo de resiliência."""

import time
from unittest.mock import Mock, patch

import pytest

from core.resilience import resilient_operation, PermanentFailure


def test_resilient_operation_success_first_try():
    """
    Valida que a função decorada é chamada uma vez e seu resultado é
    retornado quando não há exceções.
    """
    mock_function = Mock(return_value="success")

    @resilient_operation()
    def decorated_function():
        return mock_function()

    result = decorated_function()

    assert result == "success"
    mock_function.assert_called_once()


@patch("time.sleep")
def test_resilient_operation_retries_on_transient_error(mock_sleep):
    """
    Valida a lógica de retry com backoff para falhas transitórias.
    """
    mock_function = Mock(side_effect=[ConnectionError, "success"])

    @resilient_operation(initial_delay=0.1, backoff_factor=2)
    def decorated_function():
        return mock_function()

    result = decorated_function()

    assert result == "success"
    assert mock_function.call_count == 2
    mock_sleep.assert_called_once_with(0.1)


@patch("time.sleep")
def test_resilient_operation_fails_after_max_retries(mock_sleep):
    """
    Valida que a operação falha após o número máximo de tentativas
    para erros transitórios.
    """
    mock_function = Mock(side_effect=ConnectionError)

    @resilient_operation(max_retries=3, initial_delay=0.1)
    def decorated_function():
        return mock_function()

    with pytest.raises(ConnectionError):
        decorated_function()

    assert mock_function.call_count == 3
    assert mock_sleep.call_count == 2


def test_resilient_operation_immediate_failure_on_permanent_error():
    """
    Valida que a operação falha imediatamente, sem retries, para
    uma PermanentFailure.
    """
    mock_function = Mock(side_effect=PermanentFailure)

    @resilient_operation()
    def decorated_function():
        return mock_function()

    with pytest.raises(PermanentFailure):
        decorated_function()

    mock_function.assert_called_once()


@patch("core.resilience.get_risk_gate")
def test_resilient_operation_fail_fast_if_circuit_breaker_is_open(mock_get_risk_gate):
    """
    Valida que a operação falha imediatamente se o circuit breaker estiver aberto.
    """
    mock_function = Mock()
    mock_gate = Mock()
    mock_gate.check_circuit_breaker.return_value = (True, {})
    mock_get_risk_gate.return_value = mock_gate

    from core.resilience import resilient_operation

    @resilient_operation()
    def decorated_function():
        return mock_function()

    with pytest.raises(PermanentFailure, match="Circuit breaker is open"):
        decorated_function()

    mock_function.assert_not_called()
    mock_gate.check_circuit_breaker.assert_called_once()
