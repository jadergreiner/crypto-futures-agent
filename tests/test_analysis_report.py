"""
Testes para o relatório de análise detalhada do PositionMonitor.
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, MagicMock, patch
from io import StringIO

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


def test_format_rsi_interpretation_oversold(position_monitor):
    """Testa interpretação de RSI sobrevendido."""
    assert position_monitor._format_rsi_interpretation(25) == "Sobrevendido"
    assert position_monitor._format_rsi_interpretation(29.9) == "Sobrevendido"


def test_format_rsi_interpretation_neutral(position_monitor):
    """Testa interpretação de RSI neutro."""
    assert position_monitor._format_rsi_interpretation(50) == "Neutro"
    assert position_monitor._format_rsi_interpretation(52) == "Neutro"


def test_format_rsi_interpretation_overbought(position_monitor):
    """Testa interpretação de RSI sobrecomprado."""
    assert position_monitor._format_rsi_interpretation(75) == "Sobrecomprado"
    assert position_monitor._format_rsi_interpretation(80) == "Sobrecomprado"


def test_format_macd_interpretation_bullish(position_monitor):
    """Testa interpretação de MACD bullish."""
    assert position_monitor._format_macd_interpretation(0.001) == "Bullish"
    assert position_monitor._format_macd_interpretation(0.5) == "Bullish"


def test_format_macd_interpretation_bearish(position_monitor):
    """Testa interpretação de MACD bearish."""
    assert position_monitor._format_macd_interpretation(-0.001) == "Bearish"
    assert position_monitor._format_macd_interpretation(-0.5) == "Bearish"


def test_format_macd_interpretation_none(position_monitor):
    """Testa interpretação de MACD quando valor é None."""
    assert position_monitor._format_macd_interpretation(None) == "N/D"


def test_format_adx_interpretation_no_trend(position_monitor):
    """Testa interpretação de ADX sem tendência."""
    result = position_monitor._format_adx_interpretation(15, 20, 18)
    assert "Sem Tendencia" in result


def test_format_adx_interpretation_moderate_bullish(position_monitor):
    """Testa interpretação de ADX tendência moderada bullish."""
    result = position_monitor._format_adx_interpretation(30, 25, 18)
    assert "Tendencia Moderada" in result
    assert "Bullish" in result


def test_format_adx_interpretation_strong_bearish(position_monitor):
    """Testa interpretação de ADX tendência forte bearish."""
    result = position_monitor._format_adx_interpretation(45, 18, 25)
    assert "Tendencia Forte" in result
    assert "Bearish" in result


def test_format_bb_interpretation_upper_zone(position_monitor):
    """Testa interpretação de Bollinger Bands zona superior."""
    assert position_monitor._format_bb_interpretation(0.85) == "Zona Superior"
    assert position_monitor._format_bb_interpretation(0.95) == "Zona Superior"


def test_format_bb_interpretation_lower_zone(position_monitor):
    """Testa interpretação de Bollinger Bands zona inferior."""
    assert position_monitor._format_bb_interpretation(0.15) == "Zona Inferior"
    assert position_monitor._format_bb_interpretation(0.05) == "Zona Inferior"


def test_check_ema_alignment_bullish(position_monitor):
    """Testa alinhamento de EMAs bullish."""
    result = position_monitor._check_ema_alignment(0.055, 0.053, 0.051, 0.049)
    assert result == "Alinhadas para ALTA"


def test_check_ema_alignment_bearish(position_monitor):
    """Testa alinhamento de EMAs bearish."""
    result = position_monitor._check_ema_alignment(0.049, 0.051, 0.053, 0.055)
    assert result == "Alinhadas para BAIXA"


def test_check_ema_alignment_mixed(position_monitor):
    """Testa alinhamento de EMAs misturadas."""
    result = position_monitor._check_ema_alignment(0.052, 0.051, 0.053, 0.049)
    assert "Misturadas" in result


def test_check_ema_alignment_with_none(position_monitor):
    """Testa alinhamento de EMAs com valores None."""
    result = position_monitor._check_ema_alignment(None, 0.051, 0.053, 0.049)
    assert result == "N/D"


def test_format_premium_discount_premium(position_monitor):
    """Testa formatação de zona premium."""
    assert position_monitor._format_premium_discount('premium') == "PREMIUM"
    assert position_monitor._format_premium_discount('deep_premium') == "DEEP PREMIUM"


def test_format_premium_discount_discount(position_monitor):
    """Testa formatação de zona discount."""
    assert position_monitor._format_premium_discount('discount') == "DISCOUNT"
    assert position_monitor._format_premium_discount('deep_discount') == "DEEP DISCOUNT"


def test_format_premium_discount_equilibrium(position_monitor):
    """Testa formatação de zona de equilíbrio."""
    assert position_monitor._format_premium_discount('equilibrium') == "EQUILIBRIO"


@patch('monitoring.position_monitor.logger')
def test_log_analysis_report_basic(mock_logger, position_monitor):
    """Testa que _log_analysis_report gera logs sem erros."""
    position = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'mark_price': 52000.0,
        'margin_invested': 1000.0,
        'unrealized_pnl': 200.0,
        'unrealized_pnl_pct': 20.0,
        'leverage': 10,
        'margin_type': 'ISOLATED'
    }
    
    indicators = {
        'rsi_14': 62.3,
        'macd_line': 0.0012,
        'macd_signal': 0.0008,
        'macd_histogram': 0.0004,
        'ema_17': 51500.0,
        'ema_34': 51000.0,
        'ema_72': 50500.0,
        'ema_144': 50000.0,
        'adx_14': 28.5,
        'di_plus': 25.3,
        'di_minus': 18.1,
        'bb_upper': 53000.0,
        'bb_lower': 49000.0,
        'bb_percent_b': 0.72,
        'atr_14': 500.0,
        'market_structure': 'bullish',
        'bos_recent': 1,
        'choch_recent': 0,
        'premium_discount_zone': 'premium',
        'nearest_ob_distance_pct': 8.1,
        'nearest_fvg_distance_pct': 5.4,
        'liquidity_above_pct': 4.2,
        'liquidity_below_pct': 6.8,
        'funding_rate': 0.0001,
        'long_short_ratio': 1.85,
        'open_interest_change_pct': 3.2
    }
    
    sentiment = {}
    
    decision = {
        'agent_action': 'HOLD',
        'decision_confidence': 0.75,
        'risk_score': 3.5,
        'decision_reasoning': json.dumps([
            "Estrutura bullish com BOS confirmado - favoravel para LONG",
            "EMAs alinhadas para alta - tendencia bullish confirmada"
        ]),
        'stop_loss_suggested': 49500.0,
        'take_profit_suggested': 54000.0,
        'trailing_stop_price': None
    }
    
    # Executar o método
    position_monitor._log_analysis_report(position, indicators, sentiment, decision)
    
    # Verificar que logger.info foi chamado (múltiplas vezes)
    assert mock_logger.info.call_count > 10
    
    # Verificar que algumas palavras-chave aparecem nos logs
    logged_text = ' '.join([str(call[0][0]) for call in mock_logger.info.call_args_list])
    assert 'BTCUSDT' in logged_text
    assert 'LONG' in logged_text
    assert 'RSI' in logged_text
    assert 'MACD' in logged_text
    assert 'EMAs' in logged_text
    assert 'BULLISH' in logged_text
    assert 'HOLD' in logged_text


@patch('monitoring.position_monitor.logger')
def test_log_analysis_report_handles_none_values(mock_logger, position_monitor):
    """Testa que _log_analysis_report lida com valores None corretamente."""
    position = {
        'symbol': 'ETHUSDT',
        'direction': 'SHORT',
        'entry_price': 3000.0,
        'mark_price': 2900.0,
        'margin_invested': 500.0,
        'unrealized_pnl': 50.0,
        'unrealized_pnl_pct': 10.0,
        'leverage': 5,
        'margin_type': 'CROSS'
    }
    
    # Indicators com muitos None
    indicators = {
        'rsi_14': None,
        'macd_line': None,
        'macd_signal': None,
        'macd_histogram': None,
        'ema_17': None,
        'ema_34': None,
        'ema_72': None,
        'ema_144': None,
        'adx_14': None,
        'market_structure': 'range',
        'bos_recent': 0,
        'choch_recent': 0,
        'premium_discount_zone': None,
        'nearest_ob_distance_pct': None,
        'nearest_fvg_distance_pct': None,
        'liquidity_above_pct': None,
        'liquidity_below_pct': None,
        'funding_rate': None,
        'long_short_ratio': None,
        'open_interest_change_pct': None
    }
    
    sentiment = {}
    
    decision = {
        'agent_action': 'HOLD',
        'decision_confidence': 0.5,
        'risk_score': 5.0,
        'decision_reasoning': json.dumps(["Posição estável"]),
        'stop_loss_suggested': None,
        'take_profit_suggested': None,
        'trailing_stop_price': None
    }
    
    # Executar o método - não deve lançar exceção
    position_monitor._log_analysis_report(position, indicators, sentiment, decision)
    
    # Verificar que N/D aparece nos logs para valores ausentes
    logged_text = ' '.join([str(call[0][0]) for call in mock_logger.info.call_args_list])
    assert 'N/D' in logged_text
    assert mock_logger.info.call_count > 10


def test_evaluate_position_adds_smc_reasoning_long(position_monitor):
    """Testa que evaluate_position adiciona reasoning sobre SMC para LONG."""
    position = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'mark_price': 52000.0,
        'liquidation_price': 45000.0,
        'unrealized_pnl_pct': 4.0,
        'margin_type': 'ISOLATED'
    }
    
    indicators = {
        'market_structure': 'bullish',
        'bos_recent': 1,
        'choch_recent': 0,
        'rsi_14': 60.0,
        'ema_17': 51500.0,
        'ema_34': 51000.0,
        'ema_72': 50500.0,
        'ema_144': 50000.0,
        'atr_14': 500.0,
        'nearest_ob_distance_pct': 5.0
    }
    
    sentiment = {}
    
    decision = position_monitor.evaluate_position(position, indicators, sentiment)
    
    # Verificar que reasoning foi adicionado
    reasoning = json.loads(decision['decision_reasoning'])
    assert len(reasoning) > 0
    
    # Verificar que reasoning menciona SMC
    reasoning_text = ' '.join(reasoning)
    assert 'bullish' in reasoning_text.lower() or 'BOS' in reasoning_text


def test_evaluate_position_uses_smc_for_stop_loss(position_monitor):
    """Testa que evaluate_position usa níveis SMC para calcular stop loss."""
    position = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'mark_price': 52000.0,
        'liquidation_price': 45000.0,
        'unrealized_pnl_pct': 4.0,
        'margin_type': 'ISOLATED'
    }
    
    indicators = {
        'market_structure': 'bullish',
        'atr_14': 500.0,
        'nearest_ob_distance_pct': 5.0  # OB 5% abaixo do mark_price
    }
    
    sentiment = {}
    
    decision = position_monitor.evaluate_position(position, indicators, sentiment)
    
    # Verificar que stop loss foi calculado
    assert decision['stop_loss_suggested'] is not None
    
    # Stop loss deve estar abaixo do preço de entrada
    assert decision['stop_loss_suggested'] < position['entry_price']
