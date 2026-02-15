"""
Unit tests for FeatureEngineer.
Tests the build_observation and get_feature_names methods.
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any

from indicators.features import FeatureEngineer
from tests.test_e2e_pipeline import create_synthetic_ohlcv, create_synthetic_sentiment_data, create_synthetic_macro_data


class TestFeatureEngineer:
    """Tests for FeatureEngineer class."""
    
    def test_get_feature_names_count(self):
        """Test that get_feature_names returns exactly 104 names."""
        names = FeatureEngineer.get_feature_names()
        assert len(names) == 104, f"Expected 104 feature names, got {len(names)}"
    
    def test_get_feature_names_no_duplicates(self):
        """Test that feature names are unique."""
        names = FeatureEngineer.get_feature_names()
        unique_names = set(names)
        assert len(unique_names) == len(names), "Feature names contain duplicates"
    
    def test_build_observation_with_none_data(self):
        """Test build_observation with all None data returns 104 zeros."""
        obs = FeatureEngineer.build_observation(
            symbol="BTCUSDT",
            h1_data=None,
            h4_data=None,
            d1_data=None,
            sentiment=None,
            macro=None,
            smc=None,
            position_state=None,
            multi_tf_result=None
        )
        
        assert obs.shape == (104,), f"Expected shape (104,), got {obs.shape}"
        assert obs.dtype == np.float32, f"Expected dtype float32, got {obs.dtype}"
        # Most features should be zeros or default values when no data
        assert np.all(np.abs(obs) <= 10), "Observation values should be clipped to [-10, 10]"
    
    def test_build_observation_with_synthetic_data(self):
        """Test build_observation with synthetic data returns 104 features without NaN."""
        # Create synthetic data
        h1_data = create_synthetic_ohlcv(length=200, base_price=30000.0, seed=42)
        h4_data = create_synthetic_ohlcv(length=200, base_price=30000.0, seed=43)
        d1_data = create_synthetic_ohlcv(length=200, base_price=30000.0, seed=44)
        sentiment = create_synthetic_sentiment_data()
        macro = create_synthetic_macro_data()
        
        obs = FeatureEngineer.build_observation(
            symbol="BTCUSDT",
            h1_data=h1_data,
            h4_data=h4_data,
            d1_data=d1_data,
            sentiment=sentiment,
            macro=macro,
            smc=None,  # SMC can be None for this test
            position_state=None,
            multi_tf_result=None
        )
        
        assert obs.shape == (104,), f"Expected shape (104,), got {obs.shape}"
        assert obs.dtype == np.float32, f"Expected dtype float32, got {obs.dtype}"
        assert not np.any(np.isnan(obs)), "Observation contains NaN values"
        assert not np.any(np.isinf(obs)), "Observation contains infinite values"
    
    def test_build_observation_with_multi_tf_result(self):
        """Test that Block 7 and Block 8 use real values from multi_tf_result."""
        # Create minimal data
        d1_data = create_synthetic_ohlcv(length=50, base_price=30000.0, seed=42)
        
        # Create multi_tf_result with known values
        multi_tf_result = {
            'd1_bias': 'BULLISH',
            'market_regime': 'RISK_ON',
            'correlation_btc': 0.75,
            'beta_btc': 1.5
        }
        
        obs = FeatureEngineer.build_observation(
            symbol="BTCUSDT",
            h1_data=None,
            h4_data=None,
            d1_data=d1_data,
            sentiment=None,
            macro=None,
            smc=None,
            position_state=None,
            multi_tf_result=multi_tf_result
        )
        
        # Block 7: btc_return, correlation, beta (indices 55-57)
        # correlation should be 0.75 (clipped)
        assert obs[56] == pytest.approx(0.75, abs=0.01), f"correlation feature should be 0.75, got {obs[56]}"
        
        # beta should be 1.5/3 = 0.5 (normalized by dividing by 3)
        assert obs[57] == pytest.approx(0.5, abs=0.01), f"beta feature should be 0.5, got {obs[57]}"
        
        # Block 8: d1_bias, market_regime (indices 58-59)
        # BULLISH should map to 1.0
        assert obs[58] == pytest.approx(1.0, abs=0.01), f"d1_bias should be 1.0, got {obs[58]}"
        
        # RISK_ON should map to 1.0
        assert obs[59] == pytest.approx(1.0, abs=0.01), f"market_regime should be 1.0, got {obs[59]}"
    
    def test_build_observation_block7_bearish_risk_off(self):
        """Test Block 7 and 8 with BEARISH and RISK_OFF values."""
        multi_tf_result = {
            'd1_bias': 'BEARISH',
            'market_regime': 'RISK_OFF',
            'correlation_btc': -0.5,
            'beta_btc': 2.0
        }
        
        obs = FeatureEngineer.build_observation(
            symbol="ETHUSDT",
            h1_data=None,
            h4_data=None,
            d1_data=None,
            sentiment=None,
            macro=None,
            smc=None,
            position_state=None,
            multi_tf_result=multi_tf_result
        )
        
        # correlation should be -0.5
        assert obs[56] == pytest.approx(-0.5, abs=0.01), f"correlation should be -0.5, got {obs[56]}"
        
        # beta should be 2.0/3 = 0.667 (normalized)
        assert obs[57] == pytest.approx(0.667, abs=0.01), f"beta should be ~0.667, got {obs[57]}"
        
        # BEARISH should map to -1.0
        assert obs[58] == pytest.approx(-1.0, abs=0.01), f"d1_bias should be -1.0, got {obs[58]}"
        
        # RISK_OFF should map to -1.0
        assert obs[59] == pytest.approx(-1.0, abs=0.01), f"market_regime should be -1.0, got {obs[59]}"
    
    def test_build_observation_block7_neutro(self):
        """Test Block 7 and 8 with NEUTRO values."""
        multi_tf_result = {
            'd1_bias': 'NEUTRO',
            'market_regime': 'NEUTRO',
            'correlation_btc': 0.0,
            'beta_btc': 1.0
        }
        
        obs = FeatureEngineer.build_observation(
            symbol="SOLUSDT",
            h1_data=None,
            h4_data=None,
            d1_data=None,
            sentiment=None,
            macro=None,
            smc=None,
            position_state=None,
            multi_tf_result=multi_tf_result
        )
        
        # All should be around 0.0 or neutral values
        assert obs[56] == pytest.approx(0.0, abs=0.01), f"correlation should be 0.0, got {obs[56]}"
        assert obs[57] == pytest.approx(0.333, abs=0.01), f"beta should be ~0.333, got {obs[57]}"
        assert obs[58] == pytest.approx(0.0, abs=0.01), f"d1_bias should be 0.0, got {obs[58]}"
        assert obs[59] == pytest.approx(0.0, abs=0.01), f"market_regime should be 0.0, got {obs[59]}"
    
    def test_build_observation_without_multi_tf_result(self):
        """Test that Block 7 and 8 use default values when multi_tf_result is None."""
        obs = FeatureEngineer.build_observation(
            symbol="BTCUSDT",
            h1_data=None,
            h4_data=None,
            d1_data=None,
            sentiment=None,
            macro=None,
            smc=None,
            position_state=None,
            multi_tf_result=None
        )
        
        # Block 7 defaults: [0.0, 0.0, 1.0] according to code
        assert obs[55] == pytest.approx(0.0, abs=0.01), f"btc_return default should be 0.0, got {obs[55]}"
        assert obs[56] == pytest.approx(0.0, abs=0.01), f"correlation default should be 0.0, got {obs[56]}"
        # Beta default is 1.0 (not normalized when multi_tf_result is None)
        assert obs[57] == pytest.approx(1.0, abs=0.01), f"beta default should be 1.0, got {obs[57]}"
        
        # Block 8 defaults: [0.0, 0.0]
        assert obs[58] == pytest.approx(0.0, abs=0.01), f"d1_bias default should be 0.0, got {obs[58]}"
        assert obs[59] == pytest.approx(0.0, abs=0.01), f"market_regime default should be 0.0, got {obs[59]}"
    
    def test_build_observation_with_position_state(self):
        """Test Block 9 (position) features."""
        position_state = {
            'has_position': True,
            'direction': 'LONG',
            'pnl_pct': 5.0,
            'time_in_position_hours': 12,
            'stop_distance_pct': 2.0,
            'tp_distance_pct': 6.0
        }
        
        obs = FeatureEngineer.build_observation(
            symbol="BTCUSDT",
            h1_data=None,
            h4_data=None,
            d1_data=None,
            sentiment=None,
            macro=None,
            smc=None,
            position_state=position_state,
            multi_tf_result=None
        )
        
        # Block 9: position_direction, position_pnl, position_time, stop_distance, tp_distance (indices 60-64)
        # direction LONG = 1.0
        assert obs[60] == pytest.approx(1.0, abs=0.01), f"position_direction should be 1.0, got {obs[60]}"
        
        # pnl_pct 5.0 clipped and normalized
        assert obs[61] != 0.0, f"position_pnl should not be 0.0, got {obs[61]}"
        
        # time_in_position normalized
        assert obs[62] > 0.0, f"position_time should be > 0.0, got {obs[62]}"
    
    def test_observation_clipping(self):
        """Test that observation values are clipped to [-10, 10]."""
        # Create data that might produce extreme values
        obs = FeatureEngineer.build_observation(
            symbol="BTCUSDT",
            h1_data=None,
            h4_data=None,
            d1_data=None,
            sentiment=None,
            macro=None,
            smc=None,
            position_state=None,
            multi_tf_result=None
        )
        
        assert np.all(obs >= -10), "Some observations are below -10"
        assert np.all(obs <= 10), "Some observations are above 10"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
