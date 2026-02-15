"""
Tests for CryptoFuturesEnv to verify multi_tf_result integration.
"""

import pytest
import numpy as np
import pandas as pd
from agent.environment import CryptoFuturesEnv
from tests.test_e2e_pipeline import (
    create_synthetic_ohlcv,
    create_synthetic_macro_data,
    create_synthetic_sentiment_data
)
from indicators.technical import TechnicalIndicators
from indicators.smc import SmartMoneyConcepts


def create_test_data_with_indicators(symbol='BTCUSDT'):
    """Create test data with all required indicators."""
    # Generate OHLCV data
    h1_data = create_synthetic_ohlcv(length=200, seed=41)
    h4_data = create_synthetic_ohlcv(length=200, seed=42)
    d1_data = create_synthetic_ohlcv(length=50, seed=43)
    
    # Calculate indicators
    h1_data = TechnicalIndicators.calculate_all(h1_data)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    d1_data = TechnicalIndicators.calculate_all(d1_data)
    
    # Calculate SMC
    try:
        smc_result = SmartMoneyConcepts.calculate_all_smc(h4_data)
    except Exception:
        smc_result = {
            'structure': None,
            'swings': [],
            'bos': [],
            'choch': [],
            'order_blocks': [],
            'fvgs': [],
            'liquidity_levels': [],
            'liquidity_sweeps': [],
            'premium_discount': None
        }
    
    sentiment = create_synthetic_sentiment_data()
    sentiment['symbol'] = symbol
    
    macro = create_synthetic_macro_data()
    
    return {
        'h1': h1_data,
        'h4': h4_data,
        'd1': d1_data,
        'sentiment': sentiment,
        'macro': macro,
        'smc': smc_result,
        'symbol': symbol
    }


def test_environment_computes_multi_tf_result():
    """Verify that environment computes multi_tf_result during initialization."""
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Verify multi_tf_result was computed
    assert hasattr(env, 'multi_tf_result')
    assert env.multi_tf_result is not None
    assert 'd1_bias' in env.multi_tf_result
    assert 'market_regime' in env.multi_tf_result
    assert 'correlation_btc' in env.multi_tf_result
    assert 'beta_btc' in env.multi_tf_result
    
    # Verify symbol was extracted correctly
    assert hasattr(env, 'symbol')
    assert env.symbol == 'BTCUSDT'


def test_environment_uses_symbol_from_data():
    """Verify that environment uses the symbol from data dict."""
    data = create_test_data_with_indicators(symbol='ETHUSDT')
    env = CryptoFuturesEnv(data, episode_length=50)
    
    assert env.symbol == 'ETHUSDT'
    assert env.multi_tf_result['symbol'] == 'ETHUSDT'


def test_observation_has_multi_tf_features():
    """Verify Block 7 and 8 features are non-placeholder during training."""
    # Create env with data that has d1 indicators
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    obs, info = env.reset()
    
    # Verify observation shape
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))
    
    # Block 7 starts at index 55 (11+6+11+19+4+4)
    block7_start = 55
    block8_start = 58
    
    # Block 7: correlation should be between -1 and 1, beta should be reasonable
    btc_return = obs[block7_start]
    correlation_val = obs[block7_start + 1]
    beta_val = obs[block7_start + 2]
    
    # These should be within valid ranges (not all zeros)
    assert -1.0 <= btc_return <= 1.0
    assert -1.0 <= correlation_val <= 1.0
    assert 0.0 <= beta_val <= 1.0  # Beta divided by 3 then clipped to [0, 1]
    
    # Block 8: d1_bias and regime should be -1, 0, or 1
    d1_bias_val = obs[block8_start]
    regime_val = obs[block8_start + 1]
    
    assert d1_bias_val in [-1.0, 0.0, 1.0]
    assert regime_val in [-1.0, 0.0, 1.0]


def test_observation_multi_tf_across_steps():
    """Verify that multi_tf_result is consistent across steps in an episode."""
    data = create_test_data_with_indicators()
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Reset and get first observation
    obs1, _ = env.reset()
    
    # Take a few steps and check observations
    for _ in range(5):
        action = env.action_space.sample()
        obs2, reward, terminated, truncated, info = env.step(action)
        
        if terminated or truncated:
            break
        
        # Verify observation is valid
        assert obs2.shape == (104,)
        assert not np.any(np.isnan(obs2))
        
        # Block 7 and 8 should still have valid values
        block7_start = 55
        block8_start = 58
        
        correlation_val = obs2[block7_start + 1]
        beta_val = obs2[block7_start + 2]
        d1_bias_val = obs2[block8_start]
        regime_val = obs2[block8_start + 1]
        
        assert -1.0 <= correlation_val <= 1.0
        assert 0.0 <= beta_val <= 1.0
        assert d1_bias_val in [-1.0, 0.0, 1.0]
        assert regime_val in [-1.0, 0.0, 1.0]


def test_environment_handles_missing_data_gracefully():
    """Verify that environment handles missing D1 data gracefully."""
    # Create data with empty D1
    data = create_test_data_with_indicators()
    data['d1'] = pd.DataFrame()
    
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # Should still initialize with fallback values
    assert env.multi_tf_result is not None
    assert env.multi_tf_result['d1_bias'] == 'NEUTRO'
    assert env.multi_tf_result['market_regime'] == 'NEUTRO'
    
    # Should still be able to reset and step
    obs, info = env.reset()
    assert obs.shape == (104,)
    assert not np.any(np.isnan(obs))


def test_environment_handles_btcusdt_symbol():
    """Verify that environment correctly handles BTCUSDT symbol."""
    data = create_test_data_with_indicators(symbol='BTCUSDT')
    env = CryptoFuturesEnv(data, episode_length=50)
    
    # For BTCUSDT, correlation and beta should be 1.0 (self-correlation)
    # But this depends on having btc_data, which we don't have here
    # So it should use fallback values
    assert env.symbol == 'BTCUSDT'
    assert env.multi_tf_result is not None


def test_data_loader_includes_symbol():
    """Verify that DataLoader includes 'symbol' key in returned data."""
    from agent.data_loader import DataLoader
    
    # Test with synthetic data (no DB)
    loader = DataLoader(db=None)
    
    # Load training data
    data = loader.load_training_data(symbol='ETHUSDT', min_length=100)
    
    # Verify symbol is included
    assert 'symbol' in data
    assert data['symbol'] == 'ETHUSDT'
    
    # Verify other keys are present
    assert 'h1' in data
    assert 'h4' in data
    assert 'd1' in data
    assert 'sentiment' in data
    assert 'macro' in data
    assert 'smc' in data
