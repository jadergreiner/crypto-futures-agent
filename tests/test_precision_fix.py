"""
Testes para o fix de precision error do OrderExecutor.
"""

import pytest
import tempfile
import os
import math
from unittest.mock import Mock, NonCallableMock

from execution.order_executor import OrderExecutor
from data.database import DatabaseManager


@pytest.fixture
def mock_client():
    """Mock do cliente Binance SDK."""
    client = Mock()
    client.rest_api = Mock()
    return client


@pytest.fixture
def temp_db():
    """Banco de dados temporário para testes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        yield db


@pytest.fixture
def order_executor(mock_client, temp_db):
    """Fixture do OrderExecutor em modo paper."""
    return OrderExecutor(mock_client, temp_db, mode="paper")


def test_get_quantity_precision_from_api(order_executor, mock_client):
    """Testa busca de quantity precision da API."""
    # Mock da resposta da exchange_information - cada item deve ser um objeto com atributos
    mock_btc = Mock()
    mock_btc.symbol = 'BTCUSDT'
    mock_btc.quantity_precision = 3
    
    mock_kaia = Mock()
    mock_kaia.symbol = 'KAIAUSDT'
    mock_kaia.quantity_precision = 0
    
    mock_eth = Mock()
    mock_eth.symbol = 'ETHUSDT'
    mock_eth.quantity_precision = 3
    
    # Use NonCallableMock to avoid .data being callable
    mock_data = NonCallableMock()
    mock_data.symbols = [mock_btc, mock_kaia, mock_eth]
    
    mock_response = NonCallableMock()
    mock_response.data = mock_data
    
    mock_client.rest_api.exchange_information.return_value = mock_response
    
    # Primeira chamada busca da API
    precision = order_executor._get_quantity_precision('KAIAUSDT')
    assert precision == 0
    
    # Segunda chamada usa cache (não chama API novamente)
    mock_client.rest_api.exchange_information.reset_mock()
    precision = order_executor._get_quantity_precision('KAIAUSDT')
    assert precision == 0
    mock_client.rest_api.exchange_information.assert_not_called()


def test_get_quantity_precision_caching(order_executor, mock_client):
    """Testa que precision é cacheada corretamente."""
    # Mock da resposta - symbols deve ser uma lista
    mock_symbol_info = Mock()
    mock_symbol_info.symbol = 'BTCUSDT'
    mock_symbol_info.quantity_precision = 3
    
    mock_data = NonCallableMock()
    mock_data.symbols = [mock_symbol_info]
    
    mock_response = NonCallableMock()
    mock_response.data = mock_data
    
    mock_client.rest_api.exchange_information.return_value = mock_response
    
    # Primeira chamada
    precision1 = order_executor._get_quantity_precision('BTCUSDT')
    assert precision1 == 3
    assert mock_client.rest_api.exchange_information.call_count == 1
    
    # Segunda chamada usa cache
    precision2 = order_executor._get_quantity_precision('BTCUSDT')
    assert precision2 == 3
    assert mock_client.rest_api.exchange_information.call_count == 1  # Não chamou novamente


def test_get_quantity_precision_fallback_on_error(order_executor, mock_client):
    """Testa que fallback é usado em caso de erro na API."""
    mock_client.rest_api.exchange_information.side_effect = Exception("API Error")
    
    precision = order_executor._get_quantity_precision('BTCUSDT')
    assert precision == 8  # Fallback para 8 (padrão comum)


def test_get_quantity_precision_symbol_not_found(order_executor, mock_client):
    """Testa fallback quando símbolo não é encontrado na resposta."""
    mock_btc = Mock()
    mock_btc.symbol = 'BTCUSDT'
    mock_btc.quantity_precision = 3
    
    mock_data = NonCallableMock()
    mock_data.symbols = [mock_btc]
    
    mock_response = NonCallableMock()
    mock_response.data = mock_data
    
    mock_client.rest_api.exchange_information.return_value = mock_response
    
    # Buscar símbolo que não existe na resposta
    precision = order_executor._get_quantity_precision('UNKNOWNUSDT')
    assert precision == 8  # Fallback para 8


def test_calculate_order_params_with_precision_0(order_executor, mock_client):
    """Testa cálculo de quantidade com precision=0 (inteiros)."""
    # Mock precision=0 para KAIAUSDT
    mock_kaia = Mock()
    mock_kaia.symbol = 'KAIAUSDT'
    mock_kaia.quantity_precision = 0
    
    mock_data = NonCallableMock()
    mock_data.symbols = [mock_kaia]
    
    mock_response = NonCallableMock()
    mock_response.data = mock_data
    mock_client.rest_api.exchange_information.return_value = mock_response
    
    position = {
        'symbol': 'KAIAUSDT',
        'direction': 'LONG',
        'position_size_qty': 13.0,
    }
    
    # REDUCE_50 de 13.0 = 6.5, com precision=0 deve truncar para 6.0
    params = order_executor._calculate_order_params(position, 'REDUCE_50')
    
    assert params['side'] == 'SELL'
    assert params['quantity'] == 6.0  # Truncado, não arredondado para 7


def test_calculate_order_params_with_precision_3(order_executor, mock_client):
    """Testa cálculo de quantidade com precision=3."""
    # Mock precision=3 para BTCUSDT
    mock_btc = Mock()
    mock_btc.symbol = 'BTCUSDT'
    mock_btc.quantity_precision = 3
    
    mock_data = NonCallableMock()
    mock_data.symbols = [mock_btc]
    
    mock_response = NonCallableMock()
    mock_response.data = mock_data
    mock_client.rest_api.exchange_information.return_value = mock_response
    
    position = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'position_size_qty': 0.123456,
    }
    
    # CLOSE de 0.123456 com precision=3 deve truncar para 0.123
    params = order_executor._calculate_order_params(position, 'CLOSE')
    
    assert params['side'] == 'SELL'
    assert params['quantity'] == 0.123  # Truncado para 3 decimais


def test_quantity_truncation_math_floor(order_executor, mock_client):
    """Testa que truncamento usa math.floor, não round."""
    # Mock precision=0
    mock_test = Mock()
    mock_test.symbol = 'TESTUSDT'
    mock_test.quantity_precision = 0
    
    mock_data = NonCallableMock()
    mock_data.symbols = [mock_test]
    
    mock_response = NonCallableMock()
    mock_response.data = mock_data
    mock_client.rest_api.exchange_information.return_value = mock_response
    
    position = {
        'symbol': 'TESTUSDT',
        'direction': 'LONG',
        'position_size_qty': 10.0,
    }
    
    # REDUCE_50 de 10.0 = 5.0, exatamente
    params = order_executor._calculate_order_params(position, 'REDUCE_50')
    assert params['quantity'] == 5.0
    
    # Testar com valor que round() daria diferente
    position['position_size_qty'] = 15.0
    # REDUCE_50 de 15.0 = 7.5, com precision=0
    # math.floor(7.5) = 7, round(7.5) = 8
    params = order_executor._calculate_order_params(position, 'REDUCE_50')
    assert params['quantity'] == 7.0  # Deve ser 7, não 8


def test_quantity_precision_examples_from_issue(order_executor, mock_client):
    """Testa os exemplos específicos do bug report."""
    # Exemplo do bug: KAIAUSDT com 13 posição, REDUCE_50 = 6.5
    # Com precision=0 deve truncar para 6.0
    
    mock_kaia = Mock()
    mock_kaia.symbol = 'KAIAUSDT'
    mock_kaia.quantity_precision = 0
    
    mock_data = NonCallableMock()
    mock_data.symbols = [mock_kaia]
    
    mock_response = NonCallableMock()
    mock_response.data = mock_data
    mock_client.rest_api.exchange_information.return_value = mock_response
    
    position = {
        'symbol': 'KAIAUSDT',
        'direction': 'LONG',
        'position_size_qty': 13.0,
    }
    
    params = order_executor._calculate_order_params(position, 'REDUCE_50')
    
    # 13 * 0.5 = 6.5
    # math.floor(6.5 * 10^0) / 10^0 = math.floor(6.5) / 1 = 6.0
    assert params['quantity'] == 6.0
    assert params['side'] == 'SELL'
    
    # Verificar que não é 6.50000000 (o bug original)
    assert params['quantity'] != 6.5


def test_math_floor_truncation_logic():
    """Testa a lógica de truncamento com math.floor diretamente."""
    # Testar casos específicos
    
    # precision=0 (inteiros)
    assert math.floor(6.5 * 10**0) / 10**0 == 6.0
    assert math.floor(7.9 * 10**0) / 10**0 == 7.0
    assert math.floor(0.9 * 10**0) / 10**0 == 0.0
    
    # precision=3 (3 decimais)
    assert math.floor(0.123456 * 10**3) / 10**3 == 0.123
    assert math.floor(0.129999 * 10**3) / 10**3 == 0.129
    
    # precision=8 (8 decimais)
    assert math.floor(0.123456789 * 10**8) / 10**8 == 0.12345678


def test_no_emoji_in_logs(order_executor, mock_client):
    """Testa que não há emojis nos logs (fix do unicode error)."""
    import logging
    
    # Capturar logs
    captured_logs = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            captured_logs.append(self.format(record))
    
    handler = LogCapture()
    logger = logging.getLogger('execution.order_executor')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    try:
        # Mock ordem bem-sucedida
        mock_client.rest_api.new_order.return_value = {
            'orderId': '12345',
            'avgPrice': '50000.0',
            'executedQty': '1.0',
        }
        
        # Mock precision
        mock_btc = Mock()
        mock_btc.symbol = 'BTCUSDT'
        mock_btc.quantity_precision = 3
        
        mock_data = NonCallableMock()
        mock_data.symbols = [mock_btc]
        
        mock_response = NonCallableMock()
        mock_response.data = mock_data
        mock_client.rest_api.exchange_information.return_value = mock_response
        
        position = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'position_size_qty': 1.0,
            'mark_price': 50000.0,
            'entry_price': 48000.0,
            'unrealized_pnl': 2000.0,
            'unrealized_pnl_pct': 4.17,
        }
        
        decision = {
            'agent_action': 'CLOSE',
            'decision_confidence': 0.85,
            'decision_reasoning': 'Test',
            'risk_score': 3.0,
        }
        
        order_executor.execute_decision(position, decision)
        
        # Verificar que não há emojis nos logs
        log_text = '\n'.join(captured_logs)
        
        # Não deve conter emojis Unicode
        assert '✅' not in log_text
        assert '❌' not in log_text
        
        # Deve conter texto ASCII
        assert '[OK]' in log_text or 'OK' in log_text
        
    finally:
        logger.removeHandler(handler)
