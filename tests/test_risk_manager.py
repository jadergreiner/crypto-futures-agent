"""
Testes para risk manager.
"""

import pytest
from agent.risk_manager import RiskManager


def test_calculate_position_size():
    """Testa cálculo de tamanho de posição."""
    risk_manager = RiskManager()
    
    capital = 10000
    entry_price = 30000
    stop_distance_pct = 2.0  # 2%
    
    size = risk_manager.calculate_position_size(capital, entry_price, stop_distance_pct)
    
    # Com 2% de risco do capital ($200) e 2% de distância do stop ($600 por unidade)
    # Tamanho deve ser aproximadamente 200/600 = 0.333 unidades
    assert size > 0
    assert size < 1  # Deve ser menor que 1 unidade


def test_calculate_stop_loss():
    """Testa cálculo de stop loss."""
    risk_manager = RiskManager()
    
    entry_price = 30000
    atr = 500
    
    # Long stop
    stop_long = risk_manager.calculate_stop_loss(entry_price, atr, "LONG", multiplier=1.5)
    assert stop_long < entry_price
    assert stop_long == entry_price - (atr * 1.5)
    
    # Short stop
    stop_short = risk_manager.calculate_stop_loss(entry_price, atr, "SHORT", multiplier=1.5)
    assert stop_short > entry_price
    assert stop_short == entry_price + (atr * 1.5)


def test_calculate_take_profit():
    """Testa cálculo de take profit."""
    risk_manager = RiskManager()
    
    entry_price = 30000
    atr = 500
    
    # Long TP
    tp_long = risk_manager.calculate_take_profit(entry_price, atr, "LONG", multiplier=3.0)
    assert tp_long > entry_price
    assert tp_long == entry_price + (atr * 3.0)
    
    # Short TP
    tp_short = risk_manager.calculate_take_profit(entry_price, atr, "SHORT", multiplier=3.0)
    assert tp_short < entry_price
    assert tp_short == entry_price - (atr * 3.0)


def test_validate_new_trade():
    """Testa validação de novo trade."""
    risk_manager = RiskManager()
    
    capital = 10000
    open_positions = []
    
    # Primeiro trade deve ser permitido
    allowed, reason = risk_manager.validate_new_trade(
        open_positions, "BTCUSDT", "LONG", capital, 200
    )
    assert allowed is True
    
    # Simular 3 posições abertas
    open_positions = [
        {'symbol': 'BTCUSDT', 'direction': 'LONG', 'risk_usd': 200},
        {'symbol': 'ETHUSDT', 'direction': 'LONG', 'risk_usd': 200},
        {'symbol': 'SOLUSDT', 'direction': 'LONG', 'risk_usd': 200}
    ]
    
    # Quarto trade deve ser rejeitado (max 3 posições)
    allowed, reason = risk_manager.validate_new_trade(
        open_positions, "BNBUSDT", "LONG", capital, 200
    )
    assert allowed is False
    assert "Max simultaneous positions" in reason


def test_check_drawdown():
    """Testa verificação de drawdown."""
    risk_manager = RiskManager()
    
    # Sem drawdown
    portfolio = {
        'initial_capital': 10000,
        'current_capital': 10000,
        'peak_capital': 10000,
        'daily_start_capital': 10000
    }
    level, action = risk_manager.check_drawdown(portfolio)
    assert level == "OK"
    assert action == "NONE"
    
    # Drawdown diário crítico
    portfolio['current_capital'] = 9400  # 6% drawdown
    level, action = risk_manager.check_drawdown(portfolio)
    assert level == "DAILY_LIMIT"
    assert action == "CLOSE_ALL"


def test_adjust_size_by_confluence():
    """Testa ajuste de tamanho por confluência."""
    risk_manager = RiskManager()
    
    base_size = 1.0
    
    # Score baixo (< min) deve retornar 0
    adjusted = risk_manager.adjust_size_by_confluence(base_size, 7)
    assert adjusted == 0.0
    
    # Score mínimo deve retornar tamanho reduzido
    adjusted = risk_manager.adjust_size_by_confluence(base_size, 8)
    assert 0 < adjusted < base_size
    
    # Score alto deve retornar tamanho completo
    adjusted = risk_manager.adjust_size_by_confluence(base_size, 11)
    assert adjusted == base_size
