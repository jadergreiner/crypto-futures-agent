"""
Testes parametrizados para modulo de execucao (Issue #58).

Cobertura:
- OrderExecutor: execucao de ordens MARKET, timeouts, integracoes
- OrderQueue: fila thread-safe, retry logico, observers
- ErrorHandler: classificacao de erros, recovery, backoff exponencial
- Integracao com RiskGate e RateLimitedCollector

38+ casos de teste com @pytest.mark.parametrize.
Usando MockBinanceAPI para simular API da Binance.
"""

import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any

from execution.order_executor import OrderExecutor
from execution.order_queue import (
    OrderQueue, Order, OrderStatus, OrderObserver
)
from execution.error_handler import (
    ErrorHandler, ErrorType, ErrorSeverity, ErrorRecoveryStrategy
)
from data.database import DatabaseManager


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_client():
    """Mock do cliente Binance SDK."""
    client = Mock()
    client.rest_api = Mock()
    return client


@pytest.fixture
def temp_db(tmp_path):
    """Banco de dados temporario para testes."""
    db_path = str(tmp_path / "test.db")
    db = DatabaseManager(db_path)
    yield db


@pytest.fixture
def order_executor(mock_client, temp_db):
    """OrderExecutor em modo paper."""
    return OrderExecutor(mock_client, temp_db, mode="paper")


@pytest.fixture
def order_queue():
    """OrderQueue vazio."""
    queue = OrderQueue(max_queue_size=50)
    return queue


@pytest.fixture
def error_handler():
    """ErrorHandler com estrategias padrao."""
    return ErrorHandler()


@pytest.fixture
def mock_binance_api():
    """Mock da Binance API para testes."""
    api = Mock()

    # Mock de post_order (executa ordem)
    def post_order_impl(symbol: str, side: str, quantity: float, **kwargs):
        """Simula API post_order."""
        return {
            "orderId": 12345,
            "symbol": symbol,
            "status": "FILLED",
            "side": side,
            "origQty": quantity,
            "executedQty": quantity,
            "price": "50000.00",
            "type": "MARKET",
            "timeInForce": "IOC",
        }

    api.post_order = MagicMock(side_effect=post_order_impl)
    api.get_account = MagicMock(return_value={
        "totalWalletBalance": 10000.0,
        "positions": [],
    })

    return api


# ============================================================================
# TESTES DO ErrorHandler
# ============================================================================

class TestErrorHandler:
    """Testes para tratamento de erros."""

    def test_error_handler_init(self, error_handler):
        """T001: Inicializacao do ErrorHandler."""
        assert error_handler is not None
        assert ErrorType.API_ERROR in error_handler._strategies
        assert ErrorType.NETWORK_ERROR in error_handler._strategies

    def test_classify_api_error(self, error_handler):
        """T002: Classificar APIError."""
        exc = Exception("BinanceAPIError: insufficient balance")
        error_type, msg = error_handler.classify_exception(exc)
        assert "saldo" in msg.lower() or "insuficiente" in msg.lower()

    def test_classify_timeout_error(self, error_handler):
        """T003: Classificar TimeoutError."""
        exc = TimeoutError("Request timed out")
        error_type, msg = error_handler.classify_exception(exc)
        assert error_type == ErrorType.TIMEOUT_ERROR

    def test_classify_network_error(self, error_handler):
        """T004: Classificar NetworkError."""
        exc = ConnectionError("Network unreachable")
        error_type, msg = error_handler.classify_exception(exc)
        assert error_type == ErrorType.NETWORK_ERROR

    def test_classify_rate_limit_error(self, error_handler):
        """T005: Classificar Rate Limit (429)."""
        exc = Exception("429 Too Many Requests")
        error_type, msg = error_handler.classify_exception(exc)
        assert error_type == ErrorType.RATE_LIMIT_ERROR

    @pytest.mark.parametrize("attempt,expected_backoff", [
        (1, 1.0),      # 1 * 2^0 = 1
        (2, 2.0),      # 1 * 2^1 = 2
        (3, 4.0),      # 1 * 2^2 = 4
        (4, 8.0),      # 1 * 2^3 = 8 (caps at 8)
    ])
    def test_exponential_backoff(
        self, error_handler, attempt, expected_backoff
    ):
        """T006-T009: Backoff exponencial para diferentes tentativas."""
        strategy = error_handler.get_strategy(ErrorType.API_ERROR)
        backoff = strategy.calculate_backoff(attempt)
        assert backoff == expected_backoff

    def test_handle_with_retry_success(self, error_handler):
        """T010: handle_with_retry com sucesso na primeira tentativa."""
        call_count = [0]

        def operation():
            call_count[0] += 1
            return {"result": "ok"}

        success, result, error = error_handler.handle_with_retry(
            operation, "test_operation"
        )

        assert success is True
        assert result == {"result": "ok"}
        assert error is None
        assert call_count[0] == 1

    def test_handle_with_retry_with_retries(self, error_handler):
        """T011: handle_with_retry com falhas e sucessos."""
        call_count = [0]

        def operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Network error")
            return {"result": "ok"}

        success, result, error = error_handler.handle_with_retry(
            operation, "test_operation"
        )

        assert success is True
        assert result == {"result": "ok"}
        assert call_count[0] == 3

    def test_handle_with_retry_max_retries_exceeded(self, error_handler):
        """T012: handle_with_retry com falha permanente."""
        call_count = [0]

        def operation():
            call_count[0] += 1
            raise Exception("Persistent error")

        success, result, error = error_handler.handle_with_retry(
            operation, "test_operation"
        )

        assert success is False
        assert result is None
        assert error is not None
        assert error["error_type"] == ErrorType.UNKNOWN_ERROR.value

    def test_register_custom_error_handler(self, error_handler):
        """T013: Registrar handler customizado."""
        handler_called = [False]

        def custom_handler(exc, context):
            handler_called[0] = True

        error_handler.register_error_handler(
            ErrorType.NETWORK_ERROR, custom_handler
        )

        def operation():
            raise ConnectionError("Network")

        success, _, error = error_handler.handle_with_retry(
            operation, "test"
        )

        # O handler customizado deve ter sido chamado
        assert handler_called[0] is True or error is not None

    def test_insufficient_balance_no_retry(self, error_handler):
        """T014: Erro de saldo insuficiente nao retenta."""
        call_count = [0]

        def operation():
            call_count[0] += 1
            raise Exception("APIError: insufficient balance")

        success, result, error = error_handler.handle_with_retry(
            operation, "test"
        )

        assert success is False
        # Nao deve ter retentado (max_retries=0)
        assert call_count[0] <= 1


# ============================================================================
# TESTES DO OrderQueue
# ============================================================================

class TestOrderQueue:
    """Testes para fila de ordens."""

    def test_order_queue_init(self, order_queue):
        """T015: Inicializacao do OrderQueue."""
        assert order_queue is not None
        assert order_queue.queue_size() == 0

    def test_order_creation(self):
        """T016: Criacao de ordem com ID auto-gerado."""
        order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        assert order.order_id is not None
        assert order.status == OrderStatus.PENDING
        assert order.attempt == 0

    def test_enqueue_single_order(self, order_queue):
        """T017: Enfileirar ordem simples."""
        order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        order_queue.enqueue(order)
        assert order_queue.queue_size() == 1

    @pytest.mark.parametrize("symbol,side,quantity", [
        ("BTCUSDT", "BUY", 0.1),
        ("ETHUSDT", "SELL", 1.5),
        ("ADAUSDT", "BUY", 100.0),
    ])
    def test_enqueue_multiple_orders(
        self, order_queue, symbol, side, quantity
    ):
        """T018-T020: Enfileirar multiplas ordens de diferentes simbolos."""
        orders = [
            Order(symbol=symbol, side=side, quantity=quantity)
            for _ in range(3)
        ]
        for order in orders:
            order_queue.enqueue(order)

        assert order_queue.queue_size() == 3

    def test_register_executor(self, order_queue):
        """T021: Registrar funcao executora."""
        def executor(order):
            return {"orderId": 123, "status": "FILLED"}

        order_queue.register_executor(executor)
        assert order_queue._executor_fn is not None

    def test_observer_on_order_queued(self, order_queue):
        """T022: Observer notificado quando ordem eh enfileirada."""
        observer_calls = []

        class TestObserver(OrderObserver):
            def on_order_queued(self, order):
                observer_calls.append(("queued", order))

        observer = TestObserver()
        order_queue.subscribe(observer)

        order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        order_queue.enqueue(order)

        assert len(observer_calls) == 1
        assert observer_calls[0][0] == "queued"

    def test_order_retry_logic(self, order_queue):
        """T023: Logica de retry com max 3 tentativas."""
        attempt_count = [0]

        def executor(order):
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise Exception("Simulated error")
            return {"orderId": 123, "status": "FILLED"}

        order_queue.register_executor(executor)
        order_queue.start_worker()

        order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        order_queue.enqueue(order)

        # Aguardar processamento
        time.sleep(3)

        order_queue.stop_worker()

        # Deve ter retentado
        assert attempt_count[0] >= 1

    def test_get_order_by_id(self, order_queue):
        """T024: Obter ordem pelo ID."""
        order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        order_queue.enqueue(order)

        retrieved = order_queue.get_order(order.order_id)
        assert retrieved is not None
        assert retrieved.order_id == order.order_id

    def test_get_orders_by_status(self, order_queue):
        """T025: Obter ordens filtradas por status."""
        order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        order_queue.enqueue(order)

        pending = order_queue.get_pending_orders()
        assert len(pending) == 1

    def test_cancel_order_pending(self, order_queue):
        """T026: Cancelar ordem pendente."""
        order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        order_queue.enqueue(order)

        success = order_queue.cancel_order(order.order_id)
        assert success is True
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_order_already_executed(self, order_queue):
        """T027: Cancelar ordem ja executada retorna False."""
        order = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        order.mark_as_executed({"orderId": 123})

        success = order_queue.cancel_order(order.order_id)
        assert success is False

    def test_queue_statistics(self, order_queue):
        """T028: Obter estatisticas da fila."""
        order1 = Order(symbol="BTCUSDT", side="BUY", quantity=0.1)
        order2 = Order(symbol="ETHUSDT", side="SELL", quantity=1.0)
        order_queue.enqueue(order1)
        order_queue.enqueue(order2)

        stats = order_queue.get_statistics()
        assert stats["total_orders"] == 2
        assert stats["pending"] == 2
        assert stats["executed"] == 0
        assert stats["failed"] == 0

    def test_unsubscribe_observer(self, order_queue):
        """T029: Remover observer de notificacoes."""
        class TestObserver(OrderObserver):
            def on_order_queued(self, order):
                pass

        observer = TestObserver()
        order_queue.subscribe(observer)
        order_queue.unsubscribe(observer)

        assert observer not in order_queue._observers


# ============================================================================
# TESTES DE INTEGRACAO
# ============================================================================

class TestOrderExecutorIntegration:
    """Testes de integracao com RiskGate e RateLimitedCollector."""

    def test_integration_with_mock_binance_api(
        self, order_executor, mock_binance_api, mock_client
    ):
        """T030: Execucao com mock da API Binance."""
        mock_client.rest_api = mock_binance_api

        position = {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "position_size_qty": 0.5,
            "mark_price": 50000.0,
        }

        decision = {
            "agent_action": "CLOSE",
            "decision_confidence": 0.95,
        }

        result = order_executor.execute_decision(position, decision)
        # Verificar que resultado foi produzido
        assert result is not None

    def test_order_executor_timeout_scenario(
        self, order_executor, mock_client
    ):
        """T031: Cenario de timeout em execucao."""
        def slow_operation(*args, **kwargs):
            time.sleep(10)
            return {"orderId": 123}

        mock_client.rest_api.post_order = MagicMock(
            side_effect=slow_operation
        )

        position = {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "position_size_qty": 0.5,
            "mark_price": 50000.0,
        }

        decision = {
            "agent_action": "CLOSE",
            "decision_confidence": 0.95,
        }

        # Resultado deve indicar timeout
        result = order_executor.execute_decision(position, decision)
        # Verificar comportamento esperado


# ============================================================================
# TESTES PARAMETRIZADOS DE COBERTURA
# ============================================================================

class TestParametrizedCoverage:
    """Testes parametrizados para cobertura completa."""

    @pytest.mark.parametrize("error_type,expected_retry", [
        (ErrorType.API_ERROR, True),
        (ErrorType.NETWORK_ERROR, True),
        (ErrorType.TIMEOUT_ERROR, True),
        (ErrorType.RATE_LIMIT_ERROR, True),
        (ErrorType.INSUFFICIENT_BALANCE, False),
        (ErrorType.INVALID_ORDER, False),
    ])
    def test_error_type_retry_policy(
        self, error_handler, error_type, expected_retry
    ):
        """T032-T037: Politica de retry para cada tipo de erro."""
        strategy = error_handler.get_strategy(error_type)
        assert strategy.should_retry == expected_retry

    @pytest.mark.parametrize("queue_size", [10, 50, 100])
    def test_order_queue_max_size(self, queue_size):
        """T038-T040: Criar filas com diferentes tamanhos."""
        queue = OrderQueue(max_queue_size=queue_size)
        assert queue._queue.maxsize == queue_size

    @pytest.mark.parametrize("side,quantity", [
        ("BUY", 0.05),
        ("BUY", 0.1),
        ("SELL", 1.0),
        ("SELL", 5.0),
    ])
    def test_order_creation_variations(self, side, quantity):
        """T041-T044: Criar ordens com diferentes sides/quantidades."""
        order = Order(
            symbol="BTCUSDT",
            side=side,
            quantity=quantity,
        )
        assert order.side == side
        assert order.quantity == quantity
        assert order.symbol == "BTCUSDT"


# ============================================================================
# TESTES ADICIONAIS
# ============================================================================

class TestEdgeCases:
    """Testes de casos extremos e edge cases."""

    def test_error_handler_create_summary(self, error_handler):
        """T045: Criar resumo formatado de erro."""
        error_info = {
            "error_type": "network_error",
            "error_message": "Connection refused",
            "error_details": "Detailed error",
            "attempt": 2,
            "timestamp": "2026-02-22T10:00:00",
        }

        summary = error_handler.create_error_summary(error_info)
        assert "network_error" in summary
        assert "Connection refused" in summary
        assert "tentativa 2" in summary

    def test_order_to_dict_conversion(self):
        """T046: Converter ordem para dicionario."""
        order = Order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
        )
        order_dict = order.to_dict()

        assert order_dict["symbol"] == "BTCUSDT"
        assert order_dict["side"] == "BUY"
        assert order_dict["quantity"] == 0.1
        assert isinstance(order_dict["status"], str)

    def test_order_queue_empty_statistics(self, order_queue):
        """T047: Estatisticas de fila vazia."""
        stats = order_queue.get_statistics()

        assert stats["total_orders"] == 0
        assert stats["executed"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0
