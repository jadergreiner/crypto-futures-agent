"""
Unit tests for MultiTimeframeAnalysis.
Tests the aggregate method which is the main public API.
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any

from indicators.multi_timeframe import MultiTimeframeAnalysis
from indicators.technical import TechnicalIndicators
from tests.test_e2e_pipeline import create_synthetic_ohlcv, create_synthetic_macro_data


class TestMultiTimeframeAnalysis:
    """Tests for MultiTimeframeAnalysis class."""
    
    @pytest.fixture
    def mta(self):
        """Create a MultiTimeframeAnalysis instance."""
        return MultiTimeframeAnalysis()
    
    def create_data_with_indicators(self, length=100, base_price=30000.0, trend=0.0, seed=42):
        """Helper to create OHLCV data with indicators calculated."""
        ohlcv = create_synthetic_ohlcv(length=length, base_price=base_price, trend=trend, seed=seed)
        # Calculate indicators
        indicators = TechnicalIndicators.calculate_all(ohlcv)
        return indicators
    
    def test_aggregate_returns_dict(self, mta):
        """Test that aggregate returns a dictionary with all expected keys."""
        # Create synthetic data with indicators
        symbol_d1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=42)
        symbol_h4 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=43)
        symbol_h1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=44)
        btc_d1 = self.create_data_with_indicators(length=100, base_price=50000.0, seed=45)
        btc_h4 = self.create_data_with_indicators(length=100, base_price=50000.0, seed=46)
        macro_data = create_synthetic_macro_data()
        
        result = mta.aggregate(
            h1_data=symbol_h1,
            h4_data=symbol_h4,
            d1_data=symbol_d1,
            symbol="ETHUSDT",
            macro_data=macro_data,
            btc_data=btc_h4
        )
        
        # Check that result is a dictionary
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        
        # Check for all expected keys
        expected_keys = ['symbol', 'd1_bias', 'market_regime', 'correlation_btc', 'beta_btc']
        for key in expected_keys:
            assert key in result, f"Missing key '{key}' in result"
    
    def test_aggregate_d1_bias_values(self, mta):
        """Test that aggregate returns valid d1_bias values."""
        symbol_d1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=42)
        symbol_h4 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=43)
        symbol_h1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=44)
        macro_data = create_synthetic_macro_data()
        
        result = mta.aggregate(
            h1_data=symbol_h1,
            h4_data=symbol_h4,
            d1_data=symbol_d1,
            symbol="ETHUSDT",
            macro_data=macro_data,
            btc_data=None
        )
        
        assert result['d1_bias'] in ['BULLISH', 'BEARISH', 'NEUTRO'], \
            f"Invalid d1_bias: {result['d1_bias']}"
    
    def test_aggregate_market_regime_values(self, mta):
        """Test that aggregate returns valid market_regime values."""
        symbol_d1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=42)
        symbol_h4 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=43)
        symbol_h1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=44)
        macro_data = create_synthetic_macro_data()
        
        result = mta.aggregate(
            h1_data=symbol_h1,
            h4_data=symbol_h4,
            d1_data=symbol_d1,
            symbol="ETHUSDT",
            macro_data=macro_data,
            btc_data=None
        )
        
        assert result['market_regime'] in ['RISK_ON', 'RISK_OFF', 'NEUTRO'], \
            f"Invalid market_regime: {result['market_regime']}"
    
    def test_aggregate_correlation_range(self, mta):
        """Test that aggregate returns correlation in valid range."""
        symbol_d1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=42)
        symbol_h4 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=43)
        symbol_h1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=44)
        btc_h4 = self.create_data_with_indicators(length=100, base_price=50000.0, seed=45)
        macro_data = create_synthetic_macro_data()
        
        result = mta.aggregate(
            h1_data=symbol_h1,
            h4_data=symbol_h4,
            d1_data=symbol_d1,
            symbol="ETHUSDT",
            macro_data=macro_data,
            btc_data=btc_h4
        )
        
        correlation = result['correlation_btc']
        assert isinstance(correlation, (int, float)), \
            f"correlation_btc should be numeric, got {type(correlation)}"
        assert -1.0 <= correlation <= 1.0, \
            f"correlation_btc should be in [-1, 1], got {correlation}"
    
    def test_aggregate_beta_positive(self, mta):
        """Testa que aggregate retorna beta numérico (pode ser negativo)."""
        symbol_d1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=42)
        symbol_h4 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=43)
        symbol_h1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=44)
        btc_h4 = self.create_data_with_indicators(length=100, base_price=50000.0, seed=45)
        macro_data = create_synthetic_macro_data()
        
        result = mta.aggregate(
            h1_data=symbol_h1,
            h4_data=symbol_h4,
            d1_data=symbol_d1,
            symbol="ETHUSDT",
            macro_data=macro_data,
            btc_data=btc_h4
        )
        
        beta = result['beta_btc']
        assert isinstance(beta, (int, float)), \
            f"beta_btc deve ser numérico, recebeu {type(beta)}"
        # Beta pode ser negativo quando há correlação negativa
        assert -5.0 <= beta <= 5.0, \
            f"beta_btc deve estar em um range razoável, recebeu {beta}"
    
    def test_aggregate_with_none_symbol_data(self, mta):
        """Test aggregate with empty symbol data returns defaults."""
        empty_df = pd.DataFrame()
        symbol_h4 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=43)
        symbol_h1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=44)
        macro_data = create_synthetic_macro_data()
        
        result = mta.aggregate(
            h1_data=symbol_h1,
            h4_data=symbol_h4,
            d1_data=empty_df,
            symbol="ETHUSDT",
            macro_data=macro_data,
            btc_data=None
        )
        
        # Should return NEUTRO for d1_bias when no D1 data
        assert result['d1_bias'] == 'NEUTRO', \
            f"Expected NEUTRO for empty D1 data, got {result['d1_bias']}"
    
    def test_aggregate_with_none_macro_data(self, mta):
        """Test aggregate with None macro data returns defaults."""
        symbol_d1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=42)
        symbol_h4 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=43)
        symbol_h1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=44)
        
        result = mta.aggregate(
            h1_data=symbol_h1,
            h4_data=symbol_h4,
            d1_data=symbol_d1,
            symbol="ETHUSDT",
            macro_data=None,
            btc_data=None
        )
        
        # Should return NEUTRO for market_regime when no macro data
        assert result['market_regime'] == 'NEUTRO', \
            f"Expected NEUTRO for None macro data, got {result['market_regime']}"
    
    def test_aggregate_btc_symbol(self, mta):
        """Test aggregate with BTCUSDT symbol (special case)."""
        btc_d1 = self.create_data_with_indicators(length=100, base_price=50000.0, seed=42)
        btc_h4 = self.create_data_with_indicators(length=100, base_price=50000.0, seed=43)
        btc_h1 = self.create_data_with_indicators(length=100, base_price=50000.0, seed=44)
        macro_data = create_synthetic_macro_data()
        
        result = mta.aggregate(
            h1_data=btc_h1,
            h4_data=btc_h4,
            d1_data=btc_d1,
            symbol="BTCUSDT",
            macro_data=macro_data,
            btc_data=btc_h4
        )
        
        # For BTCUSDT, correlation should be 1.0 (perfect correlation with itself)
        # and beta should be 1.0
        assert result['correlation_btc'] == pytest.approx(1.0, abs=0.01), \
            f"BTCUSDT correlation should be 1.0, got {result['correlation_btc']}"
        assert result['beta_btc'] == pytest.approx(1.0, abs=0.01), \
            f"BTCUSDT beta should be 1.0, got {result['beta_btc']}"
    
    def test_aggregate_without_btc_data(self, mta):
        """Test that aggregate works without BTC data (returns default correlation/beta)."""
        symbol_d1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=42)
        symbol_h4 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=43)
        symbol_h1 = self.create_data_with_indicators(length=100, base_price=30000.0, seed=44)
        macro_data = create_synthetic_macro_data()
        
        result = mta.aggregate(
            h1_data=symbol_h1,
            h4_data=symbol_h4,
            d1_data=symbol_d1,
            symbol="ETHUSDT",
            macro_data=macro_data,
            btc_data=None
        )
        
        # Without BTC data, correlation should be 0.0 and beta should be 1.0 (defaults)
        assert result['correlation_btc'] == 0.0, \
            f"Expected correlation 0.0 without BTC data, got {result['correlation_btc']}"
        assert result['beta_btc'] == 1.0, \
            f"Expected beta 1.0 without BTC data, got {result['beta_btc']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

