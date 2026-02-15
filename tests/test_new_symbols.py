"""
Test for new symbols and playbooks added.
Verifies that the 5 new symbols are properly configured and their playbooks work.
"""

import pytest
from config.symbols import SYMBOLS, ALL_SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS, EXECUTION_CONFIG
from playbooks import (
    ZeroGPlaybook, KAIAPlaybook, AXLPlaybook, NILPlaybook, FOGOPlaybook
)


# New symbols that were added
NEW_SYMBOLS = ['0GUSDT', 'KAIAUSDT', 'AXLUSDT', 'NILUSDT', 'FOGOUSDT']


def test_new_symbols_in_config():
    """Test that all 5 new symbols are in SYMBOLS dict."""
    for symbol in NEW_SYMBOLS:
        assert symbol in SYMBOLS, f"{symbol} not found in SYMBOLS"
        
        # Verify required fields
        config = SYMBOLS[symbol]
        assert 'papel' in config
        assert 'ciclo_proprio' in config
        assert 'correlacao_btc' in config
        assert 'beta_estimado' in config
        assert 'classificacao' in config
        assert 'caracteristicas' in config


def test_new_symbols_auto_populated():
    """Test that ALL_SYMBOLS auto-populates from SYMBOLS."""
    assert len(ALL_SYMBOLS) == len(SYMBOLS)
    for symbol in NEW_SYMBOLS:
        assert symbol in ALL_SYMBOLS


def test_new_symbols_authorized():
    """Test that all 5 new symbols are in AUTHORIZED_SYMBOLS."""
    for symbol in NEW_SYMBOLS:
        assert symbol in AUTHORIZED_SYMBOLS, f"{symbol} not in AUTHORIZED_SYMBOLS"


def test_max_daily_executions_updated():
    """Test that max_daily_executions was increased to 10."""
    assert EXECUTION_CONFIG['max_daily_executions'] == 10


def test_new_symbols_beta_values():
    """Test that new symbols have expected high beta values."""
    expected_betas = {
        '0GUSDT': 3.5,
        'KAIAUSDT': 2.8,
        'AXLUSDT': 2.5,
        'NILUSDT': 4.0,
        'FOGOUSDT': 3.8
    }
    
    for symbol, expected_beta in expected_betas.items():
        assert SYMBOLS[symbol]['beta_estimado'] == expected_beta


def test_playbook_instantiation():
    """Test that all new playbooks can be instantiated."""
    playbooks = [
        ('0GUSDT', ZeroGPlaybook),
        ('KAIAUSDT', KAIAPlaybook),
        ('AXLUSDT', AXLPlaybook),
        ('NILUSDT', NILPlaybook),
        ('FOGOUSDT', FOGOPlaybook)
    ]
    
    for expected_symbol, PlaybookClass in playbooks:
        pb = PlaybookClass()
        assert pb.symbol == expected_symbol
        assert pb.beta >= 2.0  # All are high beta
        assert 'low_cap' in pb.classificacao  # All are low cap


def test_playbook_methods():
    """Test that all playbooks implement required methods."""
    playbooks = [
        ZeroGPlaybook(), KAIAPlaybook(), AXLPlaybook(), 
        NILPlaybook(), FOGOPlaybook()
    ]
    
    context = {
        'fear_greed_value': 60,
        'social_sentiment': 0.6,
        'atr_pct': 3.0
    }
    
    for pb in playbooks:
        # Test get_confluence_adjustments
        conf_adj = pb.get_confluence_adjustments(context)
        assert isinstance(conf_adj, dict)
        
        # Test get_risk_adjustments
        risk_adj = pb.get_risk_adjustments(context)
        assert isinstance(risk_adj, dict)
        assert 'position_size_multiplier' in risk_adj
        assert 'stop_multiplier' in risk_adj
        assert 0 < risk_adj['position_size_multiplier'] <= 1.0  # Should be reduced
        assert risk_adj['stop_multiplier'] >= 1.0  # Wider stops
        
        # Test get_cycle_phase
        cycle = pb.get_cycle_phase(context)
        assert isinstance(cycle, str)
        assert len(cycle) > 0
        
        # Test should_trade
        should_trade = pb.should_trade('RISK_ON', 'LONG')
        assert isinstance(should_trade, bool)


def test_high_beta_playbooks_risk_only():
    """Test that high beta playbooks only trade in RISK_ON."""
    playbooks = [
        ZeroGPlaybook(), KAIAPlaybook(), AXLPlaybook(), 
        NILPlaybook(), FOGOPlaybook()
    ]
    
    for pb in playbooks:
        # Should NOT trade in RISK_OFF
        assert pb.should_trade('RISK_OFF', 'LONG') == False
        assert pb.should_trade('RISK_OFF', 'SHORT') == False
        
        # Should NOT trade with NEUTRO bias
        assert pb.should_trade('RISK_ON', 'NEUTRO') == False
        
        # Should trade in RISK_ON with directional bias
        assert pb.should_trade('RISK_ON', 'LONG') == True
        assert pb.should_trade('RISK_ON', 'SHORT') == True


def test_position_size_multipliers():
    """Test that position size multipliers are conservative for high beta."""
    expected_multipliers = {
        '0GUSDT': 0.4,
        'KAIAUSDT': 0.5,
        'AXLUSDT': 0.5,
        'NILUSDT': 0.35,  # Most conservative
        'FOGOUSDT': 0.4
    }
    
    playbooks = {
        '0GUSDT': ZeroGPlaybook(),
        'KAIAUSDT': KAIAPlaybook(),
        'AXLUSDT': AXLPlaybook(),
        'NILUSDT': NILPlaybook(),
        'FOGOUSDT': FOGOPlaybook()
    }
    
    context = {'fear_greed_value': 60, 'social_sentiment': 0.6}
    
    for symbol, expected_mult in expected_multipliers.items():
        pb = playbooks[symbol]
        risk_adj = pb.get_risk_adjustments(context)
        actual_mult = risk_adj['position_size_multiplier']
        assert actual_mult == expected_mult, \
            f"{symbol}: expected {expected_mult}, got {actual_mult}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
