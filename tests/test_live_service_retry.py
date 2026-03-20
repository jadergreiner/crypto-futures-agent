"""Testes para retry exponencial em _arm_protection (RF-EX-002)."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, call, patch

from core.model2.live_service import (
    Model2LiveExecutionService,
    _PROTECTION_MAX_RETRIES,
    _PROTECTION_RETRY_BASE_DELAY_S,
)


def _make_mock_exchange(
    *,
    is_existing: bool = False,
    fail_times: int = 0,
) -> MagicMock:
    exchange = MagicMock()
    exchange.is_existing_protection_error.return_value = is_existing

    call_count = [0]

    def place_side_effect(**kwargs: Any) -> dict[str, Any]:
        call_count[0] += 1
        if call_count[0] <= fail_times:
            raise RuntimeError(f"Erro simulado na tentativa {call_count[0]}")
        return {"orderId": 999}

    exchange.place_protective_order.side_effect = place_side_effect
    exchange.extract_order_identifier.return_value = "999"
    return exchange


def test_retry_sucesso_na_terceira_tentativa() -> None:
    """Deve tentar ate 3x e ter sucesso na terceira."""
    service = Model2LiveExecutionService.__new__(Model2LiveExecutionService)
    exchange = _make_mock_exchange(fail_times=2)

    with patch("time.sleep") as mock_sleep:
        response, errors = service._place_protective_order_with_retry(
            exchange,
            symbol="BTCUSDT",
            signal_side="LONG",
            trigger_price=40000.0,
            order_type="STOP_MARKET",
        )

    assert response == {"orderId": 999}
    assert len(errors) == 2
    assert exchange.place_protective_order.call_count == 3
    # Deve ter dormido antes das tentativas 2 e 3
    assert mock_sleep.call_count == 2
    # Verifica back-off exponencial (1s, 2s)
    assert mock_sleep.call_args_list[0] == call(_PROTECTION_RETRY_BASE_DELAY_S * 1)
    assert mock_sleep.call_args_list[1] == call(_PROTECTION_RETRY_BASE_DELAY_S * 2)


def test_retry_falha_em_todas_as_tentativas() -> None:
    """Deve tentar _PROTECTION_MAX_RETRIES vezes e retornar erros."""
    service = Model2LiveExecutionService.__new__(Model2LiveExecutionService)
    exchange = _make_mock_exchange(fail_times=_PROTECTION_MAX_RETRIES + 5)

    with patch("time.sleep"):
        response, errors = service._place_protective_order_with_retry(
            exchange,
            symbol="BTCUSDT",
            signal_side="LONG",
            trigger_price=40000.0,
            order_type="STOP_MARKET",
        )

    assert exchange.place_protective_order.call_count == _PROTECTION_MAX_RETRIES
    assert len(errors) == _PROTECTION_MAX_RETRIES


def test_retry_nao_ocorre_em_erro_de_protecao_existente() -> None:
    """Se is_existing_protection_error, nao deve tentar novamente."""
    service = Model2LiveExecutionService.__new__(Model2LiveExecutionService)
    exchange = _make_mock_exchange(is_existing=True, fail_times=1)

    with patch("time.sleep") as mock_sleep:
        response, errors = service._place_protective_order_with_retry(
            exchange,
            symbol="BTCUSDT",
            signal_side="SHORT",
            trigger_price=50000.0,
            order_type="TAKE_PROFIT_MARKET",
        )

    # Deve retornar sem erros e sem retry
    assert errors == []
    assert mock_sleep.call_count == 0
    assert exchange.place_protective_order.call_count == 1


def test_retry_sucesso_imediato() -> None:
    """Sem falhas: retorna na primeira tentativa, sem sleep."""
    service = Model2LiveExecutionService.__new__(Model2LiveExecutionService)
    exchange = _make_mock_exchange(fail_times=0)

    with patch("time.sleep") as mock_sleep:
        response, errors = service._place_protective_order_with_retry(
            exchange,
            symbol="BTCUSDT",
            signal_side="LONG",
            trigger_price=39000.0,
            order_type="STOP_MARKET",
        )

    assert response == {"orderId": 999}
    assert errors == []
    assert mock_sleep.call_count == 0
    assert exchange.place_protective_order.call_count == 1


def test_constante_max_retries_minimo_3() -> None:
    """RF-EX-002 exige minimo 3 tentativas."""
    assert _PROTECTION_MAX_RETRIES >= 3
