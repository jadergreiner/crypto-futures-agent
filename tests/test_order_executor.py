"""
Testes unitários para o OrderExecutor.
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

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


@pytest.fixture
def order_executor_live(mock_client, temp_db):
    """Fixture do OrderExecutor em modo live."""
    return OrderExecutor(mock_client, temp_db, mode="live")


@pytest.fixture
def sample_position_long():
    """Posição LONG de exemplo."""
    return {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'mark_price': 52000.0,
        'position_size_qty': 0.5,
        'leverage': 10,
        'margin_type': 'ISOLATED',
        'unrealized_pnl': 1000.0,
        'unrealized_pnl_pct': 20.0,
        'margin_balance': 5000.0,
    }


@pytest.fixture
def sample_position_short():
    """Posição SHORT de exemplo."""
    return {
        'symbol': 'ETHUSDT',
        'direction': 'SHORT',
        'entry_price': 3000.0,
        'mark_price': 2800.0,
        'position_size_qty': 2.0,
        'leverage': 5,
        'margin_type': 'ISOLATED',
        'unrealized_pnl': 400.0,
        'unrealized_pnl_pct': 10.0,
        'margin_balance': 4000.0,
    }


@pytest.fixture
def sample_decision_close():
    """Decisão de CLOSE com alta confiança."""
    return {
        'agent_action': 'CLOSE',
        'decision_confidence': 0.85,
        'decision_reasoning': 'Posição com bom lucro, proteção de ganhos',
        'risk_score': 3.5,
    }


@pytest.fixture
def sample_decision_reduce50():
    """Decisão de REDUCE_50 com alta confiança."""
    return {
        'agent_action': 'REDUCE_50',
        'decision_confidence': 0.75,
        'decision_reasoning': 'Reduzir exposição mas manter parte da posição',
        'risk_score': 5.0,
    }


@pytest.fixture
def sample_decision_hold():
    """Decisão de HOLD."""
    return {
        'agent_action': 'HOLD',
        'decision_confidence': 0.60,
        'decision_reasoning': 'Manter posição atual',
        'risk_score': 4.0,
    }


# ============================================================================
# Testes de Inicialização
# ============================================================================

def test_order_executor_initialization_paper(order_executor):
    """Testa inicialização do OrderExecutor em modo paper."""
    assert order_executor._mode == "paper"
    assert order_executor._client is not None
    assert order_executor._db is not None
    assert len(order_executor.authorized_symbols) > 0
    assert 'BTCUSDT' in order_executor.authorized_symbols


def test_order_executor_initialization_live(order_executor_live):
    """Testa inicialização do OrderExecutor em modo live."""
    assert order_executor_live._mode == "live"


# ============================================================================
# Testes de Cálculo de Parâmetros de Ordem
# ============================================================================

def test_order_params_close_long(order_executor, sample_position_long):
    """Testa cálculo de parâmetros para CLOSE em posição LONG."""
    params = order_executor._calculate_order_params(sample_position_long, "CLOSE")
    
    assert params['side'] == 'SELL'
    assert params['quantity'] == 0.5  # 100% da posição


def test_order_params_close_short(order_executor, sample_position_short):
    """Testa cálculo de parâmetros para CLOSE em posição SHORT."""
    params = order_executor._calculate_order_params(sample_position_short, "CLOSE")
    
    assert params['side'] == 'BUY'
    assert params['quantity'] == 2.0  # 100% da posição


def test_order_params_reduce50_long(order_executor, sample_position_long):
    """Testa cálculo de parâmetros para REDUCE_50 em posição LONG."""
    params = order_executor._calculate_order_params(sample_position_long, "REDUCE_50")
    
    assert params['side'] == 'SELL'
    assert params['quantity'] == 0.25  # 50% da posição


def test_order_params_reduce50_short(order_executor, sample_position_short):
    """Testa cálculo de parâmetros para REDUCE_50 em posição SHORT."""
    params = order_executor._calculate_order_params(sample_position_short, "REDUCE_50")
    
    assert params['side'] == 'BUY'
    assert params['quantity'] == 1.0  # 50% da posição


def test_order_params_unknown_action(order_executor, sample_position_long):
    """Testa que ação desconhecida gera erro."""
    with pytest.raises(ValueError, match="Ação desconhecida"):
        order_executor._calculate_order_params(sample_position_long, "OPEN_LONG")


def test_order_params_unknown_direction(order_executor):
    """Testa que direção desconhecida gera erro."""
    position = {
        'symbol': 'BTCUSDT',
        'direction': 'SIDEWAYS',  # Direção inválida
        'position_size_qty': 0.5,
    }
    
    with pytest.raises(ValueError, match="Direção de posição desconhecida"):
        order_executor._calculate_order_params(position, "CLOSE")


# ============================================================================
# Testes de Safety Guards
# ============================================================================

def test_safety_guard_allowed_action(order_executor):
    """Testa que apenas ações permitidas passam."""
    # CLOSE deve passar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'CLOSE', 0.80)
    assert passed is True
    
    # REDUCE_50 deve passar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'REDUCE_50', 0.80)
    assert passed is True
    
    # HOLD deve falhar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'HOLD', 0.80)
    assert passed is False
    assert 'não permitida' in reason
    
    # Ação desconhecida deve falhar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'OPEN_LONG', 0.80)
    assert passed is False
    assert 'não permitida' in reason


def test_safety_guard_authorized_symbol(order_executor):
    """Testa que apenas símbolos autorizados passam."""
    # BTCUSDT está na whitelist
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'CLOSE', 0.80)
    assert passed is True
    
    # RANDOMUSDT não está na whitelist
    passed, reason = order_executor._check_safety_guards('RANDOMUSDT', 'CLOSE', 0.80)
    assert passed is False
    assert 'whitelist' in reason.lower()


def test_safety_guard_confidence_threshold(order_executor):
    """Testa que apenas confiança >= 0.70 passa."""
    # 0.80 deve passar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'CLOSE', 0.80)
    assert passed is True
    
    # 0.70 exatamente deve passar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'CLOSE', 0.70)
    assert passed is True
    
    # 0.65 deve falhar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'CLOSE', 0.65)
    assert passed is False
    assert 'confiança' in reason.lower() or 'confidence' in reason.lower()


def test_safety_guard_daily_limit(order_executor, temp_db):
    """Testa que limite diário bloqueia execuções."""
    # Inserir 6 execuções (limite) no banco
    today_timestamp = int(datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0).timestamp() * 1000)
    
    for i in range(6):
        temp_db.insert_execution_log({
            'timestamp': today_timestamp + i * 1000,
            'symbol': f'TEST{i}USDT',
            'direction': 'LONG',
            'action': 'CLOSE',
            'side': 'SELL',
            'quantity': 1.0,
            'order_type': 'MARKET',
            'reduce_only': 1,
            'executed': 1,
            'mode': 'paper',
            'reason': 'Teste',
            'order_id': None,
            'fill_price': None,
            'fill_quantity': None,
            'commission': None,
            'entry_price': 100.0,
            'mark_price': 110.0,
            'unrealized_pnl': 10.0,
            'unrealized_pnl_pct': 10.0,
            'risk_score': 3.0,
            'decision_confidence': 0.80,
            'decision_reasoning': 'Teste',
            'snapshot_id': None,
        })
    
    # 7ª execução deve falhar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'CLOSE', 0.80)
    assert passed is False
    assert 'limite diário' in reason.lower() or 'daily' in reason.lower()


def test_safety_guard_cooldown(order_executor):
    """Testa que cooldown bloqueia execuções no mesmo símbolo."""
    # Primeira execução deve passar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'CLOSE', 0.80)
    assert passed is True
    
    # Simular execução (atualizar cooldown)
    order_executor._update_cooldown('BTCUSDT')
    
    # Segunda execução imediata deve falhar
    passed, reason = order_executor._check_safety_guards('BTCUSDT', 'CLOSE', 0.80)
    assert passed is False
    assert 'cooldown' in reason.lower()
    
    # Outro símbolo deve passar
    passed, reason = order_executor._check_safety_guards('ETHUSDT', 'CLOSE', 0.80)
    assert passed is True


def test_cooldown_expires(order_executor):
    """Testa que cooldown expira após o tempo configurado."""
    symbol = 'BTCUSDT'
    
    # Definir cooldown há 1000 segundos (mais que 900s de cooldown)
    order_executor._cooldown_tracker[symbol] = time.time() - 1000
    
    # Deve passar pois cooldown já expirou
    passed, reason = order_executor._check_safety_guards(symbol, 'CLOSE', 0.80)
    assert passed is True


# ============================================================================
# Testes de Execução
# ============================================================================

def test_execute_close_long_paper(order_executor, sample_position_long, sample_decision_close, mock_client):
    """Testa execução de CLOSE em posição LONG no modo paper."""
    # Mock da resposta do SDK
    mock_client.rest_api.new_order.return_value = {
        'orderId': '12345',
        'avgPrice': '52000.0',
        'executedQty': '0.5',
        'fills': [{'commission': '0.001'}]
    }
    
    result = order_executor.execute_decision(sample_position_long, sample_decision_close)
    
    assert result['executed'] is True
    assert result['action'] == 'CLOSE'
    assert result['symbol'] == 'BTCUSDT'
    assert result['side'] == 'SELL'
    assert result['quantity'] == 0.5
    assert result['mode'] == 'paper'
    
    # Verificar que a ordem foi enviada para a Binance (modo paper também envia ordens reais)
    mock_client.rest_api.new_order.assert_called_once()
    call_args = mock_client.rest_api.new_order.call_args
    assert call_args.kwargs['symbol'] == 'BTCUSDT'
    assert call_args.kwargs['side'] == 'SELL'
    assert call_args.kwargs['quantity'] == 0.5
    assert call_args.kwargs['reduce_only'] is True


def test_execute_close_short_generates_buy(order_executor, sample_position_short, sample_decision_close, mock_client):
    """Testa que CLOSE em posição SHORT gera ordem BUY."""
    mock_client.rest_api.new_order.return_value = {
        'orderId': '67890',
        'avgPrice': '2800.0',
        'executedQty': '2.0',
    }
    
    result = order_executor.execute_decision(sample_position_short, sample_decision_close)
    
    assert result['executed'] is True
    assert result['side'] == 'BUY'
    assert result['quantity'] == 2.0
    
    call_args = mock_client.rest_api.new_order.call_args
    assert call_args.kwargs['side'] == 'BUY'


def test_execute_reduce50_long(order_executor, sample_position_long, sample_decision_reduce50, mock_client):
    """Testa execução de REDUCE_50 em posição LONG."""
    mock_client.rest_api.new_order.return_value = {
        'orderId': '11111',
        'avgPrice': '52000.0',
        'executedQty': '0.25',
    }
    
    result = order_executor.execute_decision(sample_position_long, sample_decision_reduce50)
    
    assert result['executed'] is True
    assert result['action'] == 'REDUCE_50'
    assert result['side'] == 'SELL'
    assert result['quantity'] == 0.25  # 50% de 0.5


def test_execute_reduce50_short(order_executor, sample_position_short, sample_decision_reduce50, mock_client):
    """Testa execução de REDUCE_50 em posição SHORT."""
    mock_client.rest_api.new_order.return_value = {
        'orderId': '22222',
        'avgPrice': '2800.0',
        'executedQty': '1.0',
    }
    
    result = order_executor.execute_decision(sample_position_short, sample_decision_reduce50)
    
    assert result['executed'] is True
    assert result['action'] == 'REDUCE_50'
    assert result['side'] == 'BUY'
    assert result['quantity'] == 1.0  # 50% de 2.0


def test_hold_not_executed(order_executor, sample_position_long, sample_decision_hold):
    """Testa que ação HOLD não é executada."""
    result = order_executor.execute_decision(sample_position_long, sample_decision_hold)
    
    assert result['executed'] is False
    assert 'não permitida' in result['reason']


def test_unauthorized_symbol_blocked(order_executor, sample_decision_close):
    """Testa que símbolo não autorizado é bloqueado."""
    unauthorized_position = {
        'symbol': 'RANDOMUSDT',  # Não está na whitelist
        'direction': 'LONG',
        'position_size_qty': 1.0,
        'mark_price': 100.0,
        'entry_price': 90.0,
        'unrealized_pnl': 10.0,
        'unrealized_pnl_pct': 10.0,
    }
    
    result = order_executor.execute_decision(unauthorized_position, sample_decision_close)
    
    assert result['executed'] is False
    assert 'whitelist' in result['reason'].lower()


def test_low_confidence_blocked(order_executor, sample_position_long):
    """Testa que confiança baixa bloqueia execução."""
    low_confidence_decision = {
        'agent_action': 'CLOSE',
        'decision_confidence': 0.60,  # Abaixo de 0.70
        'decision_reasoning': 'Baixa confiança',
        'risk_score': 4.0,
    }
    
    result = order_executor.execute_decision(sample_position_long, low_confidence_decision)
    
    assert result['executed'] is False
    assert 'confiança' in result['reason'].lower() or 'confidence' in result['reason'].lower()


def test_reduce_only_always_true(order_executor, sample_position_long, sample_decision_close, mock_client):
    """Testa que reduceOnly é sempre True em todas as ordens."""
    mock_client.rest_api.new_order.return_value = {
        'orderId': '99999',
        'avgPrice': '52000.0',
        'executedQty': '0.5',
    }
    
    order_executor.execute_decision(sample_position_long, sample_decision_close)
    
    # Verificar que reduce_only=True foi passado
    call_args = mock_client.rest_api.new_order.call_args
    assert call_args.kwargs['reduce_only'] is True


def test_execution_persisted_to_db(order_executor, sample_position_long, sample_decision_close, temp_db, mock_client):
    """Testa que execução é persistida no banco de dados."""
    mock_client.rest_api.new_order.return_value = {
        'orderId': '12345',
        'avgPrice': '52000.0',
        'executedQty': '0.5',
    }
    
    order_executor.execute_decision(sample_position_long, sample_decision_close, snapshot_id=1)
    
    # Verificar que há um registro no execution_log
    executions = temp_db.get_execution_log()
    assert len(executions) == 1
    
    execution = executions[0]
    assert execution['symbol'] == 'BTCUSDT'
    assert execution['action'] == 'CLOSE'
    assert execution['executed'] == 1
    assert execution['reduce_only'] == 1
    assert execution['snapshot_id'] == 1


def test_retry_on_order_failure(order_executor, sample_position_long, sample_decision_close, mock_client):
    """Testa lógica de retry em caso de falha na ordem."""
    # Primeira e segunda tentativas falham, terceira sucede
    mock_client.rest_api.new_order.side_effect = [
        Exception("Erro temporário"),
        Exception("Erro temporário 2"),
        {
            'orderId': '12345',
            'avgPrice': '52000.0',
            'executedQty': '0.5',
        }
    ]
    
    result = order_executor.execute_decision(sample_position_long, sample_decision_close)
    
    # Deve ter sucesso após retries
    assert result['executed'] is True
    assert mock_client.rest_api.new_order.call_count == 3


def test_retry_exhausted(order_executor, sample_position_long, sample_decision_close, mock_client):
    """Testa que após esgotar retries, execução falha."""
    # Todas as tentativas falham
    mock_client.rest_api.new_order.side_effect = Exception("Erro persistente")
    
    result = order_executor.execute_decision(sample_position_long, sample_decision_close)
    
    assert result['executed'] is False
    # Verifica que o reason contém alguma indicação de falha
    assert 'falha' in result['reason'].lower() or 'erro' in result['reason'].lower()
    # max_order_retries = 2, então total de 3 tentativas (original + 2 retries)
    assert mock_client.rest_api.new_order.call_count == 3


def test_extract_data_with_api_response(order_executor):
    """Testa extração de dados de um objeto ApiResponse mockado."""
    mock_response = Mock()
    mock_response.data = {'orderId': '123', 'status': 'FILLED'}
    
    result = order_executor._extract_data(mock_response)
    assert result == {'orderId': '123', 'status': 'FILLED'}


def test_extract_data_with_callable(order_executor):
    """Testa extração quando .data é um método callable."""
    mock_response = Mock()
    mock_response.data = Mock(return_value={'orderId': '456', 'status': 'FILLED'})
    
    result = order_executor._extract_data(mock_response)
    assert result == {'orderId': '456', 'status': 'FILLED'}


def test_extract_data_direct(order_executor):
    """Testa extração de dados diretos (sem ApiResponse)."""
    direct_data = {'orderId': '789', 'status': 'FILLED'}
    
    result = order_executor._extract_data(direct_data)
    assert result == {'orderId': '789', 'status': 'FILLED'}


# ============================================================================
# Testes de Contadores e Rastreadores
# ============================================================================

def test_daily_counter_increments(order_executor, sample_position_long, sample_decision_close, mock_client):
    """Testa que contador diário é incrementado."""
    mock_client.rest_api.new_order.return_value = {
        'orderId': '123',
        'avgPrice': '52000.0',
        'executedQty': '0.5',
    }
    
    initial_count = order_executor._get_daily_execution_count()
    
    order_executor.execute_decision(sample_position_long, sample_decision_close)
    
    final_count = order_executor._get_daily_execution_count()
    assert final_count == initial_count + 1


def test_cooldown_tracker_updates(order_executor):
    """Testa que rastreador de cooldown é atualizado."""
    symbol = 'BTCUSDT'
    
    assert symbol not in order_executor._cooldown_tracker
    
    order_executor._update_cooldown(symbol)
    
    assert symbol in order_executor._cooldown_tracker
    assert order_executor._is_symbol_in_cooldown(symbol) is True


# ============================================================================
# Testes de Modo Live
# ============================================================================

def test_live_mode_calls_new_order(order_executor_live, sample_position_long, sample_decision_close, mock_client):
    """Testa que modo live chama new_order com parâmetros corretos."""
    mock_client.rest_api.new_order.return_value = {
        'orderId': '12345',
        'avgPrice': '52000.0',
        'executedQty': '0.5',
    }
    
    result = order_executor_live.execute_decision(sample_position_long, sample_decision_close)
    
    assert result['executed'] is True
    assert result['mode'] == 'live'
    
    # Verificar que new_order foi chamado
    mock_client.rest_api.new_order.assert_called_once()
    call_args = mock_client.rest_api.new_order.call_args
    
    # Verificar parâmetros críticos
    assert call_args.kwargs['symbol'] == 'BTCUSDT'
    assert call_args.kwargs['side'] == 'SELL'
    assert call_args.kwargs['type'] == 'MARKET'
    assert call_args.kwargs['quantity'] == 0.5
    assert call_args.kwargs['reduce_only'] is True
    assert call_args.kwargs['recv_window'] == 10000


# ============================================================================
# Testes de Integração com DatabaseManager
# ============================================================================

def test_database_count_executions_today(temp_db):
    """Testa contagem de execuções hoje no banco."""
    # Inserir execuções de hoje
    today_timestamp = int(datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0).timestamp() * 1000)
    
    for i in range(3):
        temp_db.insert_execution_log({
            'timestamp': today_timestamp + i * 1000,
            'symbol': f'TEST{i}USDT',
            'direction': 'LONG',
            'action': 'CLOSE',
            'side': 'SELL',
            'quantity': 1.0,
            'order_type': 'MARKET',
            'reduce_only': 1,
            'executed': 1,
            'mode': 'paper',
            'reason': 'Teste',
            'order_id': None,
            'fill_price': None,
            'fill_quantity': None,
            'commission': None,
            'entry_price': 100.0,
            'mark_price': 110.0,
            'unrealized_pnl': 10.0,
            'unrealized_pnl_pct': 10.0,
            'risk_score': 3.0,
            'decision_confidence': 0.80,
            'decision_reasoning': 'Teste',
            'snapshot_id': None,
        })
    
    # Inserir execução falhada (não deve contar)
    temp_db.insert_execution_log({
        'timestamp': today_timestamp,
        'symbol': 'FAILUSDT',
        'direction': 'LONG',
        'action': 'CLOSE',
        'side': 'SELL',
        'quantity': 1.0,
        'order_type': 'MARKET',
        'reduce_only': 1,
        'executed': 0,  # Falhou
        'mode': 'paper',
        'reason': 'Bloqueado',
        'order_id': None,
        'fill_price': None,
        'fill_quantity': None,
        'commission': None,
        'entry_price': 100.0,
        'mark_price': 110.0,
        'unrealized_pnl': 10.0,
        'unrealized_pnl_pct': 10.0,
        'risk_score': 3.0,
        'decision_confidence': 0.80,
        'decision_reasoning': 'Teste',
        'snapshot_id': None,
    })
    
    count = temp_db.count_executions_today()
    assert count == 3  # Apenas as 3 bem-sucedidas


def test_database_get_execution_log(temp_db):
    """Testa recuperação de logs de execução do banco."""
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    
    # Inserir algumas execuções
    temp_db.insert_execution_log({
        'timestamp': timestamp,
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'action': 'CLOSE',
        'side': 'SELL',
        'quantity': 0.5,
        'order_type': 'MARKET',
        'reduce_only': 1,
        'executed': 1,
        'mode': 'paper',
        'reason': 'Sucesso',
        'order_id': '123',
        'fill_price': 52000.0,
        'fill_quantity': 0.5,
        'commission': 0.001,
        'entry_price': 50000.0,
        'mark_price': 52000.0,
        'unrealized_pnl': 1000.0,
        'unrealized_pnl_pct': 20.0,
        'risk_score': 3.5,
        'decision_confidence': 0.85,
        'decision_reasoning': 'Proteção de lucro',
        'snapshot_id': 1,
    })
    
    # Buscar todos
    logs = temp_db.get_execution_log()
    assert len(logs) == 1
    assert logs[0]['symbol'] == 'BTCUSDT'
    
    # Buscar por símbolo
    logs = temp_db.get_execution_log(symbol='BTCUSDT')
    assert len(logs) == 1
    
    # Buscar símbolo inexistente
    logs = temp_db.get_execution_log(symbol='ETHUSDT')
    assert len(logs) == 0
    
    # Buscar apenas executadas
    logs = temp_db.get_execution_log(executed_only=True)
    assert len(logs) == 1


# ============================================================================
# Testes de Conversão de SDK Objects
# ============================================================================

def test_extract_data_converts_sdk_object_to_dict(order_executor):
    """Testa que _extract_data converte SDK objects em dicts."""
    # Mock de um objeto SDK (como NewOrderResponse) com atributos snake_case
    class MockNewOrderResponse:
        def __init__(self):
            self.order_id = 12345
            self.symbol = 'BTCUSDT'
            self.status = 'FILLED'
            self.avg_price = '52000.0'
            self.executed_qty = '0.5'
            self.orig_qty = '0.5'
            self._internal_field = 'should be filtered'  # Atributo privado
    
    sdk_object = MockNewOrderResponse()
    result = order_executor._extract_data(sdk_object)
    
    # Deve ser um dict
    assert isinstance(result, dict)
    
    # Deve conter os campos em snake_case originais
    assert result['order_id'] == 12345
    assert result['symbol'] == 'BTCUSDT'
    assert result['avg_price'] == '52000.0'
    assert result['executed_qty'] == '0.5'
    
    # Deve conter também as versões camelCase
    assert result['orderId'] == 12345
    assert result['avgPrice'] == '52000.0'
    assert result['executedQty'] == '0.5'
    
    # Não deve conter campos privados
    assert '_internal_field' not in result


def test_extract_data_with_api_response_wrapper(order_executor):
    """Testa _extract_data com ApiResponse wrapper contendo SDK object."""
    # Mock de SDK object
    class MockOrderResponse:
        def __init__(self):
            self.order_id = 67890
            self.avg_price = '51000.0'
            self.executed_qty = '1.0'
    
    # Mock de ApiResponse wrapper
    mock_api_response = Mock()
    mock_api_response.data = MockOrderResponse()
    
    result = order_executor._extract_data(mock_api_response)
    
    assert isinstance(result, dict)
    assert result['order_id'] == 67890
    assert result['orderId'] == 67890  # camelCase também presente
    assert result['avgPrice'] == '51000.0'


def test_extract_data_with_list_of_sdk_objects(order_executor):
    """Testa conversão de lista de SDK objects (como position_information_v2)."""
    # Mock de SDK objects em uma lista
    class MockPositionInfo:
        def __init__(self, symbol, position_amt):
            self.symbol = symbol
            self.position_amt = position_amt
            self.unrealized_profit = '100.0'
    
    position_list = [
        MockPositionInfo('BTCUSDT', '0.5'),
        MockPositionInfo('ETHUSDT', '2.0')
    ]
    
    result = order_executor._extract_data(position_list)
    
    # Deve ser uma lista de dicts
    assert isinstance(result, list)
    assert len(result) == 2
    
    # Cada elemento deve ser um dict
    assert isinstance(result[0], dict)
    assert result[0]['symbol'] == 'BTCUSDT'
    assert result[0]['position_amt'] == '0.5'
    
    assert isinstance(result[1], dict)
    assert result[1]['symbol'] == 'ETHUSDT'
    assert result[1]['position_amt'] == '2.0'


def test_execute_decision_with_sdk_object_response(order_executor, sample_position_long, sample_decision_close, mock_client):
    """
    Teste end-to-end: execute_decision com SDK object response.
    
    Simula o cenário real onde new_order() retorna um SDK object (não dict),
    e valida que execute_decision consegue extrair order_id, avgPrice, etc.
    """
    # Mock de SDK object como resposta
    class MockNewOrderResponse:
        def __init__(self):
            self.order_id = 999888
            self.symbol = 'BTCUSDT'
            self.status = 'FILLED'
            self.side = 'SELL'
            self.type = 'MARKET'
            self.avg_price = '52500.0'
            self.executed_qty = '0.5'
            self.orig_qty = '0.5'
            self.cum_qty = '0.5'
            self.cum_quote = '26250.0'
            self.reduce_only = True
    
    # Mock da API retorna SDK object (não dict)
    mock_response = Mock()
    mock_response.data = MockNewOrderResponse()
    mock_client.rest_api.new_order.return_value = mock_response
    
    # Executar decisão
    result = order_executor.execute_decision(sample_position_long, sample_decision_close)
    
    # Deve ter executado com sucesso
    assert result['executed'] is True
    assert result['action'] == 'CLOSE'
    assert result['symbol'] == 'BTCUSDT'
    
    # order_response deve ser um dict (convertido do SDK object)
    order_response = result['order_response']
    assert isinstance(order_response, dict)
    
    # Deve ter extraído os campos corretamente
    assert order_response['order_id'] == 999888
    assert order_response['orderId'] == 999888  # Ambas as versões
    assert order_response['avg_price'] == '52500.0'
    assert order_response['avgPrice'] == '52500.0'
    assert order_response['executed_qty'] == '0.5'
    assert order_response['executedQty'] == '0.5'


def test_convert_sdk_object_preserves_nested_structures(order_executor):
    """Testa que conversão preserva estruturas aninhadas."""
    class MockFill:
        def __init__(self, price, qty, commission):
            self.price = price
            self.qty = qty
            self.commission = commission
    
    class MockOrderWithFills:
        def __init__(self):
            self.order_id = 111
            self.fills = [
                MockFill('50000', '0.3', '0.001'),
                MockFill('50100', '0.2', '0.0008')
            ]
    
    sdk_object = MockOrderWithFills()
    result = order_executor._extract_data(sdk_object)
    
    assert isinstance(result, dict)
    assert result['order_id'] == 111
    
    # Fills deve ser uma lista de dicts
    assert isinstance(result['fills'], list)
    assert len(result['fills']) == 2
    assert isinstance(result['fills'][0], dict)
    assert result['fills'][0]['price'] == '50000'
    assert result['fills'][0]['commission'] == '0.001'


def test_map_to_camel_case_common_fields(order_executor):
    """Testa mapeamento explícito de campos comuns."""
    snake_dict = {
        'order_id': 123,
        'avg_price': '50000',
        'executed_qty': '1.0',
        'reduce_only': True,
        'stop_price': '49000',
        'update_time': 1234567890
    }
    
    result = order_executor._map_to_camel_case(snake_dict)
    
    # Deve manter snake_case original
    assert result['order_id'] == 123
    assert result['avg_price'] == '50000'
    
    # Deve adicionar camelCase
    assert result['orderId'] == 123
    assert result['avgPrice'] == '50000'
    assert result['executedQty'] == '1.0'
    assert result['reduceOnly'] is True
    assert result['stopPrice'] == '49000'
    assert result['updateTime'] == 1234567890


def test_integration_sdk_response_scenario_from_production(order_executor, mock_client, temp_db):
    """
    Teste de integração: Simula cenário de produção reportado no bug.
    
    Cenário:
    1. Posição 0GUSDT LONG com position_amt='2'
    2. Decisão de REDUCE_50 com confiança 0.75
    3. SDK retorna NewOrderResponse com atributos (não dict)
    4. Código deve extrair order_id, avgPrice, executedQty corretamente
    5. Execução deve ser marcada como executed=1 no banco
    """
    # 1. Posição problemática do 0GUSDT (relatada no bug)
    position_0g = {
        'symbol': '0GUSDT',
        'direction': 'LONG',
        'entry_price': 0.025,
        'mark_price': 0.030,
        'position_size_qty': 2.0,  # position_amt do log de produção
        'leverage': 5,
        'margin_type': 'ISOLATED',
        'unrealized_pnl': 10.0,
        'unrealized_pnl_pct': 20.0,
        'margin_balance': 0.15,
    }
    
    # 2. Decisão de REDUCE_50
    decision = {
        'agent_action': 'REDUCE_50',
        'decision_confidence': 0.75,
        'decision_reasoning': 'Reduzir exposição em símbolo high-beta',
        'risk_score': 4.5,
    }
    
    # 3. Mock da resposta como SDK object (cenário que causava o bug)
    class MockNewOrderResponse:
        """Simula NewOrderResponse real do SDK Binance."""
        def __init__(self):
            self.order_id = 987654321
            self.client_order_id = 'test_order_123'
            self.symbol = '0GUSDT'
            self.status = 'FILLED'
            self.side = 'SELL'
            self.type = 'MARKET'
            self.price = '0'  # MARKET orders têm price 0
            self.avg_price = '0.030'
            self.orig_qty = '1.0'
            self.executed_qty = '1.0'  # 50% de 2.0
            self.cum_qty = '1.0'
            self.cum_quote = '0.030'
            self.time_in_force = 'GTC'
            self.reduce_only = True
            self.close_position = False
            self.update_time = 1707995123456
            # Campo privado que deve ser filtrado
            self._internal_state = 'should_not_appear'
    
    # Mock do ApiResponse wrapper
    mock_api_response = Mock()
    mock_api_response.data = MockNewOrderResponse()
    mock_client.rest_api.new_order.return_value = mock_api_response
    
    # 4. Executar decisão
    result = order_executor.execute_decision(position_0g, decision, snapshot_id=999)
    
    # 5. Validações
    # Deve ter executado COM SUCESSO (o bug fazia falhar aqui)
    assert result['executed'] is True, f"Execução falhou: {result.get('reason')}"
    assert result['action'] == 'REDUCE_50'
    assert result['symbol'] == '0GUSDT'
    assert result['side'] == 'SELL'
    assert result['quantity'] == 1.0  # 50% de 2.0
    
    # order_response deve ser um dict (convertido do SDK object)
    order_response = result['order_response']
    assert isinstance(order_response, dict), "order_response deve ser dict, não SDK object"
    
    # Deve ter ambas as versões de cada campo (snake_case E camelCase)
    assert 'order_id' in order_response
    assert 'orderId' in order_response
    assert order_response['order_id'] == 987654321
    assert order_response['orderId'] == 987654321
    
    assert 'avg_price' in order_response
    assert 'avgPrice' in order_response
    assert order_response['avg_price'] == '0.030'
    assert order_response['avgPrice'] == '0.030'
    
    assert 'executed_qty' in order_response
    assert 'executedQty' in order_response
    assert order_response['executed_qty'] == '1.0'
    assert order_response['executedQty'] == '1.0'
    
    # Campos privados NÃO devem aparecer
    assert '_internal_state' not in order_response
    
    # Verificar que foi persistido corretamente no banco
    executions = temp_db.get_execution_log(symbol='0GUSDT')
    assert len(executions) == 1
    execution = executions[0]
    
    # CRÍTICO: executed deve ser 1 (o bug fazia ficar 0)
    assert execution['executed'] == 1, "Execução deve estar marcada como sucesso no banco"
    assert execution['order_id'] is not None, "order_id não deve ser null no banco"
    assert execution['snapshot_id'] == 999
    assert execution['symbol'] == '0GUSDT'
    assert execution['action'] == 'REDUCE_50'
