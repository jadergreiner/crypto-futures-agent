"""
Suite RED para M2-024.4 — Retry controlado para falha transitória de exchange.

Testa:
  R1: classify_exchange_exception distingue transient vs permanent
  R2: exchange_retry_with_budget executa retry em transient até budget
  R3: ExchangeRetryBudgetError tem campos obrigatórios e reason_code no catálogo
  R4: _place_market_entry_with_retry em live_service usa exchange_retry_with_budget
  R5: Após budget esgotado, registra reason_code=timeout e retorna fail-safe
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# R1: classify_exchange_exception
# ---------------------------------------------------------------------------

class TestClassifyExchangeException:
    """R1: classify_exchange_exception retorna 'transient' ou 'permanent'."""

    def test_connection_error_e_transient(self) -> None:
        """ConnectionError deve ser classificado como transient."""
        from core.model2.io_retry import classify_exchange_exception

        exc = ConnectionError("connection refused")
        result = classify_exchange_exception(exc)
        assert result == "transient"

    def test_timeout_error_e_transient(self) -> None:
        """TimeoutError deve ser classificado como transient."""
        from core.model2.io_retry import classify_exchange_exception

        exc = TimeoutError("request timed out")
        result = classify_exchange_exception(exc)
        assert result == "transient"

    def test_excecao_generica_e_permanent(self) -> None:
        """Exceções genéricas não mapeadas são permanent."""
        from core.model2.io_retry import classify_exchange_exception

        exc = ValueError("bad quantity")
        result = classify_exchange_exception(exc)
        assert result == "permanent"

    def test_retorna_literal_valido(self) -> None:
        """Retorno deve ser exatamente 'transient' ou 'permanent'."""
        from core.model2.io_retry import classify_exchange_exception

        result_t = classify_exchange_exception(ConnectionError())
        result_p = classify_exchange_exception(ValueError())
        assert result_t in ("transient", "permanent")
        assert result_p in ("transient", "permanent")


# ---------------------------------------------------------------------------
# R2: exchange_retry_with_budget
# ---------------------------------------------------------------------------

class TestExchangeRetryWithBudget:
    """R2: exchange_retry_with_budget executa retry em transient até budget."""

    def test_sucesso_na_primeira_tentativa(self) -> None:
        """Função que sucede na 1ª tentativa não faz retry."""
        from core.model2.io_retry import exchange_retry_with_budget

        fn = MagicMock(return_value={"status": "ok"})
        result = exchange_retry_with_budget(fn, max_attempts=3)
        assert result == {"status": "ok"}
        assert fn.call_count == 1

    def test_retry_em_transient_ate_sucesso(self) -> None:
        """Função que falha com transient e depois sucede deve tentar novamente."""
        from core.model2.io_retry import exchange_retry_with_budget

        fn = MagicMock(side_effect=[ConnectionError("fail"), {"status": "ok"}])
        result = exchange_retry_with_budget(fn, max_attempts=3, backoff=(0.0, 0.0))
        assert result == {"status": "ok"}
        assert fn.call_count == 2

    def test_budget_esgotado_lanca_exchange_retry_budget_error(self) -> None:
        """Após max_attempts em transient, deve lançar ExchangeRetryBudgetError."""
        from core.model2.io_retry import exchange_retry_with_budget, ExchangeRetryBudgetError

        fn = MagicMock(side_effect=ConnectionError("always fails"))
        with pytest.raises(ExchangeRetryBudgetError):
            exchange_retry_with_budget(fn, max_attempts=3, backoff=(0.0, 0.0, 0.0))
        assert fn.call_count == 3

    def test_permanent_nao_faz_retry(self) -> None:
        """Exceção permanent deve lançar ExchangeRetryBudgetError imediatamente (1 tentativa)."""
        from core.model2.io_retry import exchange_retry_with_budget, ExchangeRetryBudgetError

        fn = MagicMock(side_effect=ValueError("bad qty"))
        with pytest.raises(ExchangeRetryBudgetError):
            exchange_retry_with_budget(fn, max_attempts=3, backoff=(0.0, 0.0, 0.0))
        assert fn.call_count == 1

    def test_default_max_attempts_e_3(self) -> None:
        """Default de max_attempts deve ser 3."""
        from core.model2.io_retry import exchange_retry_with_budget, ExchangeRetryBudgetError

        fn = MagicMock(side_effect=ConnectionError("fail"))
        with pytest.raises(ExchangeRetryBudgetError) as exc_info:
            exchange_retry_with_budget(fn, backoff=(0.0, 0.0, 0.0))
        assert exc_info.value.attempt_count == 3


# ---------------------------------------------------------------------------
# R3: ExchangeRetryBudgetError
# ---------------------------------------------------------------------------

class TestExchangeRetryBudgetError:
    """R3: ExchangeRetryBudgetError tem campos obrigatórios."""

    def test_tem_attempt_count(self) -> None:
        """ExchangeRetryBudgetError deve ter campo attempt_count."""
        from core.model2.io_retry import ExchangeRetryBudgetError

        exc = ExchangeRetryBudgetError(
            attempt_count=3,
            reason_code="timeout",
            last_exception=ConnectionError("fail"),
        )
        assert exc.attempt_count == 3

    def test_tem_reason_code(self) -> None:
        """ExchangeRetryBudgetError deve ter campo reason_code."""
        from core.model2.io_retry import ExchangeRetryBudgetError

        exc = ExchangeRetryBudgetError(
            attempt_count=3,
            reason_code="timeout",
            last_exception=ConnectionError("fail"),
        )
        assert exc.reason_code == "timeout"

    def test_tem_last_exception(self) -> None:
        """ExchangeRetryBudgetError deve ter campo last_exception."""
        from core.model2.io_retry import ExchangeRetryBudgetError

        cause = ConnectionError("fail")
        exc = ExchangeRetryBudgetError(
            attempt_count=3,
            reason_code="timeout",
            last_exception=cause,
        )
        assert exc.last_exception is cause

    def test_reason_code_no_catalogo(self) -> None:
        """reason_code padrão deve existir no REASON_CODE_CATALOG."""
        from core.model2.io_retry import ExchangeRetryBudgetError
        from core.model2.live_execution import REASON_CODE_CATALOG

        exc = ExchangeRetryBudgetError(
            attempt_count=3,
            reason_code="timeout",
            last_exception=ConnectionError("fail"),
        )
        assert exc.reason_code in REASON_CODE_CATALOG

    def test_e_subclasse_de_exception(self) -> None:
        """ExchangeRetryBudgetError deve herdar de Exception."""
        from core.model2.io_retry import ExchangeRetryBudgetError

        exc = ExchangeRetryBudgetError(
            attempt_count=1,
            reason_code="timeout",
            last_exception=ValueError(),
        )
        assert isinstance(exc, Exception)


# ---------------------------------------------------------------------------
# R4 + R5: _place_market_entry_with_retry em live_service
# ---------------------------------------------------------------------------

class TestPlaceMarketEntryWithRetry:
    """R4/R5: _place_market_entry_with_retry usa exchange_retry e fail-safe."""

    def _make_service(self) -> object:
        """Cria instância mínima de Model2LiveExecutionService para testes."""
        from core.model2.live_service import Model2LiveExecutionService as LiveExecutionService

        service = LiveExecutionService.__new__(LiveExecutionService)
        service.exchange = MagicMock()
        return service

    def test_sucesso_retorna_response(self) -> None:
        """Quando exchange.place_market_entry sucede, retorna a resposta."""
        from core.model2.live_service import Model2LiveExecutionService as LiveExecutionService

        service = self._make_service()
        assert isinstance(service, LiveExecutionService)
        service.exchange.place_market_entry.return_value = {"orderId": 123}  # type: ignore[attr-defined]

        result = service._place_market_entry_with_retry(  # type: ignore[attr-defined]
            exchange=service.exchange,  # type: ignore[attr-defined]
            symbol="BTCUSDT",
            signal_side="SHORT",
            quantity=0.001,
        )
        assert result == {"orderId": 123}

    def test_transient_faz_retry(self) -> None:
        """Falha transitória deve acionar retry."""
        from core.model2.live_service import Model2LiveExecutionService as LiveExecutionService

        service = self._make_service()
        assert isinstance(service, LiveExecutionService)
        service.exchange.place_market_entry.side_effect = [  # type: ignore[attr-defined]
            ConnectionError("timeout"),
            {"orderId": 456},
        ]

        result = service._place_market_entry_with_retry(  # type: ignore[attr-defined]
            exchange=service.exchange,  # type: ignore[attr-defined]
            symbol="BTCUSDT",
            signal_side="SHORT",
            quantity=0.001,
            backoff=(0.0, 0.0),
        )
        assert result == {"orderId": 456}

    def test_budget_esgotado_retorna_none(self) -> None:
        """Após budget esgotado, retorna None (fail-safe, não propaga)."""
        from core.model2.live_service import Model2LiveExecutionService as LiveExecutionService

        service = self._make_service()
        assert isinstance(service, LiveExecutionService)
        service.exchange.place_market_entry.side_effect = ConnectionError("always fails")  # type: ignore[attr-defined]

        result = service._place_market_entry_with_retry(  # type: ignore[attr-defined]
            exchange=service.exchange,  # type: ignore[attr-defined]
            symbol="BTCUSDT",
            signal_side="SHORT",
            quantity=0.001,
            backoff=(0.0, 0.0, 0.0),
        )
        assert result is None

    def test_budget_esgotado_loga_timeout(self) -> None:
        """Após budget esgotado, deve logar warning via logging module."""
        import logging
        from core.model2.live_service import Model2LiveExecutionService as LiveExecutionService

        service = self._make_service()
        assert isinstance(service, LiveExecutionService)
        service.exchange.place_market_entry.side_effect = ConnectionError("always fails")  # type: ignore[attr-defined]

        mock_log = MagicMock()
        with patch("core.model2.live_service.logging") as mock_logging:
            mock_logging.getLogger.return_value = mock_log
            service._place_market_entry_with_retry(  # type: ignore[attr-defined]
                exchange=service.exchange,  # type: ignore[attr-defined]
                symbol="BTCUSDT",
                signal_side="SHORT",
                quantity=0.001,
                backoff=(0.0, 0.0, 0.0),
            )
        assert mock_log.warning.called
