"""
End-to-end pipeline tests with synthetic data.
Tests the full flow without requiring real API keys.
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any

from indicators.technical import TechnicalIndicators
from indicators.smc import SmartMoneyConcepts
from indicators.multi_timeframe import MultiTimeframeAnalysis
from indicators.features import FeatureEngineer


def create_synthetic_ohlcv(
    length: int = 200,
    base_price: float = 30000.0,
    volatility: float = 100.0,
    trend: float = 0.0,
    seed: int = 42
) -> pd.DataFrame:
    """
    Creates synthetic OHLCV data with realistic structure.
    
    Args:
        length: Number of candles
        base_price: Starting price
        volatility: Price volatility
        trend: Trend direction (positive = upward, negative = downward)
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with OHLCV data
    """
    np.random.seed(seed)
    
    timestamps = [1700000000000 + i * 3600000 for i in range(length)]
    
    # Generate close prices with random walk + trend
    close_prices = [base_price]
    for i in range(1, length):
        change = np.random.randn() * volatility + trend
        new_price = close_prices[-1] + change
        close_prices.append(max(new_price, 100))  # Prevent negative prices
    
    close_prices = np.array(close_prices)
    
    # Generate OHLC from close
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = base_price
    
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.randn(length) * volatility * 0.3)
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.randn(length) * volatility * 0.3)
    
    volumes = np.abs(np.random.randn(length) * 1000 + 5000)
    
    data = {
        'timestamp': timestamps,
        'symbol': ['BTCUSDT'] * length,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes,
        'quote_volume': volumes * close_prices,
        'trades_count': (volumes / 10).astype(int),
    }
    
    return pd.DataFrame(data)


def create_synthetic_macro_data() -> Dict[str, Any]:
    """Creates synthetic macro data."""
    return {
        'timestamp': 1700000000000,
        'fear_greed_value': 55,
        'fear_greed_classification': 'Neutral',
        'btc_dominance': 48.5,
        'dxy': 100.0,
        'dxy_change_pct': -0.2,
        'stablecoin_exchange_flow_net': 1e9,
    }


def create_synthetic_sentiment_data() -> Dict[str, Any]:
    """Creates synthetic sentiment data."""
    return {
        'timestamp': 1700000000000,
        'symbol': 'BTCUSDT',
        'long_short_ratio': 1.15,
        'open_interest': 50000000.0,
        'open_interest_change_pct': 2.5,
        'funding_rate': 0.0001,
        'long_account': 0.53,
        'short_account': 0.47,
        'liquidations_long_vol': 1000000.0,
        'liquidations_short_vol': 800000.0,
    }


def test_create_synthetic_data():
    """Test that synthetic data generation works correctly."""
    df = create_synthetic_ohlcv(length=200)
    
    assert len(df) == 200
    assert 'timestamp' in df.columns
    assert 'open' in df.columns
    assert 'high' in df.columns
    assert 'low' in df.columns
    assert 'close' in df.columns
    assert 'volume' in df.columns
    
    # Verify OHLC relationships
    assert all(df['high'] >= df['low'])
    assert all(df['high'] >= df['close'])
    assert all(df['high'] >= df['open'])
    assert all(df['low'] <= df['close'])
    assert all(df['low'] <= df['open'])


def test_technical_indicators_on_synthetic_data():
    """Test that technical indicators can be calculated on synthetic data."""
    df = create_synthetic_ohlcv(length=700)  # Need enough for long EMAs
    
    result = TechnicalIndicators.calculate_all(df)
    
    # Check all indicators are present
    expected_cols = [
        'ema_17', 'ema_34', 'ema_72', 'ema_144', 'ema_305', 'ema_610',
        'rsi_14', 'macd_line', 'macd_signal', 'macd_histogram',
        'bb_upper', 'bb_middle', 'bb_lower', 'bb_bandwidth', 'bb_percent_b',
        'obv', 'atr_14', 'adx_14', 'di_plus', 'di_minus',
        'ema_alignment_score'
    ]
    
    for col in expected_cols:
        assert col in result.columns, f"Missing indicator: {col}"
    
    # Check that recent values are not NaN (after warm-up period)
    last_row = result.iloc[-1]
    assert not pd.isna(last_row['rsi_14'])
    assert not pd.isna(last_row['atr_14'])
    assert not pd.isna(last_row['adx_14'])


def test_smc_on_synthetic_data():
    """Test that SMC can be calculated on synthetic data."""
    df = create_synthetic_ohlcv(length=200)
    df = TechnicalIndicators.calculate_all(df)
    
    smc_result = SmartMoneyConcepts.calculate_all_smc(df)
    
    # Check all SMC components are present
    assert 'structure' in smc_result
    assert 'bos' in smc_result
    assert 'choch' in smc_result
    assert 'order_blocks' in smc_result
    assert 'fvgs' in smc_result
    assert 'liquidity_sweeps' in smc_result
    assert 'premium_discount' in smc_result
    
    # Check structure is not None
    assert smc_result['structure'] is not None


def test_multi_timeframe_analysis():
    """Test multi-timeframe analysis aggregation."""
    # Create synthetic data for different timeframes
    h1_data = create_synthetic_ohlcv(length=200, seed=41)
    h4_data = create_synthetic_ohlcv(length=200, seed=42)
    d1_data = create_synthetic_ohlcv(length=50, seed=43)
    btc_data = create_synthetic_ohlcv(length=200, seed=44)
    
    # Calculate indicators
    h1_data = TechnicalIndicators.calculate_all(h1_data)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    d1_data = TechnicalIndicators.calculate_all(d1_data)
    btc_data = TechnicalIndicators.calculate_all(btc_data)
    
    macro_data = create_synthetic_macro_data()
    
    # Run multi-timeframe analysis
    result = MultiTimeframeAnalysis.aggregate(
        h1_data=h1_data,
        h4_data=h4_data,
        d1_data=d1_data,
        symbol='ETHUSDT',
        macro_data=macro_data,
        btc_data=btc_data
    )
    
    # Check all fields are present
    assert 'symbol' in result
    assert 'd1_bias' in result
    assert 'market_regime' in result
    assert 'correlation_btc' in result
    assert 'beta_btc' in result
    
    # Check values are valid
    assert result['d1_bias'] in ['BULLISH', 'BEARISH', 'NEUTRO']
    assert result['market_regime'] in ['RISK_ON', 'RISK_OFF', 'NEUTRO']
    assert -1.0 <= result['correlation_btc'] <= 1.0
    assert result['beta_btc'] >= 0.0


def test_build_observation_without_multi_tf_result():
    """Test build_observation with placeholder values (backward compatibility)."""
    df = create_synthetic_ohlcv(length=200)
    df = TechnicalIndicators.calculate_all(df)
    
    smc_result = SmartMoneyConcepts.calculate_all_smc(df)
    sentiment = create_synthetic_sentiment_data()
    macro = create_synthetic_macro_data()
    
    observation = FeatureEngineer.build_observation(
        symbol='BTCUSDT',
        h1_data=df,
        h4_data=df,
        d1_data=df,
        sentiment=sentiment,
        macro=macro,
        smc=smc_result,
        position_state=None,
        multi_tf_result=None  # Not provided - should use placeholders
    )
    
    # Check observation shape
    assert len(observation) == 104
    
    # Check no NaN values
    assert not np.any(np.isnan(observation))
    
    # Check values are clipped
    assert np.all(observation >= -10)
    assert np.all(observation <= 10)
    
    # Check that blocks 7 and 8 have placeholder values
    # Block 7 features are at indices 55-57 (11+6+11+19+4+4)
    # They should be [0.0, 0.0, 1.0] (unnormalized placeholders)
    block7_start = 11 + 6 + 11 + 19 + 4 + 4  # 55
    assert observation[block7_start] == 0.0  # btc_return placeholder
    assert observation[block7_start + 1] == 0.0  # correlation placeholder
    # Beta placeholder is 1.0 (representing neutral beta)
    assert np.isclose(observation[block7_start + 2], 1.0)
    
    # Block 8 features are at indices 58-59 (after block 7)
    block8_start = block7_start + 3  # 58
    assert observation[block8_start] == 0.0  # d1_bias placeholder
    assert observation[block8_start + 1] == 0.0  # regime placeholder


def test_build_observation_with_multi_tf_result():
    """Test build_observation with real multi-timeframe values."""
    # Create data
    h1_data = create_synthetic_ohlcv(length=200, seed=41)
    h4_data = create_synthetic_ohlcv(length=200, seed=42)
    d1_data = create_synthetic_ohlcv(length=50, seed=43)
    btc_data = create_synthetic_ohlcv(length=200, seed=44)
    
    # Calculate indicators
    h1_data = TechnicalIndicators.calculate_all(h1_data)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    d1_data = TechnicalIndicators.calculate_all(d1_data)
    btc_data = TechnicalIndicators.calculate_all(btc_data)
    
    # Calculate SMC
    smc_result = SmartMoneyConcepts.calculate_all_smc(h1_data)
    
    sentiment = create_synthetic_sentiment_data()
    macro = create_synthetic_macro_data()
    
    # Multi-timeframe analysis
    multi_tf_result = MultiTimeframeAnalysis.aggregate(
        h1_data=h1_data,
        h4_data=h4_data,
        d1_data=d1_data,
        symbol='ETHUSDT',
        macro_data=macro,
        btc_data=btc_data
    )
    
    # Build observation with multi_tf_result
    observation = FeatureEngineer.build_observation(
        symbol='ETHUSDT',
        h1_data=h1_data,
        h4_data=h4_data,
        d1_data=d1_data,
        sentiment=sentiment,
        macro=macro,
        smc=smc_result,
        position_state=None,
        multi_tf_result=multi_tf_result
    )
    
    # Check observation shape
    assert len(observation) == 104
    
    # Check no NaN values
    assert not np.any(np.isnan(observation))
    
    # Check values are clipped
    assert np.all(observation >= -10)
    assert np.all(observation <= 10)
    
    # Check that blocks 7 and 8 have real values (not all zeros)
    block7_start = 11 + 6 + 11 + 19 + 4 + 4  # 55
    block8_start = block7_start + 3  # 58
    
    # Block 7: correlation should be between -1 and 1, beta should be reasonable
    # Beta is divided by 3 first, then clipped to [0, 1]
    correlation_val = observation[block7_start + 1]
    beta_val = observation[block7_start + 2]
    
    assert -1.0 <= correlation_val <= 1.0
    assert 0.0 <= beta_val <= 1.0  # Beta divided by 3 then clipped to [0, 1]
    
    # Block 8: d1_bias and regime should be -1, 0, or 1
    d1_bias_val = observation[block8_start]
    regime_val = observation[block8_start + 1]
    
    assert d1_bias_val in [-1.0, 0.0, 1.0]
    assert regime_val in [-1.0, 0.0, 1.0]


def test_full_pipeline_e2e():
    """
    End-to-end test of the full pipeline:
    Synthetic Data -> Technical Indicators -> SMC -> Multi-TF -> FeatureEngineer
    """
    # Step 1: Create synthetic data for all timeframes
    h1_data = create_synthetic_ohlcv(length=250, trend=5, seed=100)
    h4_data = create_synthetic_ohlcv(length=200, trend=5, seed=101)
    d1_data = create_synthetic_ohlcv(length=100, trend=10, seed=102)
    btc_d1_data = create_synthetic_ohlcv(length=100, trend=8, seed=103)
    
    # Step 2: Calculate technical indicators
    h1_data = TechnicalIndicators.calculate_all(h1_data)
    h4_data = TechnicalIndicators.calculate_all(h4_data)
    d1_data = TechnicalIndicators.calculate_all(d1_data)
    btc_d1_data = TechnicalIndicators.calculate_all(btc_d1_data)
    
    # Step 3: Calculate SMC structures
    smc_result = SmartMoneyConcepts.calculate_all_smc(h1_data)
    
    # Step 4: Create macro and sentiment data
    macro_data = create_synthetic_macro_data()
    sentiment_data = create_synthetic_sentiment_data()
    
    # Step 5: Multi-timeframe analysis
    multi_tf_result = MultiTimeframeAnalysis.aggregate(
        h1_data=h1_data,
        h4_data=h4_data,
        d1_data=d1_data,
        symbol='SOLUSDT',
        macro_data=macro_data,
        btc_data=btc_d1_data
    )
    
    # Step 6: Build observation
    observation = FeatureEngineer.build_observation(
        symbol='SOLUSDT',
        h1_data=h1_data,
        h4_data=h4_data,
        d1_data=d1_data,
        sentiment=sentiment_data,
        macro=macro_data,
        smc=smc_result,
        position_state=None,
        multi_tf_result=multi_tf_result
    )
    
    # Verify final observation
    assert len(observation) == 104, f"Expected 104 features, got {len(observation)}"
    assert not np.any(np.isnan(observation)), "Observation contains NaN values"
    assert np.all(observation >= -10) and np.all(observation <= 10), \
        "Observation values outside [-10, 10] range"
    
    # Verify all blocks have reasonable values
    # Block 1: Price (11 features)
    assert not np.all(observation[0:11] == 0)
    
    # Block 2: EMAs (6 features)
    assert not np.all(observation[11:17] == 0)
    
    # Block 3: Indicators (11 features)
    assert not np.all(observation[17:28] == 0)
    
    # Block 4: SMC (19 features) - might be zeros if no structures found
    # This is ok, SMC structures are not always present
    
    # Block 5: Sentiment (4 features)
    assert not np.all(observation[47:51] == 0)
    
    # Block 6: Macro (4 features)
    assert not np.all(observation[51:55] == 0)
    
    # Block 7: Correlation (3 features) - should have real values now
    assert not np.all(observation[55:58] == 0) or observation[57] != 0
    
    # Block 8: D1 Context (2 features) - should have real values now
    # May be 0 if NEUTRO, but should be valid
    assert observation[58] in [-1.0, 0.0, 1.0]
    assert observation[59] in [-1.0, 0.0, 1.0]
    
    # Block 9: Position (5 features) - should be zeros (no position)
    assert np.all(observation[60:65] == 0)


def test_multi_tf_result_bias_mapping():
    """Test that D1 bias is correctly mapped to numeric scores."""
    df = create_synthetic_ohlcv(length=200)
    df = TechnicalIndicators.calculate_all(df)
    smc = SmartMoneyConcepts.calculate_all_smc(df)
    
    # Test BULLISH mapping
    multi_tf_bullish = {
        'd1_bias': 'BULLISH',
        'market_regime': 'RISK_ON',
        'correlation_btc': 0.8,
        'beta_btc': 1.5
    }
    
    obs_bullish = FeatureEngineer.build_observation(
        symbol='BTCUSDT',
        h1_data=df,
        h4_data=df,
        d1_data=df,
        sentiment=create_synthetic_sentiment_data(),
        macro=create_synthetic_macro_data(),
        smc=smc,
        position_state=None,
        multi_tf_result=multi_tf_bullish
    )
    
    block8_start = 11 + 6 + 11 + 19 + 4 + 4 + 3  # 58
    assert obs_bullish[block8_start] == 1.0  # BULLISH -> 1.0
    assert obs_bullish[block8_start + 1] == 1.0  # RISK_ON -> 1.0
    
    # Test BEARISH mapping
    multi_tf_bearish = {
        'd1_bias': 'BEARISH',
        'market_regime': 'RISK_OFF',
        'correlation_btc': 0.8,
        'beta_btc': 1.5
    }
    
    obs_bearish = FeatureEngineer.build_observation(
        symbol='BTCUSDT',
        h1_data=df,
        h4_data=df,
        d1_data=df,
        sentiment=create_synthetic_sentiment_data(),
        macro=create_synthetic_macro_data(),
        smc=smc,
        position_state=None,
        multi_tf_result=multi_tf_bearish
    )
    
    assert obs_bearish[block8_start] == -1.0  # BEARISH -> -1.0
    assert obs_bearish[block8_start + 1] == -1.0  # RISK_OFF -> -1.0
    
    # Test NEUTRO mapping
    multi_tf_neutro = {
        'd1_bias': 'NEUTRO',
        'market_regime': 'NEUTRO',
        'correlation_btc': 0.0,
        'beta_btc': 1.0
    }
    
    obs_neutro = FeatureEngineer.build_observation(
        symbol='BTCUSDT',
        h1_data=df,
        h4_data=df,
        d1_data=df,
        sentiment=create_synthetic_sentiment_data(),
        macro=create_synthetic_macro_data(),
        smc=smc,
        position_state=None,
        multi_tf_result=multi_tf_neutro
    )
    
    assert obs_neutro[block8_start] == 0.0  # NEUTRO -> 0.0
    assert obs_neutro[block8_start + 1] == 0.0  # NEUTRO -> 0.0
