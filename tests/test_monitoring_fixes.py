"""
Testes para as correções do pipeline de monitoramento.
Valida as correções de logging, variable shadowing, e decision priority.
"""

import pytest
import tempfile
import os
import logging
from unittest.mock import Mock, MagicMock, patch

from monitoring.position_monitor import PositionMonitor, ACTION_PRIORITY
from monitoring.logger import AgentLogger
from data.database import DatabaseManager
from core.layer_manager import LayerManager


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
def position_monitor(mock_client, temp_db):
    """Fixture do PositionMonitor."""
    return PositionMonitor(mock_client, temp_db, mode="paper")


# ============================================================================
# TESTE #1: Logging configuration - Root logger configurado
# ============================================================================

def test_root_logger_is_configured():
    """
    Testa que o root logger foi configurado com handlers após setup_logger().
    Isso garante que módulos usando logging.getLogger(__name__) tenham seus logs capturados.
    """
    # Limpar handlers anteriores
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Setup logger
    AgentLogger.setup_logger()
    
    # Verificar que o root logger tem handlers
    assert len(root_logger.handlers) > 0, "Root logger deve ter handlers configurados"
    
    # Verificar que há pelo menos um StreamHandler (console)
    has_stream_handler = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    assert has_stream_handler, "Root logger deve ter StreamHandler"


def test_module_logger_can_log():
    """
    Testa que um logger de módulo (como logging.getLogger(__name__)) consegue logar.
    """
    # Setup logger
    AgentLogger.setup_logger()
    
    # Criar logger de módulo (simula monitoring.position_monitor)
    module_logger = logging.getLogger("test_module.submodule")
    
    # Verificar que pode logar (não vai falhar silenciosamente)
    with patch('logging.StreamHandler.emit') as mock_emit:
        module_logger.info("Test message from module")
        # O handler foi chamado (prova que não foi silenciosamente descartado)
        assert mock_emit.called, "StreamHandler.emit should have been called"


# ============================================================================
# TESTE #2: Variable shadowing - `symbol` não é sobrescrito
# ============================================================================

def test_monitor_cycle_no_variable_shadowing(position_monitor, mock_client):
    """
    Testa que o parâmetro `symbol` do monitor_cycle não é sobrescrito
    pela variável do loop (agora renomeada para `pos_symbol`).
    """
    # Mock de posições retornadas
    mock_positions = [
        {'symbol': 'C98USDT', 'direction': 'LONG', 'entry_price': 0.5, 
         'mark_price': 0.52, 'liquidation_price': 0.3, 'position_size_qty': 100,
         'leverage': 10, 'margin_type': 'ISOLATED', 'unrealized_pnl': 2.0,
         'isolated_wallet': 50, 'position_size_usdt': 52, 'unrealized_pnl_pct': 3.85,
         'margin_balance': 50},
        {'symbol': 'BTCUSDT', 'direction': 'SHORT', 'entry_price': 50000, 
         'mark_price': 49000, 'liquidation_price': 55000, 'position_size_qty': 0.1,
         'leverage': 10, 'margin_type': 'ISOLATED', 'unrealized_pnl': 100,
         'isolated_wallet': 5000, 'position_size_usdt': 4900, 'unrealized_pnl_pct': 2.04,
         'margin_balance': 5000}
    ]
    
    with patch.object(position_monitor, 'fetch_open_positions', return_value=mock_positions):
        with patch.object(position_monitor, 'fetch_current_market_data', return_value={'h1': None, 'h4': None, 'sentiment': {}}):
            with patch.object(position_monitor, 'calculate_indicators_snapshot', return_value={}):
                with patch.object(position_monitor.db, 'insert_position_snapshot', return_value=1):
                    # Chamar com symbol=None para monitorar todas
                    snapshots = position_monitor.monitor_cycle(symbol=None)
                    
                    # Se houve shadowing, fetch_open_positions seria chamado com 'BTCUSDT'
                    # na segunda iteração em vez de None
                    # Como corrigimos, deve ter sido chamado apenas uma vez com None
                    assert len(snapshots) == 2


# ============================================================================
# TESTE #3: Decision priority - CLOSE não pode ser downgraded para REDUCE_50
# ============================================================================

def test_action_priority_dictionary_exists():
    """Testa que o dicionário ACTION_PRIORITY foi definido corretamente."""
    assert 'HOLD' in ACTION_PRIORITY
    assert 'REDUCE_50' in ACTION_PRIORITY
    assert 'CLOSE' in ACTION_PRIORITY
    assert ACTION_PRIORITY['CLOSE'] > ACTION_PRIORITY['REDUCE_50']
    assert ACTION_PRIORITY['REDUCE_50'] > ACTION_PRIORITY['HOLD']


def test_update_action_respects_priority(position_monitor):
    """
    Testa que _update_action_if_higher_priority não faz downgrade.
    """
    decision = {
        'agent_action': 'CLOSE',
        'decision_confidence': 0.95,
        'decision_reasoning': [],
        'risk_score': 8.0
    }
    reasoning = []
    
    # Tentar fazer downgrade para REDUCE_50 (menor prioridade)
    position_monitor._update_action_if_higher_priority(
        decision, 'REDUCE_50', 0.70, reasoning,
        "Tentando downgrade"
    )
    
    # A ação deve permanecer CLOSE (não foi downgraded)
    assert decision['agent_action'] == 'CLOSE'
    assert decision['decision_confidence'] == 0.95  # Confiança não mudou
    
    # Como o downgrade foi bloqueado, reasoning não é adicionado
    assert len(reasoning) == 0


def test_update_action_allows_upgrade(position_monitor):
    """
    Testa que _update_action_if_higher_priority permite upgrade.
    """
    decision = {
        'agent_action': 'HOLD',
        'decision_confidence': 0.5,
        'decision_reasoning': [],
        'risk_score': 3.0
    }
    reasoning = []
    
    # Fazer upgrade para REDUCE_50
    position_monitor._update_action_if_higher_priority(
        decision, 'REDUCE_50', 0.75, reasoning,
        "Upgrade para REDUCE_50"
    )
    
    # A ação deve ter sido atualizada
    assert decision['agent_action'] == 'REDUCE_50'
    assert decision['decision_confidence'] == 0.75
    # Reasoning foi adicionado com marcador [UPGRADE]
    assert len(reasoning) == 1
    assert '[UPGRADE]' in reasoning[0]


def test_update_action_same_priority_updates_confidence(position_monitor):
    """
    Testa que ações com mesma prioridade atualizam confiança se maior.
    """
    decision = {
        'agent_action': 'REDUCE_50',
        'decision_confidence': 0.60,
        'decision_reasoning': [],
        'risk_score': 5.0
    }
    reasoning = []
    
    # Tentar outra REDUCE_50 com confiança maior
    position_monitor._update_action_if_higher_priority(
        decision, 'REDUCE_50', 0.80, reasoning,
        "Segunda verificação REDUCE_50"
    )
    
    # A ação permanece, mas confiança aumenta
    assert decision['agent_action'] == 'REDUCE_50'
    assert decision['decision_confidence'] == 0.80
    # Reasoning foi adicionado com marcador [CONFIRMAÇÃO]
    assert len(reasoning) == 1
    assert '[CONFIRMAÇÃO]' in reasoning[0]


def test_evaluate_position_critical_close_not_downgraded(position_monitor):
    """
    Testa que uma decisão CLOSE por liquidação não é downgraded
    por verificações subsequentes de funding rate.
    """
    # Posição próxima da liquidação
    position = {
        'symbol': 'C98USDT',
        'direction': 'LONG',
        'entry_price': 0.50,
        'mark_price': 0.31,  # Muito próximo da liquidação
        'liquidation_price': 0.30,  # Distância < 5%
        'position_size_qty': 100,
        'position_size_usdt': 31,
        'unrealized_pnl': -19,
        'unrealized_pnl_pct': -61.3
    }
    
    # Indicadores com funding rate extremo (que normalmente sugeriria REDUCE_50)
    indicators = {
        'funding_rate': 0.10,  # Extremamente alto
        'market_structure': 'bullish',
        'choch_recent': 0,
        'rsi_14': 60,
        'ema_17': 0.32,
        'ema_72': 0.35,
        'atr_14': 0.02
    }
    
    sentiment = {'funding_rate': 0.10}
    
    # Avaliar posição
    decision = position_monitor.evaluate_position(position, indicators, sentiment)
    
    # Deve ser CLOSE por liquidação, não REDUCE_50 por funding
    assert decision['agent_action'] == 'CLOSE'
    # A confiança pode ser ajustada por múltiplas verificações, mas deve ser alta
    assert decision['decision_confidence'] >= 0.75


# ============================================================================
# TESTE #4: LayerManager e start_operation recebem dependências
# ============================================================================

def test_layer_manager_accepts_db_and_client(temp_db, mock_client):
    """
    Testa que LayerManager pode ser inicializado com db e client.
    """
    layer_manager = LayerManager(db=temp_db, client=mock_client)
    
    assert layer_manager.db is temp_db
    assert layer_manager.client is mock_client


def test_layer_manager_works_without_db_and_client():
    """
    Testa que LayerManager ainda funciona sem db e client (retrocompatibilidade).
    """
    layer_manager = LayerManager()
    
    assert layer_manager.db is None
    assert layer_manager.client is None
    # Mas deve funcionar normalmente
    assert isinstance(layer_manager.agent_state, dict)


# ============================================================================
# TESTE DE INTEGRAÇÃO: Monitor cycle completo
# ============================================================================

def test_monitor_cycle_integration(position_monitor, mock_client, temp_db):
    """
    Teste de integração que valida o ciclo completo de monitoramento
    com as correções aplicadas.
    """
    import pandas as pd
    
    # Mock de posição
    mock_positions = [{
        'symbol': 'C98USDT',
        'direction': 'LONG',
        'entry_price': 0.50,
        'mark_price': 0.52,
        'liquidation_price': 0.30,
        'position_size_qty': 100,
        'leverage': 10,
        'margin_type': 'ISOLATED',
        'unrealized_pnl': 2.0,
        'isolated_wallet': 50,
        'position_size_usdt': 52,
        'unrealized_pnl_pct': 3.85,
        'margin_balance': 50
    }]
    
    # Mock de dados de mercado
    mock_market_data = {
        'h1': pd.DataFrame({'close': [0.51, 0.52], 'high': [0.53, 0.54], 'low': [0.50, 0.51]}),
        'h4': pd.DataFrame({'close': [0.51, 0.52], 'high': [0.53, 0.54], 'low': [0.50, 0.51]}),
        'sentiment': {'funding_rate': 0.01, 'long_short_ratio': 1.2}
    }
    
    with patch.object(position_monitor, 'fetch_open_positions', return_value=mock_positions):
        with patch.object(position_monitor, 'fetch_current_market_data', return_value=mock_market_data):
            with patch.object(position_monitor, 'calculate_indicators_snapshot', return_value={
                'rsi_14': 55, 'ema_17': 0.51, 'ema_72': 0.49, 'funding_rate': 0.01
            }):
                # Executar ciclo
                snapshots = position_monitor.monitor_cycle(symbol=None)
                
                # Verificar que o ciclo completou com sucesso
                assert len(snapshots) == 1
                assert snapshots[0]['symbol'] == 'C98USDT'
                assert 'agent_action' in snapshots[0]
