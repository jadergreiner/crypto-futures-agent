"""
Sentiment data collector from Binance Futures API using official SDK.
"""

from __future__ import annotations

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import (
    DerivativesTradingUsdsFutures,
)
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    LongShortRatioPeriodEnum,
    TopTraderLongShortRatioPositionsPeriodEnum,
)
from config.settings import (
    API_MAX_RETRIES,
    API_RETRY_DELAYS,
)

logger = logging.getLogger(__name__)


class SentimentCollector:
    """
    Collects market sentiment data from Binance Futures API using official SDK.
    Includes Long/Short Ratio, Open Interest, Funding Rate, and Taker Buy/Sell Volume.
    """
    
    # Map period strings to SDK enum values for Long/Short Ratio
    PERIOD_MAP_LS = {
        "5m": LongShortRatioPeriodEnum.PERIOD_5m,
        "15m": LongShortRatioPeriodEnum.PERIOD_15m,
        "30m": LongShortRatioPeriodEnum.PERIOD_30m,
        "1h": LongShortRatioPeriodEnum.PERIOD_1h,
        "2h": LongShortRatioPeriodEnum.PERIOD_2h,
        "4h": LongShortRatioPeriodEnum.PERIOD_4h,
        "6h": LongShortRatioPeriodEnum.PERIOD_6h,
        "12h": LongShortRatioPeriodEnum.PERIOD_12h,
        "1d": LongShortRatioPeriodEnum.PERIOD_1d,
    }
    
    # Map period strings to SDK enum values for Top Trader Ratio
    PERIOD_MAP_TOP_TRADER = {
        "5m": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_5m,
        "15m": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_15m,
        "30m": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_30m,
        "1h": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_1h,
        "2h": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_2h,
        "4h": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_4h,
        "6h": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_6h,
        "12h": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_12h,
        "1d": TopTraderLongShortRatioPositionsPeriodEnum.PERIOD_1d,
    }
    
    def __init__(self, client: DerivativesTradingUsdsFutures):
        """
        Initialize sentiment collector with SDK client.
        
        Args:
            client: Configured DerivativesTradingUsdsFutures client
        """
        self._client = client
        logger.info("SentimentCollector initialized with SDK client")
    
    def _retry_request(self, func, *args, **kwargs):
        """
        Execute request with retry logic and exponential backoff.
        
        Args:
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(API_MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < API_MAX_RETRIES - 1:
                    backoff_time = API_RETRY_DELAYS[attempt]
                    logger.warning(
                        f"Sentiment request failed (attempt {attempt + 1}/{API_MAX_RETRIES}): {e}. "
                        f"Retrying in {backoff_time}s..."
                    )
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Sentiment request failed after {API_MAX_RETRIES} attempts: {e}")
                    raise
    
    def _extract_data(self, response):
        """
        Extrai dados do wrapper ApiResponse do SDK.
        
        O SDK Binance encapsula respostas em um objeto ApiResponse.
        Este método extrai com segurança o payload de dados real.
        
        Args:
            response: Resposta bruta do SDK (ApiResponse ou dados diretos)
            
        Returns:
            Os dados reais (list, dict, etc.)
        """
        if response is None:
            return None
        
        # ApiResponse tem um atributo .data contendo o payload real
        if hasattr(response, 'data'):
            return response.data
        
        # Se já são os dados brutos (list, dict), retorna como está
        return response
    
    def fetch_long_short_ratio(
        self,
        symbol: str,
        period: str = "4h",
        limit: int = 1,
    ) -> Dict[str, Any]:
        """
        Fetch global long/short account ratio.
        
        Args:
            symbol: Trading pair symbol
            period: Period ("5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d")
            limit: Number of data points
            
        Returns:
            Dict with long_short_ratio, long_account, short_account, timestamp
        """
        period_enum = self.PERIOD_MAP_LS.get(period)
        if not period_enum:
            raise ValueError(f"Invalid period: {period}. Must be one of {list(self.PERIOD_MAP_LS.keys())}")
        
        try:
            def _fetch():
                return self._client.rest_api.long_short_ratio(
                    symbol=symbol,
                    period=period_enum,
                    limit=limit,
                )
            
            response = self._retry_request(_fetch)
            data = self._extract_data(response)
            
            if data:
                # Se é uma lista, pegar o primeiro item
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                else:
                    latest = data
                
                result = {
                    'long_short_ratio': float(getattr(latest, 'long_short_ratio', 0)),
                    'long_account': float(getattr(latest, 'long_account', 0)),
                    'short_account': float(getattr(latest, 'short_account', 0)),
                    'timestamp': int(getattr(latest, 'timestamp', 0)),
                }
                logger.debug(f"Fetched long/short ratio for {symbol}: {result['long_short_ratio']}")
                return result
            
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch long/short ratio for {symbol}: {e}")
            return {}
    
    def fetch_top_trader_ls_ratio(
        self,
        symbol: str,
        period: str = "4h",
        limit: int = 1,
    ) -> Dict[str, Any]:
        """
        Fetch top trader long/short ratio (positions).
        
        Args:
            symbol: Trading pair symbol
            period: Period ("5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d")
            limit: Number of data points
            
        Returns:
            Dict with top trader ratio data
        """
        period_enum = self.PERIOD_MAP_TOP_TRADER.get(period)
        if not period_enum:
            raise ValueError(f"Invalid period: {period}. Must be one of {list(self.PERIOD_MAP_TOP_TRADER.keys())}")
        
        try:
            def _fetch():
                return self._client.rest_api.top_trader_long_short_ratio_positions(
                    symbol=symbol,
                    period=period_enum,
                    limit=limit,
                )
            
            response = self._retry_request(_fetch)
            data = self._extract_data(response)
            
            if data:
                # Se é uma lista, pegar o primeiro item
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                else:
                    latest = data
                
                result = {
                    'top_long_short_ratio': float(getattr(latest, 'long_short_ratio', 0)),
                    'top_long_account': float(getattr(latest, 'long_account', 0)),
                    'top_short_account': float(getattr(latest, 'short_account', 0)),
                    'timestamp': int(getattr(latest, 'timestamp', 0)),
                }
                logger.debug(f"Fetched top trader L/S ratio for {symbol}: {result['top_long_short_ratio']}")
                return result
            
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch top trader L/S ratio for {symbol}: {e}")
            return {}
    
    def fetch_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current open interest.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with open interest data
        """
        try:
            def _fetch():
                return self._client.rest_api.open_interest(symbol=symbol)
            
            response = self._retry_request(_fetch)
            data = self._extract_data(response)
            
            if data:
                result = {
                    'open_interest': float(getattr(data, 'open_interest', 0)),
                    'symbol': getattr(data, 'symbol', symbol),
                    'timestamp': int(getattr(data, 'time', 0)),
                }
                logger.debug(f"Fetched open interest for {symbol}: {result['open_interest']}")
                return result
            
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch open interest for {symbol}: {e}")
            return {}
    
    def fetch_funding_rate(
        self,
        symbol: str,
        limit: int = 1,
    ) -> Dict[str, Any]:
        """
        Fetch funding rate history.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of records
            
        Returns:
            Dict with funding rate data
        """
        try:
            def _fetch():
                return self._client.rest_api.get_funding_rate_history(
                    symbol=symbol,
                    limit=limit,
                )
            
            response = self._retry_request(_fetch)
            data = self._extract_data(response)
            
            if data:
                # Se é uma lista, pegar o primeiro item
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                else:
                    latest = data
                
                result = {
                    'funding_rate': float(getattr(latest, 'funding_rate', 0)),
                    'funding_time': int(getattr(latest, 'funding_time', 0)),
                    'symbol': getattr(latest, 'symbol', symbol),
                }
                logger.debug(f"Fetched funding rate for {symbol}: {result['funding_rate']}")
                return result
            
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            return {}
    
    def fetch_taker_buy_sell_volume(
        self,
        symbol: str,
        period: str = "4h",
        limit: int = 1,
    ) -> Dict[str, Any]:
        """
        Fetch taker buy/sell volume ratio.
        
        Args:
            symbol: Trading pair symbol
            period: Period ("5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d")
            limit: Number of data points
            
        Returns:
            Dict with taker volume data
            
        Note:
            Using PERIOD_MAP_LS enum for period. If SDK uses different enum for this endpoint,
            this may need to be updated based on SDK documentation.
        """
        # Note: The SDK period enum might be different for this endpoint
        # Using the same mapping as long_short_ratio. Verify with SDK docs if issues occur.
        period_enum = self.PERIOD_MAP_LS.get(period)
        if not period_enum:
            raise ValueError(f"Invalid period: {period}. Must be one of {list(self.PERIOD_MAP_LS.keys())}")
        
        try:
            def _fetch():
                return self._client.rest_api.taker_buy_sell_volume(
                    symbol=symbol,
                    period=period_enum,
                    limit=limit,
                )
            
            response = self._retry_request(_fetch)
            data = self._extract_data(response)
            
            if data:
                # Se é uma lista, pegar o primeiro item
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                else:
                    latest = data
                
                result = {
                    'buy_sell_ratio': float(getattr(latest, 'buy_sell_ratio', 0)),
                    'buy_vol': float(getattr(latest, 'buy_vol', 0)),
                    'sell_vol': float(getattr(latest, 'sell_vol', 0)),
                    'timestamp': int(getattr(latest, 'timestamp', 0)),
                }
                logger.debug(f"Fetched taker volume for {symbol}: {result['buy_sell_ratio']}")
                return result
            
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch taker volume for {symbol}: {e}")
            return {}
    
    def fetch_all_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch all sentiment data for a symbol.
        
        Consolidates data from multiple endpoints with individual error handling.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Consolidated sentiment data dictionary
        """
        result = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'symbol': symbol,
        }
        
        # Long/Short Ratio
        try:
            ls_data = self.fetch_long_short_ratio(symbol, period="4h")
            result.update({
                'long_short_ratio': ls_data.get('long_short_ratio'),
                'long_account': ls_data.get('long_account'),
                'short_account': ls_data.get('short_account'),
            })
        except Exception as e:
            logger.warning(f"Could not fetch long/short ratio for {symbol}: {e}")
            result.update({
                'long_short_ratio': None,
                'long_account': None,
                'short_account': None,
            })
        
        # Top Trader Ratio
        try:
            top_trader_data = self.fetch_top_trader_ls_ratio(symbol, period="4h")
            result.update({
                'top_long_short_ratio': top_trader_data.get('top_long_short_ratio'),
                'top_long_account': top_trader_data.get('top_long_account'),
                'top_short_account': top_trader_data.get('top_short_account'),
            })
        except Exception as e:
            logger.warning(f"Could not fetch top trader ratio for {symbol}: {e}")
            result.update({
                'top_long_short_ratio': None,
                'top_long_account': None,
                'top_short_account': None,
            })
        
        # Open Interest
        try:
            oi_data = self.fetch_open_interest(symbol)
            result['open_interest'] = oi_data.get('open_interest')
        except Exception as e:
            logger.warning(f"Could not fetch open interest for {symbol}: {e}")
            result['open_interest'] = None
        
        # Funding Rate
        try:
            funding_data = self.fetch_funding_rate(symbol)
            result.update({
                'funding_rate': funding_data.get('funding_rate'),
                'funding_time': funding_data.get('funding_time'),
            })
        except Exception as e:
            logger.warning(f"Could not fetch funding rate for {symbol}: {e}")
            result.update({
                'funding_rate': None,
                'funding_time': None,
            })
        
        # Taker Buy/Sell Volume
        try:
            taker_data = self.fetch_taker_buy_sell_volume(symbol, period="4h")
            result.update({
                'buy_sell_ratio': taker_data.get('buy_sell_ratio'),
                'buy_vol': taker_data.get('buy_vol'),
                'sell_vol': taker_data.get('sell_vol'),
            })
        except Exception as e:
            logger.warning(f"Could not fetch taker volume for {symbol}: {e}")
            result.update({
                'buy_sell_ratio': None,
                'buy_vol': None,
                'sell_vol': None,
            })
        
        logger.info(f"Collected all sentiment data for {symbol}")
        return result
