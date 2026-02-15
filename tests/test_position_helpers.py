"""
Testes unitários para os métodos helper de avaliação de posição.
Validam a simetria e lógica dos helpers de interpretação direcional.
"""

import pytest
from unittest.mock import Mock

from monitoring.position_monitor import PositionMonitor
from data.database import DatabaseManager


@pytest.fixture
def position_monitor():
    """Fixture simplificada do PositionMonitor para testar helpers estáticos."""
    mock_client = Mock()
    mock_db = Mock(spec=DatabaseManager)
    return PositionMonitor(mock_client, mock_db, mode="paper")


class TestMarketStructureHelpers:
    """Testa os helpers de interpretação de estrutura SMC."""
    
    def test_is_market_structure_adverse_long_bearish(self):
        """LONG com estrutura bearish deve ser adverso."""
        assert PositionMonitor._is_market_structure_adverse('LONG', 'bearish') is True
    
    def test_is_market_structure_adverse_long_bullish(self):
        """LONG com estrutura bullish não deve ser adverso."""
        assert PositionMonitor._is_market_structure_adverse('LONG', 'bullish') is False
    
    def test_is_market_structure_adverse_short_bullish(self):
        """SHORT com estrutura bullish deve ser adverso."""
        assert PositionMonitor._is_market_structure_adverse('SHORT', 'bullish') is True
    
    def test_is_market_structure_adverse_short_bearish(self):
        """SHORT com estrutura bearish não deve ser adverso."""
        assert PositionMonitor._is_market_structure_adverse('SHORT', 'bearish') is False
    
    def test_is_market_structure_favorable_long_bullish(self):
        """LONG com estrutura bullish deve ser favorável."""
        assert PositionMonitor._is_market_structure_favorable('LONG', 'bullish') is True
    
    def test_is_market_structure_favorable_long_bearish(self):
        """LONG com estrutura bearish não deve ser favorável."""
        assert PositionMonitor._is_market_structure_favorable('LONG', 'bearish') is False
    
    def test_is_market_structure_favorable_short_bearish(self):
        """SHORT com estrutura bearish deve ser favorável."""
        assert PositionMonitor._is_market_structure_favorable('SHORT', 'bearish') is True
    
    def test_is_market_structure_favorable_short_bullish(self):
        """SHORT com estrutura bullish não deve ser favorável."""
        assert PositionMonitor._is_market_structure_favorable('SHORT', 'bullish') is False
    
    def test_symmetry_adverse_vs_favorable(self):
        """Testa simetria: se é adverso para LONG, deve ser favorável para SHORT e vice-versa."""
        # Estrutura bullish: favorável para LONG, adverso para SHORT
        assert PositionMonitor._is_market_structure_favorable('LONG', 'bullish') is True
        assert PositionMonitor._is_market_structure_adverse('SHORT', 'bullish') is True
        
        # Estrutura bearish: adverso para LONG, favorável para SHORT
        assert PositionMonitor._is_market_structure_adverse('LONG', 'bearish') is True
        assert PositionMonitor._is_market_structure_favorable('SHORT', 'bearish') is True


class TestRSIInterpretation:
    """Testa o helper de interpretação de RSI contextualizado por direção."""
    
    def test_long_reversal_signal_low_rsi(self):
        """LONG com RSI < 30 deve gerar sinal de reversão."""
        result = PositionMonitor._interpret_rsi('LONG', 25.0, 50000.0, 49000.0)
        assert result['is_reversal_signal'] is True
        assert result['is_favorable'] is False
        assert 'risco' in result['message'].lower()
    
    def test_long_reversal_signal_price_below_ema(self):
        """LONG com preço abaixo da EMA72 deve gerar sinal de reversão."""
        result = PositionMonitor._interpret_rsi('LONG', 50.0, 48000.0, 50000.0)
        assert result['is_reversal_signal'] is True
        assert result['is_favorable'] is False
    
    def test_long_favorable_high_rsi_and_price(self):
        """LONG com RSI > 50 e preço acima da EMA72 deve ser favorável."""
        result = PositionMonitor._interpret_rsi('LONG', 60.0, 51000.0, 50000.0)
        assert result['is_reversal_signal'] is False
        assert result['is_favorable'] is True
        assert 'favorável' in result['message'].lower()
    
    def test_short_reversal_signal_high_rsi(self):
        """SHORT com RSI > 70 deve gerar sinal de reversão."""
        result = PositionMonitor._interpret_rsi('SHORT', 75.0, 50000.0, 51000.0)
        assert result['is_reversal_signal'] is True
        assert result['is_favorable'] is False
        assert 'risco' in result['message'].lower()
    
    def test_short_reversal_signal_price_above_ema(self):
        """SHORT com preço acima da EMA72 deve gerar sinal de reversão."""
        result = PositionMonitor._interpret_rsi('SHORT', 50.0, 52000.0, 50000.0)
        assert result['is_reversal_signal'] is True
        assert result['is_favorable'] is False
    
    def test_short_favorable_low_rsi_and_price(self):
        """SHORT com RSI < 50 e preço abaixo da EMA72 deve ser favorável."""
        result = PositionMonitor._interpret_rsi('SHORT', 40.0, 49000.0, 50000.0)
        assert result['is_reversal_signal'] is False
        assert result['is_favorable'] is True
        assert 'favorável' in result['message'].lower()
    
    def test_symmetry_reversal_conditions(self):
        """Testa simetria: condições de reversão espelhadas para LONG e SHORT."""
        # RSI extremo oposto deve gerar reversão em ambas as direções
        long_result = PositionMonitor._interpret_rsi('LONG', 25.0, 50000.0, 50000.0)
        short_result = PositionMonitor._interpret_rsi('SHORT', 75.0, 50000.0, 50000.0)
        
        assert long_result['is_reversal_signal'] is True
        assert short_result['is_reversal_signal'] is True


class TestEMAAlignment:
    """Testa o helper de interpretação de alinhamento de EMAs."""
    
    def test_long_favorable_uptrend(self):
        """LONG com EMAs alinhadas para alta (17 > 34 > 72 > 144) deve ser favorável."""
        result = PositionMonitor._interpret_ema_alignment('LONG', 1000, 900, 800, 700)
        assert result['is_favorable'] is True
        assert result['is_adverse'] is False
        assert result['risk_adjustment'] == -0.5
        assert 'bullish' in result['message'].lower()
    
    def test_long_adverse_downtrend(self):
        """LONG com EMAs alinhadas para baixa (17 < 34 < 72 < 144) deve ser adverso."""
        result = PositionMonitor._interpret_ema_alignment('LONG', 700, 800, 900, 1000)
        assert result['is_favorable'] is False
        assert result['is_adverse'] is True
        assert result['risk_adjustment'] == 1.0
        assert 'aviso' in result['message'].lower()
    
    def test_short_favorable_downtrend(self):
        """SHORT com EMAs alinhadas para baixa (17 < 34 < 72 < 144) deve ser favorável."""
        result = PositionMonitor._interpret_ema_alignment('SHORT', 700, 800, 900, 1000)
        assert result['is_favorable'] is True
        assert result['is_adverse'] is False
        assert result['risk_adjustment'] == -0.5
        assert 'bearish' in result['message'].lower()
    
    def test_short_adverse_uptrend(self):
        """SHORT com EMAs alinhadas para alta (17 > 34 > 72 > 144) deve ser adverso."""
        result = PositionMonitor._interpret_ema_alignment('SHORT', 1000, 900, 800, 700)
        assert result['is_favorable'] is False
        assert result['is_adverse'] is True
        assert result['risk_adjustment'] == 1.0
        assert 'aviso' in result['message'].lower()
    
    def test_symmetry_same_ema_alignment(self):
        """Testa simetria: mesma configuração de EMAs deve ter efeitos opostos em LONG vs SHORT."""
        # EMAs alinhadas para alta: favorável LONG, adverso SHORT
        long_result = PositionMonitor._interpret_ema_alignment('LONG', 1000, 900, 800, 700)
        short_result = PositionMonitor._interpret_ema_alignment('SHORT', 1000, 900, 800, 700)
        
        assert long_result['is_favorable'] is True
        assert short_result['is_adverse'] is True
        assert long_result['risk_adjustment'] == -0.5
        assert short_result['risk_adjustment'] == 1.0


class TestFundingRateAdverse:
    """Testa o helper de verificação de funding rate adverso."""
    
    def test_long_adverse_high_positive_funding(self):
        """LONG com funding rate muito positivo (> threshold) deve ser adverso."""
        # funding_rate = 0.0006 -> 0.06% > threshold 0.05%
        assert PositionMonitor._is_funding_rate_adverse('LONG', 0.0006, 0.05) is True
    
    def test_long_not_adverse_low_funding(self):
        """LONG com funding rate baixo não deve ser adverso."""
        # funding_rate = 0.0003 -> 0.03% < threshold 0.05%
        assert PositionMonitor._is_funding_rate_adverse('LONG', 0.0003, 0.05) is False
    
    def test_long_not_adverse_negative_funding(self):
        """LONG com funding rate negativo não deve ser adverso (favorável)."""
        # funding_rate = -0.0006 -> -0.06% (negativo é favorável para LONG)
        assert PositionMonitor._is_funding_rate_adverse('LONG', -0.0006, 0.05) is False
    
    def test_short_adverse_high_negative_funding(self):
        """SHORT com funding rate muito negativo (< -threshold) deve ser adverso."""
        # funding_rate = -0.0006 -> -0.06% < -0.05%
        assert PositionMonitor._is_funding_rate_adverse('SHORT', -0.0006, 0.05) is True
    
    def test_short_not_adverse_low_funding(self):
        """SHORT com funding rate baixo não deve ser adverso."""
        # funding_rate = -0.0003 -> -0.03% > -0.05%
        assert PositionMonitor._is_funding_rate_adverse('SHORT', -0.0003, 0.05) is False
    
    def test_short_not_adverse_positive_funding(self):
        """SHORT com funding rate positivo não deve ser adverso (favorável)."""
        # funding_rate = 0.0006 -> 0.06% (positivo é favorável para SHORT)
        assert PositionMonitor._is_funding_rate_adverse('SHORT', 0.0006, 0.05) is False
    
    def test_symmetry_funding_rate(self):
        """Testa simetria: funding extremo oposto deve ser adverso para cada direção."""
        # Funding muito positivo: adverso para LONG, não adverso para SHORT
        assert PositionMonitor._is_funding_rate_adverse('LONG', 0.0008, 0.05) is True
        assert PositionMonitor._is_funding_rate_adverse('SHORT', 0.0008, 0.05) is False
        
        # Funding muito negativo: não adverso para LONG, adverso para SHORT
        assert PositionMonitor._is_funding_rate_adverse('LONG', -0.0008, 0.05) is False
        assert PositionMonitor._is_funding_rate_adverse('SHORT', -0.0008, 0.05) is True


class TestCalculateSuggestedStops:
    """Testa o helper de cálculo de stop loss e take profit."""
    
    def test_long_stops_without_ob(self):
        """LONG sem Order Block deve usar apenas ATR."""
        result = PositionMonitor._calculate_suggested_stops(
            'LONG', 50000.0, 51000.0, 500.0, 2.0, 3.0, None
        )
        
        # Stop = entry - (atr * stop_multiplier) = 50000 - (500 * 2) = 49000
        assert result['stop_loss'] == 49000.0
        # TP = entry + (atr * tp_multiplier) = 50000 + (500 * 3) = 51500
        assert result['take_profit'] == 51500.0
    
    def test_long_stops_with_ob(self):
        """LONG com Order Block deve considerar OB no cálculo do stop."""
        result = PositionMonitor._calculate_suggested_stops(
            'LONG', 50000.0, 51000.0, 500.0, 2.0, 3.0, 2.0  # OB a 2% abaixo
        )
        
        # OB price = 51000 * (1 - 0.02) = 49980
        # SMC stop = 49980 - (500 * 0.5) = 49730
        # ATR stop = 50000 - (500 * 2) = 49000
        # Stop loss = max(49730, 49000) = 49730 (mais conservador)
        assert result['stop_loss'] == 49730.0
        assert result['take_profit'] == 51500.0
    
    def test_short_stops_without_ob(self):
        """SHORT sem Order Block deve usar apenas ATR."""
        result = PositionMonitor._calculate_suggested_stops(
            'SHORT', 50000.0, 49000.0, 500.0, 2.0, 3.0, None
        )
        
        # Stop = entry + (atr * stop_multiplier) = 50000 + (500 * 2) = 51000
        assert result['stop_loss'] == 51000.0
        # TP = entry - (atr * tp_multiplier) = 50000 - (500 * 3) = 48500
        assert result['take_profit'] == 48500.0
    
    def test_short_stops_with_ob(self):
        """SHORT com Order Block deve considerar OB no cálculo do stop."""
        result = PositionMonitor._calculate_suggested_stops(
            'SHORT', 50000.0, 49000.0, 500.0, 2.0, 3.0, 2.0  # OB a 2% acima
        )
        
        # OB price = 49000 * (1 + 0.02) = 49980
        # SMC stop = 49980 + (500 * 0.5) = 50230
        # ATR stop = 50000 + (500 * 2) = 51000
        # Stop loss = min(50230, 51000) = 50230 (mais conservador)
        assert result['stop_loss'] == 50230.0
        assert result['take_profit'] == 48500.0
    
    def test_symmetry_stop_distance(self):
        """Testa simetria: mesmos parâmetros devem gerar distâncias simétricas em LONG vs SHORT."""
        entry = 50000.0
        mark = 50000.0
        atr = 500.0
        
        long_result = PositionMonitor._calculate_suggested_stops(
            'LONG', entry, mark, atr, 2.0, 3.0, None
        )
        short_result = PositionMonitor._calculate_suggested_stops(
            'SHORT', entry, mark, atr, 2.0, 3.0, None
        )
        
        # Distância do stop em relação ao entry deve ser igual
        long_stop_distance = abs(entry - long_result['stop_loss'])
        short_stop_distance = abs(entry - short_result['stop_loss'])
        assert long_stop_distance == short_stop_distance
        
        # Distância do TP em relação ao entry deve ser igual
        long_tp_distance = abs(entry - long_result['take_profit'])
        short_tp_distance = abs(entry - short_result['take_profit'])
        assert long_tp_distance == short_tp_distance


class TestIntegrationSymmetry:
    """Testa a simetria geral: situações espelhadas devem gerar decisões simétricas."""
    
    def test_favorable_conditions_symmetry(self, position_monitor):
        """Condições favoráveis espelhadas devem gerar decisões similares para LONG e SHORT."""
        # Posição LONG favorável
        long_position = {
            'direction': 'LONG',
            'unrealized_pnl_pct': 5.0,
            'mark_price': 51000.0,
            'entry_price': 50000.0,
            'liquidation_price': 45000.0,
            'margin_type': 'ISOLATED',
            'symbol': 'BTCUSDT',
            'margin_invested': 1000.0
        }
        
        long_indicators = {
            'market_structure': 'bullish',
            'bos_recent': 1,
            'choch_recent': 0,
            'rsi_14': 60.0,
            'ema_17': 51000.0,
            'ema_34': 50500.0,
            'ema_72': 50000.0,
            'ema_144': 49500.0,
            'atr_14': 500.0,
            'funding_rate': -0.01,  # Favorável para LONG
            'nearest_ob_distance_pct': None
        }
        
        # Posição SHORT favorável (espelhada)
        short_position = {
            'direction': 'SHORT',
            'unrealized_pnl_pct': 5.0,
            'mark_price': 49000.0,
            'entry_price': 50000.0,
            'liquidation_price': 55000.0,
            'margin_type': 'ISOLATED',
            'symbol': 'BTCUSDT',
            'margin_invested': 1000.0
        }
        
        short_indicators = {
            'market_structure': 'bearish',
            'bos_recent': 1,
            'choch_recent': 0,
            'rsi_14': 40.0,
            'ema_17': 49000.0,
            'ema_34': 49500.0,
            'ema_72': 50000.0,
            'ema_144': 50500.0,
            'atr_14': 500.0,
            'funding_rate': 0.01,  # Favorável para SHORT
            'nearest_ob_distance_pct': None
        }
        
        sentiment = {}
        
        long_decision = position_monitor.evaluate_position(long_position, long_indicators, sentiment)
        short_decision = position_monitor.evaluate_position(short_position, short_indicators, sentiment)
        
        # Ambas as decisões devem ser similares (HOLD com risk score baixo)
        assert long_decision['agent_action'] == 'HOLD'
        assert short_decision['agent_action'] == 'HOLD'
        
        # Risk scores devem ser similares (ambos favoráveis)
        assert abs(long_decision['risk_score'] - short_decision['risk_score']) < 1.0
