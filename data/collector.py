"""
Binance Futures API collector for OHLCV data.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from config.settings import (
    BINANCE_BASE_URL, API_RETRY_ATTEMPTS, API_RETRY_BACKOFF,
    KLINES_LIMIT, TIMEFRAMES, HISTORICAL_PERIODS
)

logger = logging.getLogger(__name__)


class BinanceCollector:
    """
    Collects OHLCV data from Binance Futures API.
    Implements retry logic with exponential backoff.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Binance collector.
        
        Args:
            api_key: Binance API key (optional for public endpoints)
            api_secret: Binance API secret (optional for public endpoints)
        """
        self.base_url = BINANCE_BASE_URL
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'X-MBX-APIKEY': api_key})
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response JSON data
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(API_RETRY_ATTEMPTS):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < API_RETRY_ATTEMPTS - 1:
                    backoff_time = API_RETRY_BACKOFF[attempt]
                    logger.warning(f"Request failed (attempt {attempt + 1}/{API_RETRY_ATTEMPTS}): {e}. "
                                 f"Retrying in {backoff_time}s...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Request failed after {API_RETRY_ATTEMPTS} attempts: {e}")
                    raise
    
    def fetch_klines(self, symbol: str, interval: str, limit: int = 500,
                     start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch kline/candlestick data from Binance.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            interval: Kline interval ("1h", "4h", "1d")
            limit: Number of klines to fetch (max 1500)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            List of OHLCV dictionaries
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, KLINES_LIMIT)
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        raw_data = self._make_request('/fapi/v1/klines', params)
        
        # Parse Binance kline format
        parsed_data = []
        for kline in raw_data:
            parsed_data.append({
                'timestamp': kline[0],
                'symbol': symbol,
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5]),
                'quote_volume': float(kline[7]),
                'trades_count': int(kline[8])
            })
        
        logger.info(f"Fetched {len(parsed_data)} {interval} candles for {symbol}")
        return parsed_data
    
    def fetch_historical(self, symbol: str, interval: str, days: int) -> List[Dict[str, Any]]:
        """
        Fetch historical data with pagination.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval ("1h", "4h", "1d")
            days: Number of days to fetch
            
        Returns:
            List of OHLCV dictionaries
        """
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_data = []
        current_start = start_time
        
        while current_start < end_time:
            chunk = self.fetch_klines(symbol, interval, limit=KLINES_LIMIT, 
                                     start_time=current_start, end_time=end_time)
            
            if not chunk:
                break
            
            all_data.extend(chunk)
            
            # Update start time for next iteration
            current_start = chunk[-1]['timestamp'] + 1
            
            # Respect rate limits
            time.sleep(0.5)
        
        # Validate data
        validated_data = self.validate_data(all_data)
        
        logger.info(f"Fetched {len(validated_data)} historical {interval} candles for {symbol} ({days} days)")
        return validated_data
    
    def validate_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate OHLCV data for gaps and integrity.
        
        Args:
            data: List of OHLCV dictionaries
            
        Returns:
            Validated data (gaps logged but NOT interpolated)
        """
        if not data:
            return data
        
        # Check for nulls
        for i, candle in enumerate(data):
            if any(v is None for k, v in candle.items() if k != 'symbol'):
                logger.warning(f"Null value found in candle {i}: {candle}")
        
        # Check for timestamp gaps
        if len(data) > 1:
            sorted_data = sorted(data, key=lambda x: x['timestamp'])
            
            for i in range(1, len(sorted_data)):
                prev_ts = sorted_data[i-1]['timestamp']
                curr_ts = sorted_data[i]['timestamp']
                
                # Expected time diff depends on interval (this is simplified)
                expected_diff = sorted_data[1]['timestamp'] - sorted_data[0]['timestamp']
                actual_diff = curr_ts - prev_ts
                
                if actual_diff > expected_diff * 1.5:  # Allow some tolerance
                    logger.warning(f"Gap detected between {prev_ts} and {curr_ts} for {sorted_data[i]['symbol']}")
            
            return sorted_data
        
        return data
    
    def fetch_all_symbols(self, symbols: List[str], interval: str, limit: int = 500) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch data for multiple symbols.
        
        Args:
            symbols: List of trading pair symbols
            interval: Kline interval
            limit: Number of klines per symbol
            
        Returns:
            Dictionary mapping symbol to OHLCV data
        """
        result = {}
        
        for symbol in symbols:
            try:
                data = self.fetch_klines(symbol, interval, limit)
                result[symbol] = data
                time.sleep(0.2)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                result[symbol] = []
        
        return result
    
    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get exchange information for symbol(s).
        
        Args:
            symbol: Optional specific symbol
            
        Returns:
            Exchange information
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self._make_request('/fapi/v1/exchangeInfo', params)
    
    def get_server_time(self) -> int:
        """
        Get Binance server time.
        
        Returns:
            Server timestamp in milliseconds
        """
        response = self._make_request('/fapi/v1/time')
        return response['serverTime']
