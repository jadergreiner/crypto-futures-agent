"""
Testes unitários para o PositionMonitor.
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from monitoring.position_monitor import PositionMonitor
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
def position_monitor(mock_client, temp_db):
    """Fixture do PositionMonitor."""
    return PositionMonitor(mock_client, temp_db, mode="paper")


def test_position_monitor_initialization(position_monitor):
    """Testa inicialização do PositionMonitor."""
    assert position_monitor.mode == "paper"
    assert position_monitor._running == False
    assert position_monitor.collector is not None
    assert position_monitor.sentiment_collector is not None
    assert position_monitor.risk_manager is not None


def test_fetch_open_positions_empty(position_monitor, mock_client):
    """Testa fetch de posições quando não há posições abertas."""
    # Mock resposta da API sem posições abertas
    mock_client.rest_api.position_information.return_value = [
        {
            'symbol': 'BTCUSDT',
            'positionAmt': '0',
            'entryPrice': '0',
            'markPrice': '50000',
            'unRealizedProfit': '0',
            'liquidationPrice': '0',
            'leverage': '10',
            'marginType': 'ISOLATED',
            'isolatedWallet': '1000'
        }
    ]
    
    positions = position_monitor.fetch_open_positions()
    assert len(positions) == 0


def test_fetch_open_positions_long(position_monitor, mock_client):
    """Testa fetch de posição LONG."""
    # Mock resposta da API com posição LONG
    mock_client.rest_api.position_information.return_value = [
        {
            'symbol': 'C98USDT',
            'positionAmt': '100',  # Positivo = LONG
            'entryPrice': '0.5',
            'markPrice': '0.55',
            'unRealizedProfit': '5',
            'liquidationPrice': '0.35',
            'leverage': '10',
            'marginType': 'ISOLATED',
            'isolatedWallet': '100'
        }
    ]
    
    positions = position_monitor.fetch_open_positions('C98USDT')
    
    assert len(positions) == 1
    pos = positions[0]
    assert pos['symbol'] == 'C98USDT'
    assert pos['direction'] == 'LONG'
    assert pos['entry_price'] == 0.5
    assert pos['mark_price'] == 0.55
    assert pos['position_size_qty'] == 100
    assert pos['leverage'] == 10
    assert pos['unrealized_pnl'] == 5


def test_fetch_open_positions_short(position_monitor, mock_client):
    """Testa fetch de posição SHORT."""
    # Mock resposta da API com posição SHORT
    mock_client.rest_api.position_information.return_value = {
        'symbol': 'BTCUSDT',
        'positionAmt': '-0.5',  # Negativo = SHORT
        'entryPrice': '50000',
        'markPrice': '49000',
        'unRealizedProfit': '500',
        'liquidationPrice': '52000',
        'leverage': '5',
        'marginType': 'ISOLATED',
        'isolatedWallet': '10000'
    }
    
    positions = position_monitor.fetch_open_positions('BTCUSDT')
    
    assert len(positions) == 1
    pos = positions[0]
    assert pos['direction'] == 'SHORT'
    assert pos['position_size_qty'] == 0.5


def test_evaluate_position_close_on_big_loss(position_monitor):
    """Testa decisão de CLOSE quando loss é grande."""
    position = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 50000,
        'mark_price': 48000,
        'unrealized_pnl': -1000,
        'unrealized_pnl_pct': -4.0,  # Mais de 3%
        'liquidation_price': 45000,
        'position_size_usdt': 25000
    }
    
    indicators = {
        'rsi_14': 55,
        'market_structure': 'bullish'
    }
    
    sentiment = {}
    
    decision = position_monitor.evaluate_position(position, indicators, sentiment)
    
    assert decision['agent_action'] == 'CLOSE'
    assert decision['decision_confidence'] > 0.85
    # Verificar se o texto está presente (mesmo com encoding JSON)
    reasoning_text = json.loads(decision['decision_reasoning'])
    assert any('stop loss' in r.lower() for r in reasoning_text)


def test_evaluate_position_close_near_liquidation(position_monitor):
    """Testa decisão de CLOSE quando próximo da liquidação."""
    position = {
        'symbol': 'ETHUSDT',
        'direction': 'LONG',
        'entry_price': 3000,
        'mark_price': 2650,
        'unrealized_pnl': -500,
        'unrealized_pnl_pct': -2.0,
        'liquidation_price': 2600,  # Apenas 1.9% de distância
        'position_size_usdt': 25000
    }
    
    indicators = {}
    sentiment = {}
    
    decision = position_monitor.evaluate_position(position, indicators, sentiment)
    
    assert decision['agent_action'] == 'CLOSE'
    # Verificar se o texto está presente (mesmo com encoding JSON)
    reasoning_text = json.loads(decision['decision_reasoning'])
    assert any('liquida' in r.lower() for r in reasoning_text)


def test_evaluate_position_reduce_on_choch(position_monitor):
    """Testa decisão de REDUCE_50 quando CHoCH contra posição com lucro."""
    position = {
        'symbol': 'SOLUSDT',
        'direction': 'LONG',
        'entry_price': 100,
        'mark_price': 110,
        'unrealized_pnl': 500,
        'unrealized_pnl_pct': 10.0,
        'liquidation_price': 80,
        'position_size_usdt': 5000
    }
    
    indicators = {
        'market_structure': 'bearish',  # Contra LONG
        'choch_recent': 1,
        'rsi_14': 45
    }
    
    sentiment = {}
    
    decision = position_monitor.evaluate_position(position, indicators, sentiment)
    
    assert decision['agent_action'] == 'REDUCE_50'
    assert 'CHoCH' in decision['decision_reasoning']


def test_evaluate_position_hold_favorable(position_monitor):
    """Testa decisão de HOLD quando estrutura é favorável."""
    position = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 50000,
        'mark_price': 52000,
        'unrealized_pnl': 1000,
        'unrealized_pnl_pct': 4.0,
        'liquidation_price': 45000,
        'position_size_usdt': 25000
    }
    
    indicators = {
        'market_structure': 'bullish',
        'choch_recent': 0,
        'rsi_14': 60,
        'ema_17': 51000,
        'ema_72': 50000,
        'atr_14': 500
    }
    
    sentiment = {}
    
    decision = position_monitor.evaluate_position(position, indicators, sentiment)
    
    assert decision['agent_action'] == 'HOLD'
    assert decision['risk_score'] < 6.0


def test_evaluate_position_reduce_on_extreme_funding(position_monitor):
    """Testa decisão de REDUCE_50 em funding rate extremo."""
    position = {
        'symbol': 'DOGEUSDT',
        'direction': 'LONG',
        'entry_price': 0.1,
        'mark_price': 0.11,
        'unrealized_pnl': 50,
        'unrealized_pnl_pct': 10.0,
        'liquidation_price': 0.08,
        'position_size_usdt': 500
    }
    
    indicators = {
        'funding_rate': 0.06,  # Extremo para LONG (muitos LONGs)
        'rsi_14': 55
    }
    
    sentiment = {}
    
    decision = position_monitor.evaluate_position(position, indicators, sentiment)
    
    assert decision['agent_action'] == 'REDUCE_50'
    assert 'Funding rate extremo' in decision['decision_reasoning']


def test_create_snapshot(position_monitor):
    """Testa criação de snapshot completo."""
    position = {
        'symbol': 'C98USDT',
        'direction': 'LONG',
        'entry_price': 0.5,
        'mark_price': 0.55,
        'liquidation_price': 0.35,
        'position_size_qty': 100,
        'position_size_usdt': 55,
        'leverage': 10,
        'margin_type': 'ISOLATED',
        'unrealized_pnl': 5,
        'unrealized_pnl_pct': 10.0,
        'margin_balance': 100
    }
    
    indicators = {
        'rsi_14': 60,
        'ema_17': 0.54,
        'market_structure': 'bullish',
        'funding_rate': 0.01
    }
    
    sentiment = {}
    
    decision = {
        'agent_action': 'HOLD',
        'decision_confidence': 0.8,
        'decision_reasoning': json.dumps(['Tudo favorável']),
        'risk_score': 3.0,
        'stop_loss_suggested': 0.48,
        'take_profit_suggested': 0.62,
        'trailing_stop_price': None
    }
    
    snapshot = position_monitor.create_snapshot(position, indicators, sentiment, decision)
    
    # Verificar campos essenciais
    assert snapshot['symbol'] == 'C98USDT'
    assert snapshot['direction'] == 'LONG'
    assert snapshot['entry_price'] == 0.5
    assert snapshot['agent_action'] == 'HOLD'
    assert snapshot['risk_score'] == 3.0
    assert snapshot['rsi_14'] == 60
    assert snapshot['market_structure'] == 'bullish'
    assert snapshot['reward_calculated'] is None
    assert snapshot['outcome_label'] is None
    assert 'timestamp' in snapshot


def test_insert_and_retrieve_snapshot(position_monitor, temp_db):
    """Testa inserção e recuperação de snapshot do banco."""
    snapshot = {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'symbol': 'C98USDT',
        'direction': 'LONG',
        'entry_price': 0.5,
        'mark_price': 0.55,
        'liquidation_price': 0.35,
        'position_size_qty': 100,
        'position_size_usdt': 55,
        'leverage': 10,
        'margin_type': 'ISOLATED',
        'unrealized_pnl': 5,
        'unrealized_pnl_pct': 10.0,
        'margin_balance': 100,
        'rsi_14': 60,
        'ema_17': 0.54,
        'ema_34': 0.53,
        'ema_72': 0.52,
        'ema_144': 0.51,
        'macd_line': 0.01,
        'macd_signal': 0.005,
        'macd_histogram': 0.005,
        'bb_upper': 0.60,
        'bb_lower': 0.50,
        'bb_percent_b': 0.5,
        'atr_14': 0.02,
        'adx_14': 25,
        'di_plus': 20,
        'di_minus': 15,
        'market_structure': 'bullish',
        'bos_recent': 1,
        'choch_recent': 0,
        'nearest_ob_distance_pct': 2.0,
        'nearest_fvg_distance_pct': 3.0,
        'premium_discount_zone': 'premium',
        'liquidity_above_pct': 5.0,
        'liquidity_below_pct': 8.0,
        'funding_rate': 0.01,
        'long_short_ratio': 1.2,
        'open_interest_change_pct': 5.0,
        'agent_action': 'HOLD',
        'decision_confidence': 0.8,
        'decision_reasoning': json.dumps(['Tudo OK']),
        'risk_score': 3.0,
        'stop_loss_suggested': 0.48,
        'take_profit_suggested': 0.62,
        'trailing_stop_price': None,
        'reward_calculated': None,
        'outcome_label': None
    }
    
    # Inserir
    snapshot_id = temp_db.insert_position_snapshot(snapshot)
    assert snapshot_id > 0
    
    # Recuperar
    snapshots = temp_db.get_position_snapshots('C98USDT')
    assert len(snapshots) == 1
    
    retrieved = snapshots[0]
    assert retrieved['symbol'] == 'C98USDT'
    assert retrieved['agent_action'] == 'HOLD'
    assert retrieved['risk_score'] == 3.0


def test_update_snapshot_outcome(position_monitor, temp_db):
    """Testa atualização de outcome retroativo."""
    # Criar e inserir snapshot inicial
    snapshot = {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 50000,
        'mark_price': 51000,
        'liquidation_price': 45000,
        'position_size_qty': 0.5,
        'position_size_usdt': 25500,
        'leverage': 5,
        'margin_type': 'ISOLATED',
        'unrealized_pnl': 500,
        'unrealized_pnl_pct': 2.0,
        'margin_balance': 5000,
        'rsi_14': None, 'ema_17': None, 'ema_34': None, 'ema_72': None, 'ema_144': None,
        'macd_line': None, 'macd_signal': None, 'macd_histogram': None,
        'bb_upper': None, 'bb_lower': None, 'bb_percent_b': None,
        'atr_14': None, 'adx_14': None, 'di_plus': None, 'di_minus': None,
        'market_structure': None, 'bos_recent': 0, 'choch_recent': 0,
        'nearest_ob_distance_pct': None, 'nearest_fvg_distance_pct': None,
        'premium_discount_zone': None, 'liquidity_above_pct': None, 'liquidity_below_pct': None,
        'funding_rate': None, 'long_short_ratio': None, 'open_interest_change_pct': None,
        'agent_action': 'HOLD',
        'decision_confidence': 0.7,
        'decision_reasoning': '[]',
        'risk_score': 5.0,
        'stop_loss_suggested': None, 'take_profit_suggested': None, 'trailing_stop_price': None,
        'reward_calculated': None,
        'outcome_label': None
    }
    
    snapshot_id = temp_db.insert_position_snapshot(snapshot)
    
    # Atualizar outcome
    temp_db.update_snapshot_outcome(snapshot_id, reward=0.5, outcome_label='win')
    
    # Verificar atualização
    snapshots = temp_db.get_position_snapshots('BTCUSDT')
    assert len(snapshots) == 1
    assert snapshots[0]['reward_calculated'] == 0.5
    assert snapshots[0]['outcome_label'] == 'win'


def test_get_snapshots_for_training(position_monitor, temp_db):
    """Testa recuperação de snapshots para treinamento RL."""
    # Criar 3 snapshots: 2 com outcome, 1 sem
    base_snapshot = {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'symbol': 'ETHUSDT',
        'direction': 'LONG',
        'entry_price': 3000, 'mark_price': 3100, 'liquidation_price': 2500,
        'position_size_qty': 1, 'position_size_usdt': 3100, 'leverage': 5,
        'margin_type': 'ISOLATED', 'unrealized_pnl': 100, 'unrealized_pnl_pct': 3.33,
        'margin_balance': 1000,
        'rsi_14': None, 'ema_17': None, 'ema_34': None, 'ema_72': None, 'ema_144': None,
        'macd_line': None, 'macd_signal': None, 'macd_histogram': None,
        'bb_upper': None, 'bb_lower': None, 'bb_percent_b': None,
        'atr_14': None, 'adx_14': None, 'di_plus': None, 'di_minus': None,
        'market_structure': None, 'bos_recent': 0, 'choch_recent': 0,
        'nearest_ob_distance_pct': None, 'nearest_fvg_distance_pct': None,
        'premium_discount_zone': None, 'liquidity_above_pct': None, 'liquidity_below_pct': None,
        'funding_rate': None, 'long_short_ratio': None, 'open_interest_change_pct': None,
        'agent_action': 'HOLD', 'decision_confidence': 0.7, 'decision_reasoning': '[]',
        'risk_score': 5.0,
        'stop_loss_suggested': None, 'take_profit_suggested': None, 'trailing_stop_price': None,
        'reward_calculated': None, 'outcome_label': None
    }
    
    # Inserir 3 snapshots
    id1 = temp_db.insert_position_snapshot(base_snapshot)
    id2 = temp_db.insert_position_snapshot(base_snapshot)
    id3 = temp_db.insert_position_snapshot(base_snapshot)
    
    # Atualizar outcome de 2 deles
    temp_db.update_snapshot_outcome(id1, 0.8, 'win')
    temp_db.update_snapshot_outcome(id2, -0.3, 'loss')
    
    # Buscar para treinamento (apenas os com outcome)
    training_data = temp_db.get_snapshots_for_training(symbol='ETHUSDT')
    
    assert len(training_data) == 2
    assert all(snap['outcome_label'] is not None for snap in training_data)


def test_monitor_cycle_no_positions(position_monitor, mock_client):
    """Testa ciclo de monitoramento sem posições abertas."""
    # Mock sem posições
    mock_client.rest_api.position_information.return_value = []
    
    snapshots = position_monitor.monitor_cycle()
    
    assert len(snapshots) == 0
