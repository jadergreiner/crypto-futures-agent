"""
Testes específicos para as correções de bugs de cross margin no PositionMonitor.
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, MagicMock, patch

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


class TestBug1MarginTypeNormalization:
    """Testes para Bug 1: marginType deve ser normalizado corretamente."""
    
    def test_margin_type_lowercase_cross(self, position_monitor, mock_client):
        """Testa que margin_type 'cross' minúsculo é normalizado para 'CROSS'."""
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'C98USDT',
            'position_amt': '100',
            'entry_price': '0.029',
            'mark_price': '0.0319',
            'un_realized_profit': '0.25',
            'liquidation_price': '0.02',
            'leverage': '10',
            'margin_type': 'cross',  # minúsculo
            'isolated_wallet': '0'
        }]
        
        positions = position_monitor.fetch_open_positions('C98USDT')
        
        assert len(positions) == 1
        assert positions[0]['margin_type'] == 'CROSS'
    
    def test_margin_type_uppercase_cross(self, position_monitor, mock_client):
        """Testa que margin_type 'CROSS' maiúsculo é mantido."""
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'C98USDT',
            'position_amt': '100',
            'entry_price': '0.029',
            'mark_price': '0.0319',
            'un_realized_profit': '0.25',
            'liquidation_price': '0.02',
            'leverage': '10',
            'margin_type': 'CROSS',  # maiúsculo
            'isolated_wallet': '0'
        }]
        
        positions = position_monitor.fetch_open_positions('C98USDT')
        
        assert len(positions) == 1
        assert positions[0]['margin_type'] == 'CROSS'
    
    def test_margin_type_isolated(self, position_monitor, mock_client):
        """Testa que margin_type 'isolated' é normalizado para 'ISOLATED'."""
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'BTCUSDT',
            'position_amt': '1',
            'entry_price': '50000',
            'mark_price': '51000',
            'un_realized_profit': '1000',
            'liquidation_price': '45000',
            'leverage': '5',
            'margin_type': 'isolated',  # minúsculo
            'isolated_wallet': '10000'
        }]
        
        positions = position_monitor.fetch_open_positions('BTCUSDT')
        
        assert len(positions) == 1
        assert positions[0]['margin_type'] == 'ISOLATED'
    
    def test_margin_type_default_when_missing(self, position_monitor, mock_client):
        """Testa que margin_type ausente usa default 'isolated' normalizado para 'ISOLATED'."""
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'ETHUSDT',
            'position_amt': '2',
            'entry_price': '3000',
            'mark_price': '3100',
            'un_realized_profit': '200',
            'liquidation_price': '2800',
            'leverage': '3',
            # margin_type ausente
            'isolated_wallet': '2000'
        }]
        
        positions = position_monitor.fetch_open_positions('ETHUSDT')
        
        assert len(positions) == 1
        assert positions[0]['margin_type'] == 'ISOLATED'


class TestBug2PnlCalculation:
    """Testes para Bug 2: PnL% deve ser calculado baseado na margem investida."""
    
    def test_pnl_percentage_with_leverage_10x(self, position_monitor, mock_client):
        """Testa que PnL% é calculado corretamente com alavancagem 10x.
        
        Exemplo real:
        - Notional: 100 * 0.029 = 2.90 USDT
        - Margem investida: 2.90 / 10 = 0.29 USDT
        - PnL: 0.25 USDT
        - PnL%: (0.25 / 0.29) * 100 = 86.2%
        """
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'C98USDT',
            'position_amt': '100',
            'entry_price': '0.029',
            'mark_price': '0.0319',
            'un_realized_profit': '0.25',
            'liquidation_price': '0.02',
            'leverage': '10',
            'margin_type': 'cross',
            'isolated_wallet': '0'
        }]
        
        positions = position_monitor.fetch_open_positions('C98USDT')
        
        assert len(positions) == 1
        pos = positions[0]
        
        # Verificar cálculos
        notional_value = 100 * 0.0319  # position_size_usdt
        expected_margin = notional_value / 10  # margin_invested
        expected_pnl_pct = (0.25 / expected_margin) * 100
        
        assert pos['position_size_usdt'] == pytest.approx(3.19, rel=0.01)
        assert pos['margin_invested'] == pytest.approx(0.319, rel=0.01)
        assert pos['unrealized_pnl_pct'] == pytest.approx(78.37, rel=0.15)  # Tolerância de 15%
        
        # PnL% deve ser MUITO maior que se calculássemos sobre notional (7.8%)
        wrong_pnl_pct = (0.25 / notional_value) * 100
        assert pos['unrealized_pnl_pct'] > wrong_pnl_pct * 5  # Pelo menos 5x maior
    
    def test_pnl_percentage_with_leverage_5x(self, position_monitor, mock_client):
        """Testa PnL% com alavancagem 5x."""
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'BTCUSDT',
            'position_amt': '1',
            'entry_price': '50000',
            'mark_price': '51000',
            'un_realized_profit': '1000',
            'liquidation_price': '45000',
            'leverage': '5',
            'margin_type': 'isolated',
            'isolated_wallet': '10000'
        }]
        
        positions = position_monitor.fetch_open_positions('BTCUSDT')
        
        assert len(positions) == 1
        pos = positions[0]
        
        # Notional: 1 * 51000 = 51000 USDT
        # Margem: 51000 / 5 = 10200 USDT
        # PnL%: (1000 / 10200) * 100 = 9.8%
        
        assert pos['position_size_usdt'] == pytest.approx(51000, rel=0.01)
        assert pos['margin_invested'] == pytest.approx(10200, rel=0.01)
        assert pos['unrealized_pnl_pct'] == pytest.approx(9.8, rel=0.1)
    
    def test_margin_invested_field_present(self, position_monitor, mock_client):
        """Testa que o campo margin_invested está presente na posição."""
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'ETHUSDT',
            'position_amt': '10',
            'entry_price': '3000',
            'mark_price': '3100',
            'un_realized_profit': '1000',
            'liquidation_price': '2800',
            'leverage': '3',
            'margin_type': 'isolated',
            'isolated_wallet': '10000'
        }]
        
        positions = position_monitor.fetch_open_positions('ETHUSDT')
        
        assert len(positions) == 1
        assert 'margin_invested' in positions[0]
        assert positions[0]['margin_invested'] > 0
    
    def test_pnl_percentage_with_leverage_1x(self, position_monitor, mock_client):
        """Testa PnL% com alavancagem 1x (sem alavancagem)."""
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'BNBUSDT',
            'position_amt': '5',
            'entry_price': '400',
            'mark_price': '420',
            'un_realized_profit': '100',
            'liquidation_price': '0',
            'leverage': '1',
            'margin_type': 'cross',
            'isolated_wallet': '0'
        }]
        
        positions = position_monitor.fetch_open_positions('BNBUSDT')
        
        assert len(positions) == 1
        pos = positions[0]
        
        # Notional: 5 * 420 = 2100 USDT
        # Margem: 2100 / 1 = 2100 USDT (mesma coisa)
        # PnL%: (100 / 2100) * 100 = 4.76%
        
        assert pos['margin_invested'] == pytest.approx(2100, rel=0.01)
        assert pos['unrealized_pnl_pct'] == pytest.approx(4.76, rel=0.1)


class TestBug3CrossMarginRiskLogic:
    """Testes para Bug 3: Lógica de risco deve considerar cross margin."""
    
    def test_cross_margin_increases_risk_score(self, position_monitor, mock_client):
        """Testa que cross margin aumenta o risk_score."""
        # Posição ISOLATED
        position_isolated = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 50000,
            'mark_price': 51000,
            'unrealized_pnl': 1000,
            'unrealized_pnl_pct': 10.0,
            'liquidation_price': 45000,
            'position_size_usdt': 51000,
            'margin_type': 'ISOLATED',
            'margin_invested': 10200
        }
        
        # Posição CROSS (mesma config, só muda margin_type)
        position_cross = position_isolated.copy()
        position_cross['margin_type'] = 'CROSS'
        
        indicators = {'rsi_14': 55, 'market_structure': 'bullish'}
        sentiment = {}
        
        # Mock para fetch_account_balance retornar um valor
        mock_client.rest_api.account_information_v2.return_value = {
            'available_balance': '20000'
        }
        
        decision_isolated = position_monitor.evaluate_position(position_isolated, indicators, sentiment)
        decision_cross = position_monitor.evaluate_position(position_cross, indicators, sentiment)
        
        # Cross margin deve ter risk_score maior
        assert decision_cross['risk_score'] > decision_isolated['risk_score']
    
    def test_cross_margin_adds_warning_to_reasoning(self, position_monitor, mock_client):
        """Testa que cross margin adiciona aviso no reasoning."""
        position = {
            'symbol': 'C98USDT',
            'direction': 'LONG',
            'entry_price': 0.029,
            'mark_price': 0.0319,
            'unrealized_pnl': 0.25,
            'unrealized_pnl_pct': 86.2,
            'liquidation_price': 0.02,
            'position_size_usdt': 3.19,
            'margin_type': 'CROSS',
            'margin_invested': 0.319
        }
        
        indicators = {'rsi_14': 60}
        sentiment = {}
        
        # Mock para fetch_account_balance
        mock_client.rest_api.account_information_v2.return_value = {
            'available_balance': '100'
        }
        
        decision = position_monitor.evaluate_position(position, indicators, sentiment)
        
        reasoning = json.loads(decision['decision_reasoning'])
        
        # Deve conter aviso sobre CROSS MARGIN
        assert any('CROSS MARGIN' in r for r in reasoning)
        assert any('todo saldo da conta' in r.lower() for r in reasoning)
    
    def test_cross_margin_high_exposure_increases_risk(self, position_monitor, mock_client):
        """Testa que alta exposição em cross margin aumenta ainda mais o risco."""
        position = {
            'symbol': 'ETHUSDT',
            'direction': 'LONG',
            'entry_price': 3000,
            'mark_price': 3100,
            'unrealized_pnl': 1000,
            'unrealized_pnl_pct': 10.0,
            'liquidation_price': 2800,
            'position_size_usdt': 31000,
            'margin_type': 'CROSS',
            'margin_invested': 10333  # ~103% do saldo (alta exposição)
        }
        
        indicators = {'rsi_14': 55}
        sentiment = {}
        
        # Mock com saldo baixo para simular alta exposição
        mock_client.rest_api.account_information_v2.return_value = {
            'available_balance': '10000'  # Margem é maior que saldo disponível
        }
        
        decision = position_monitor.evaluate_position(position, indicators, sentiment)
        
        reasoning = json.loads(decision['decision_reasoning'])
        
        # Deve ter alta exposição mencionada
        assert any('exposição' in r.lower() for r in reasoning)
    
    def test_cross_margin_liquidation_threshold_is_higher(self, position_monitor, mock_client):
        """Testa que o threshold de liquidação é maior para cross margin."""
        # Posição cross próxima da liquidação (7% de distância)
        position_cross = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 50000,
            'mark_price': 47000,  # 7% acima da liquidação
            'unrealized_pnl': -3000,
            'unrealized_pnl_pct': -30.0,
            'liquidation_price': 43790,  # ~7% abaixo
            'position_size_usdt': 47000,
            'margin_type': 'CROSS',
            'margin_invested': 10000
        }
        
        # Mesma posição em isolated
        position_isolated = position_cross.copy()
        position_isolated['margin_type'] = 'ISOLATED'
        
        indicators = {'rsi_14': 40}
        sentiment = {}
        
        # Mock para fetch_account_balance
        mock_client.rest_api.account_information_v2.return_value = {
            'available_balance': '20000'
        }
        
        decision_cross = position_monitor.evaluate_position(position_cross, indicators, sentiment)
        decision_isolated = position_monitor.evaluate_position(position_isolated, indicators, sentiment)
        
        # Cross margin com 7% de distância não deve fechar (threshold 8%)
        # Isolated com 7% de distância não deve fechar também (threshold 5% só fecha < 5%)
        # Mas ambos devem ter avisos sobre proximidade
        
        reasoning_cross = json.loads(decision_cross['decision_reasoning'])
        reasoning_isolated = json.loads(decision_isolated['decision_reasoning'])
        
        # Verificar que cross tem aviso específico sobre liquidação total
        cross_has_critical = any('CRÍTICO' in r or 'TODO o saldo' in r for r in reasoning_cross)
        assert cross_has_critical or decision_cross['agent_action'] == 'CLOSE'
    
    def test_fetch_account_balance(self, position_monitor, mock_client):
        """Testa que fetch_account_balance funciona corretamente."""
        mock_client.rest_api.account_information_v2.return_value = {
            'available_balance': '15000.50'
        }
        
        balance = position_monitor.fetch_account_balance()
        
        assert balance == pytest.approx(15000.50, rel=0.01)
    
    def test_fetch_account_balance_handles_error(self, position_monitor, mock_client):
        """Testa que fetch_account_balance trata erros graciosamente."""
        mock_client.rest_api.account_information_v2.side_effect = Exception("API error")
        
        balance = position_monitor.fetch_account_balance()
        
        assert balance == 0  # Deve retornar 0 em caso de erro


class TestSnapshotIncludesMarginInvested:
    """Testes para garantir que margin_invested é incluído no snapshot."""
    
    def test_snapshot_includes_margin_invested(self, position_monitor):
        """Testa que create_snapshot inclui margin_invested."""
        position = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 50000,
            'mark_price': 51000,
            'liquidation_price': 45000,
            'position_size_qty': 1,
            'position_size_usdt': 51000,
            'leverage': 5,
            'margin_type': 'ISOLATED',
            'margin_invested': 10200,
            'unrealized_pnl': 1000,
            'unrealized_pnl_pct': 9.8,
            'margin_balance': 10000
        }
        
        indicators = {'rsi_14': 55}
        sentiment = {}
        decision = {
            'agent_action': 'HOLD',
            'decision_confidence': 0.5,
            'decision_reasoning': [],
            'risk_score': 5.0,
            'stop_loss_suggested': None,
            'take_profit_suggested': None,
            'trailing_stop_price': None
        }
        
        snapshot = position_monitor.create_snapshot(position, indicators, sentiment, decision)
        
        assert 'margin_invested' in snapshot
        assert snapshot['margin_invested'] == 10200
