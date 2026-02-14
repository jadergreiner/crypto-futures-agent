"""
Tests for Binance SDK integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from data.binance_client import BinanceClientFactory, create_binance_client
from data.collector import BinanceCollector
from data.sentiment_collector import SentimentCollector


class TestBinanceClientFactory:
    """Tests for BinanceClientFactory."""

    @patch('data.binance_client.BINANCE_API_KEY', 'test_key')
    @patch('data.binance_client.BINANCE_API_SECRET', 'test_secret')
    @patch('data.binance_client.BINANCE_PRIVATE_KEY_PATH', '')
    def test_factory_initialization_paper_mode(self):
        """Test factory initialization in paper mode."""
        factory = BinanceClientFactory(mode="paper")
        assert factory.mode == "paper"
        assert factory.api_key == "test_key"
        assert factory.api_secret == "test_secret"

    @patch('data.binance_client.BINANCE_API_KEY', 'test_key')
    @patch('data.binance_client.BINANCE_API_SECRET', 'test_secret')
    @patch('data.binance_client.BINANCE_PRIVATE_KEY_PATH', '')
    def test_factory_initialization_live_mode(self):
        """Test factory initialization in live mode."""
        factory = BinanceClientFactory(mode="live")
        assert factory.mode == "live"

    @patch('data.binance_client.BINANCE_API_KEY', 'test_key')
    @patch('data.binance_client.BINANCE_API_SECRET', 'test_secret')
    @patch('data.binance_client.BINANCE_PRIVATE_KEY_PATH', '')
    def test_get_rest_url_paper(self):
        """Test REST URL selection for paper mode."""
        factory = BinanceClientFactory(mode="paper")
        url = factory._get_rest_url()
        assert "testnet" in url.lower()

    @patch('data.binance_client.BINANCE_API_KEY', 'test_key')
    @patch('data.binance_client.BINANCE_API_SECRET', 'test_secret')
    @patch('data.binance_client.BINANCE_PRIVATE_KEY_PATH', '')
    def test_get_rest_url_live(self):
        """Test REST URL selection for live mode."""
        factory = BinanceClientFactory(mode="live")
        url = factory._get_rest_url()
        assert url  # Should return production URL from SDK

    @patch('data.binance_client.Path')
    @patch('data.binance_client.BINANCE_PRIVATE_KEY_PATH', '/path/to/key.pem')
    def test_use_ed25519_auth_with_existing_key(self, mock_path):
        """Test Ed25519 authentication detection with existing key."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        factory = BinanceClientFactory(mode="paper")
        assert factory._use_ed25519_auth() is True

    @patch('data.binance_client.Path')
    @patch('data.binance_client.BINANCE_PRIVATE_KEY_PATH', '/path/to/nonexistent.pem')
    def test_use_ed25519_auth_without_key(self, mock_path):
        """Test Ed25519 authentication detection without key file."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        factory = BinanceClientFactory(mode="paper")
        assert factory._use_ed25519_auth() is False


class TestBinanceCollector:
    """Tests for BinanceCollector."""

    def test_interval_mapping(self):
        """Test that all required intervals are mapped."""
        assert "1h" in BinanceCollector.INTERVAL_MAP
        assert "4h" in BinanceCollector.INTERVAL_MAP
        assert "1d" in BinanceCollector.INTERVAL_MAP
        assert "1m" in BinanceCollector.INTERVAL_MAP

    def test_interval_ms_mapping(self):
        """Test interval millisecond mappings."""
        assert BinanceCollector.INTERVAL_MS["1h"] == 60 * 60 * 1000
        assert BinanceCollector.INTERVAL_MS["4h"] == 4 * 60 * 60 * 1000
        assert BinanceCollector.INTERVAL_MS["1d"] == 24 * 60 * 60 * 1000

    def test_collector_initialization(self):
        """Test collector initialization with mock client."""
        mock_client = Mock()
        collector = BinanceCollector(mock_client)
        assert collector._client == mock_client

    def test_parse_klines_empty_data(self):
        """Test parsing empty klines data."""
        mock_client = Mock()
        collector = BinanceCollector(mock_client)
        df = collector._parse_klines([], "BTCUSDT")
        assert df.empty
        assert list(df.columns) == [
            'timestamp', 'symbol', 'open', 'high', 'low', 'close',
            'volume', 'quote_volume', 'trades_count'
        ]

    def test_parse_klines_raw_array(self):
        """Test parsing klines from raw array format."""
        mock_client = Mock()
        collector = BinanceCollector(mock_client)
        
        raw_data = [
            [1609459200000, '29000.0', '29500.0', '28800.0', '29200.0', '1000.0', 0, '29200000.0', 5000]
        ]
        
        df = collector._parse_klines(raw_data, "BTCUSDT")
        assert len(df) == 1
        assert df.iloc[0]['symbol'] == "BTCUSDT"
        assert df.iloc[0]['open'] == 29000.0
        assert df.iloc[0]['close'] == 29200.0

    def test_validate_data_empty(self):
        """Test validation of empty DataFrame."""
        mock_client = Mock()
        collector = BinanceCollector(mock_client)
        
        import pandas as pd
        df = pd.DataFrame()
        
        is_valid, issues = collector.validate_data(df, "1h")
        assert is_valid is False
        assert "empty" in issues[0].lower()

    def test_validate_data_with_nulls(self):
        """Test validation detects null values."""
        mock_client = Mock()
        collector = BinanceCollector(mock_client)
        
        import pandas as pd
        df = pd.DataFrame({
            'timestamp': [1609459200000],
            'symbol': ['BTCUSDT'],
            'open': [None],  # Null value
            'high': [29500.0],
            'low': [28800.0],
            'close': [29200.0],
            'volume': [1000.0],
            'quote_volume': [29200000.0],
            'trades_count': [5000],
        })
        
        is_valid, issues = collector.validate_data(df, "1h")
        assert is_valid is False
        assert any('null' in issue.lower() for issue in issues)

    def test_validate_data_with_negative_values(self):
        """Test validation detects negative values."""
        mock_client = Mock()
        collector = BinanceCollector(mock_client)
        
        import pandas as pd
        df = pd.DataFrame({
            'timestamp': [1609459200000],
            'symbol': ['BTCUSDT'],
            'open': [29000.0],
            'high': [29500.0],
            'low': [28800.0],
            'close': [-29200.0],  # Negative value
            'volume': [1000.0],
            'quote_volume': [29200000.0],
            'trades_count': [5000],
        })
        
        is_valid, issues = collector.validate_data(df, "1h")
        assert is_valid is False
        assert any('negative' in issue.lower() for issue in issues)


class TestSentimentCollector:
    """Tests for SentimentCollector."""

    def test_period_mapping_ls(self):
        """Test long/short ratio period mappings."""
        assert "4h" in SentimentCollector.PERIOD_MAP_LS
        assert "1h" in SentimentCollector.PERIOD_MAP_LS
        assert "1d" in SentimentCollector.PERIOD_MAP_LS

    def test_period_mapping_top_trader(self):
        """Test top trader period mappings."""
        assert "4h" in SentimentCollector.PERIOD_MAP_TOP_TRADER
        assert "1h" in SentimentCollector.PERIOD_MAP_TOP_TRADER
        assert "1d" in SentimentCollector.PERIOD_MAP_TOP_TRADER

    def test_collector_initialization(self):
        """Test sentiment collector initialization."""
        mock_client = Mock()
        collector = SentimentCollector(mock_client)
        assert collector._client == mock_client

    def test_fetch_all_sentiment_structure(self):
        """Test that fetch_all_sentiment returns proper structure."""
        mock_client = Mock()
        mock_client.rest_api.long_short_ratio = Mock(return_value=[])
        mock_client.rest_api.top_trader_long_short_ratio_positions = Mock(return_value=[])
        mock_client.rest_api.open_interest = Mock(return_value=None)
        mock_client.rest_api.get_funding_rate_history = Mock(return_value=[])
        mock_client.rest_api.taker_buy_sell_volume = Mock(return_value=[])
        
        collector = SentimentCollector(mock_client)
        result = collector.fetch_all_sentiment("BTCUSDT")
        
        assert 'timestamp' in result
        assert 'symbol' in result
        assert result['symbol'] == "BTCUSDT"
        assert 'long_short_ratio' in result
        assert 'open_interest' in result
        assert 'funding_rate' in result


def test_create_binance_client_helper():
    """Test the helper function for creating client."""
    with patch('data.binance_client.BinanceClientFactory') as mock_factory_class:
        mock_factory = Mock()
        mock_client = Mock()
        mock_factory.create_client.return_value = mock_client
        mock_factory_class.return_value = mock_factory
        
        result = create_binance_client("paper")
        
        mock_factory_class.assert_called_once_with(mode="paper")
        mock_factory.create_client.assert_called_once()
        assert result == mock_client
