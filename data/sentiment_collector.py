"""
Sentiment data collector from Binance Futures API.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from config.settings import (
    BINANCE_BASE_URL, API_RETRY_ATTEMPTS, API_RETRY_BACKOFF,
    SENTIMENT_LIMIT, FORCE_ORDERS_LIMIT
)

logger = logging.getLogger(__name__)


class SentimentCollector:
    """
    Collects market sentiment data from Binance Futures API.
    Includes Long/Short Ratio, Open Interest, Funding Rate, and Liquidations.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize sentiment collector."""
        self.base_url = BINANCE_BASE_URL
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'X-MBX-APIKEY': api_key})
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(API_RETRY_ATTEMPTS):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < API_RETRY_ATTEMPTS - 1:
                    backoff_time = API_RETRY_BACKOFF[attempt]
                    logger.warning(f"Sentiment request failed (attempt {attempt + 1}): {e}. "
                                 f"Retrying in {backoff_time}s...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Sentiment request failed after {API_RETRY_ATTEMPTS} attempts: {e}")
                    raise
    
    def fetch_long_short_ratio(self, symbol: str, period: str = "4h", limit: int = 1) -> List[Dict[str, Any]]:
        """
        Fetch global long/short account ratio.
        
        Args:
            symbol: Trading pair symbol
            period: Period ("5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d")
            limit: Number of data points
            
        Returns:
            List of long/short ratio data
        """
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        
        try:
            data = self._make_request('/futures/data/globalLongShortAccountRatio', params)
            logger.debug(f"Fetched long/short ratio for {symbol}")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch long/short ratio for {symbol}: {e}")
            return []
    
    def fetch_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current open interest.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Open interest data
        """
        params = {'symbol': symbol}
        
        try:
            data = self._make_request('/fapi/v1/openInterest', params)
            logger.debug(f"Fetched open interest for {symbol}")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch open interest for {symbol}: {e}")
            return {}
    
    def fetch_open_interest_hist(self, symbol: str, period: str = "4h", limit: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch historical open interest.
        
        Args:
            symbol: Trading pair symbol
            period: Period ("5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d")
            limit: Number of data points
            
        Returns:
            List of historical OI data
        """
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        
        try:
            data = self._make_request('/futures/data/openInterestHist', params)
            logger.debug(f"Fetched OI history for {symbol}")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch OI history for {symbol}: {e}")
            return []
    
    def fetch_funding_rate(self, symbol: str, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Fetch funding rate.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of records
            
        Returns:
            List of funding rate data
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        try:
            data = self._make_request('/fapi/v1/fundingRate', params)
            logger.debug(f"Fetched funding rate for {symbol}")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            return []
    
    def fetch_force_orders(self, symbol: str, limit: int = FORCE_ORDERS_LIMIT,
                          start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch forced liquidation orders.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of records
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            List of liquidation data
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        try:
            data = self._make_request('/fapi/v1/allForceOrders', params)
            logger.debug(f"Fetched {len(data)} liquidations for {symbol}")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch liquidations for {symbol}: {e}")
            return []
    
    def aggregate_liquidations(self, liquidations: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Aggregate liquidations by side.
        
        Args:
            liquidations: List of liquidation orders
            
        Returns:
            Aggregated liquidation volumes
        """
        long_vol = 0.0
        short_vol = 0.0
        
        for liq in liquidations:
            qty = float(liq.get('origQty', 0))
            side = liq.get('side', '')
            
            if side == 'SELL':  # Long liquidation
                long_vol += qty
            elif side == 'BUY':  # Short liquidation
                short_vol += qty
        
        return {
            'liquidations_long_vol': long_vol,
            'liquidations_short_vol': short_vol,
            'liquidations_total_vol': long_vol + short_vol
        }
    
    def fetch_all_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch all sentiment data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Consolidated sentiment data
        """
        result = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'symbol': symbol,
            'long_short_ratio': None,
            'open_interest': None,
            'open_interest_change_pct': None,
            'funding_rate': None,
            'liquidations_long_vol': 0.0,
            'liquidations_short_vol': 0.0,
            'liquidations_total_vol': 0.0
        }
        
        try:
            # Long/Short Ratio
            ls_data = self.fetch_long_short_ratio(symbol)
            if ls_data:
                result['long_short_ratio'] = float(ls_data[0].get('longShortRatio', 0))
            
            # Open Interest
            oi_data = self.fetch_open_interest(symbol)
            if oi_data:
                result['open_interest'] = float(oi_data.get('openInterest', 0))
            
            # OI Change
            oi_hist = self.fetch_open_interest_hist(symbol, period="4h", limit=2)
            if len(oi_hist) >= 2:
                current_oi = float(oi_hist[-1].get('sumOpenInterest', 0))
                prev_oi = float(oi_hist[-2].get('sumOpenInterest', 1))
                if prev_oi > 0:
                    result['open_interest_change_pct'] = ((current_oi - prev_oi) / prev_oi) * 100
            
            # Funding Rate
            funding_data = self.fetch_funding_rate(symbol)
            if funding_data:
                result['funding_rate'] = float(funding_data[0].get('fundingRate', 0))
            
            # Liquidations (last 4 hours)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (4 * 60 * 60 * 1000)
            liquidations = self.fetch_force_orders(symbol, start_time=start_time, end_time=end_time)
            liq_summary = self.aggregate_liquidations(liquidations)
            result.update(liq_summary)
            
            logger.info(f"Collected all sentiment data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error collecting sentiment for {symbol}: {e}")
        
        return result
