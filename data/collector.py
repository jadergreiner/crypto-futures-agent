"""
Binance Futures API collector for OHLCV data using official SDK.
"""

from __future__ import annotations

import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import (
    DerivativesTradingUsdsFutures,
)
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    KlineCandlestickDataIntervalEnum,
)
from config.settings import (
    API_MAX_RETRIES,
    API_RETRY_DELAYS,
    TIMEFRAMES,
    HISTORICAL_PERIODS,
)
from config.symbols import ALL_SYMBOLS

logger = logging.getLogger(__name__)


class BinanceCollector:
    """
    Collects OHLCV data from Binance Futures API using official SDK.
    Implements retry logic with exponential backoff.
    """
    
    # Map interval strings to SDK enum values
    INTERVAL_MAP = {
        "1m": KlineCandlestickDataIntervalEnum.INTERVAL_1m,
        "3m": KlineCandlestickDataIntervalEnum.INTERVAL_3m,
        "5m": KlineCandlestickDataIntervalEnum.INTERVAL_5m,
        "15m": KlineCandlestickDataIntervalEnum.INTERVAL_15m,
        "30m": KlineCandlestickDataIntervalEnum.INTERVAL_30m,
        "1h": KlineCandlestickDataIntervalEnum.INTERVAL_1h,
        "2h": KlineCandlestickDataIntervalEnum.INTERVAL_2h,
        "4h": KlineCandlestickDataIntervalEnum.INTERVAL_4h,
        "6h": KlineCandlestickDataIntervalEnum.INTERVAL_6h,
        "8h": KlineCandlestickDataIntervalEnum.INTERVAL_8h,
        "12h": KlineCandlestickDataIntervalEnum.INTERVAL_12h,
        "1d": KlineCandlestickDataIntervalEnum.INTERVAL_1d,
        "3d": KlineCandlestickDataIntervalEnum.INTERVAL_3d,
        "1w": KlineCandlestickDataIntervalEnum.INTERVAL_1w,
        "1M": KlineCandlestickDataIntervalEnum.INTERVAL_1M,
    }
    
    # Interval durations in milliseconds
    INTERVAL_MS = {
        "1m": 60 * 1000,
        "3m": 3 * 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "30m": 30 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "2h": 2 * 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "6h": 6 * 60 * 60 * 1000,
        "8h": 8 * 60 * 60 * 1000,
        "12h": 12 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
        "3d": 3 * 24 * 60 * 60 * 1000,
        "1w": 7 * 24 * 60 * 60 * 1000,
        "1M": 30 * 24 * 60 * 60 * 1000,  # Approximation (may vary by actual month length)
    }
    
    MAX_KLINES_PER_REQUEST = 1000
    
    def __init__(self, client: DerivativesTradingUsdsFutures):
        """
        Initialize Binance collector with SDK client.
        
        Args:
            client: Configured DerivativesTradingUsdsFutures client
        """
        self._client = client
        logger.info("BinanceCollector initialized with SDK client")
    
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
                        f"Request failed (attempt {attempt + 1}/{API_MAX_RETRIES}): {e}. "
                        f"Retrying in {backoff_time}s..."
                    )
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Request failed after {API_MAX_RETRIES} attempts: {e}")
                    raise
    
    def _extract_data(self, response):
        """
        Extrai dados do wrapper ApiResponse do SDK e converte SDK objects em dicts.
        
        O SDK Binance retorna objetos com atributos snake_case mas o código pode
        esperar dicts com método .get() e chaves camelCase.
        
        Esta função:
        1. Extrai .data do ApiResponse wrapper
        2. Converte SDK objects em dicts Python
        3. Mapeia atributos snake_case → camelCase para compatibilidade
        4. Trata listas de SDK objects recursivamente
        """
        if response is None:
            return None
        
        # Passo 1: ApiResponse tem um atributo .data contendo o payload real
        if hasattr(response, 'data'):
            data = response.data
            # .data pode ser um método que precisa ser chamado
            if callable(data):
                data = data()
        else:
            # Se não tem .data, assumir que já são os dados diretos
            data = response
        
        # Passo 2: Converter SDK objects para dicts
        return self._convert_sdk_object_to_dict(data)
    
    def _convert_sdk_object_to_dict(self, obj):
        """
        Converte objetos SDK da Binance em dicts Python com mapeamento snake_case → camelCase.
        
        Args:
            obj: Pode ser None, dict, list, ou SDK object com atributos
            
        Returns:
            Dict, list de dicts, ou valor primitivo
        """
        if obj is None:
            return None
        
        # Se já é dict ou tipo primitivo, retornar como está
        if isinstance(obj, (dict, str, int, float, bool, bytes, type(None))):
            return obj
        
        # Se é lista, processar cada elemento recursivamente
        if isinstance(obj, list):
            return [self._convert_sdk_object_to_dict(item) for item in obj]
        
        # Se é um SDK object (tem __dict__ mas não é dict), converter para dict
        if hasattr(obj, '__dict__'):
            # Extrair atributos, filtrando os privados (começam com _)
            raw_dict = {
                key: value for key, value in vars(obj).items()
                if not key.startswith('_')
            }
            
            # Converter valores aninhados recursivamente
            converted_dict = {
                key: self._convert_sdk_object_to_dict(value)
                for key, value in raw_dict.items()
            }
            
            # Mapear snake_case → camelCase para compatibilidade com código existente
            camel_dict = self._map_to_camel_case(converted_dict)
            
            # Log para debug
            if converted_dict:  # Só logar se não for vazio
                logger.debug(f"[COLLECTOR] SDK object convertido para dict: {type(obj).__name__} → {len(camel_dict)} campos")
            
            return camel_dict
        
        # Fallback: retornar o objeto como está
        return obj
    
    def _map_to_camel_case(self, data: dict) -> dict:
        """
        Mapeia chaves snake_case para camelCase mantendo ambas as versões.
        
        Mantemos tanto snake_case quanto camelCase para máxima compatibilidade.
        
        Args:
            data: Dict com chaves em snake_case
            
        Returns:
            Dict com chaves adicionais em camelCase
        """
        # Mapeamento de campos relevantes para klines/candlestick data
        snake_to_camel = {
            'open_time': 'openTime',
            'close_time': 'closeTime',
            'quote_volume': 'quoteVolume',
            'taker_buy_base_volume': 'takerBuyBaseVolume',
            'taker_buy_quote_volume': 'takerBuyQuoteVolume',
        }
        
        result = dict(data)  # Cópia para não modificar original
        
        # Adicionar versões camelCase das chaves snake_case
        for snake_key, camel_key in snake_to_camel.items():
            if snake_key in result and camel_key not in result:
                result[camel_key] = result[snake_key]
        
        return result
    
    def fetch_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Fetch kline/candlestick data from Binance using SDK.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            interval: Kline interval ("1h", "4h", "1d")
            limit: Number of klines to fetch (max 1000)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            DataFrame with columns: timestamp, symbol, open, high, low, close, 
                                   volume, quote_volume, trades_count
        """
        # Map interval string to enum
        interval_enum = self.INTERVAL_MAP.get(interval)
        if not interval_enum:
            raise ValueError(f"Invalid interval: {interval}. Must be one of {list(self.INTERVAL_MAP.keys())}")
        
        # Limit to max per request
        limit = min(limit, self.MAX_KLINES_PER_REQUEST)
        
        def _fetch():
            response = self._client.rest_api.kline_candlestick_data(
                symbol=symbol,
                interval=interval_enum,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )
            
            # Log rate limits if available
            if hasattr(response, 'rate_limits'):
                logger.debug(f"Rate limits: {response.rate_limits}")
            
            return response
        
        response = self._retry_request(_fetch)
        raw_data = self._extract_data(response)
        df = self._parse_klines(raw_data, symbol)
        
        logger.debug(f"Fetched {len(df)} {interval} candles for {symbol}")
        return df
    
    def _parse_klines(self, raw_data: Any, symbol: str) -> pd.DataFrame:
        """
        Parse klines data from SDK response to DataFrame.
        
        Supports both Pydantic model objects and raw arrays.
        
        Args:
            raw_data: Response from SDK (list of klines)
            symbol: Trading pair symbol
            
        Returns:
            Parsed DataFrame
        """
        if not raw_data:
            return pd.DataFrame(columns=[
                'timestamp', 'symbol', 'open', 'high', 'low', 'close',
                'volume', 'quote_volume', 'trades_count'
            ])
        
        parsed_data = []
        
        for kline in raw_data:
            # Check if it's a Pydantic model or raw array
            if hasattr(kline, 'open_time'):
                # Pydantic model
                parsed_data.append({
                    'timestamp': kline.open_time,
                    'symbol': symbol,
                    'open': float(kline.open),
                    'high': float(kline.high),
                    'low': float(kline.low),
                    'close': float(kline.close),
                    'volume': float(kline.volume),
                    'quote_volume': float(kline.quote_asset_volume),
                    'trades_count': int(kline.number_of_trades),
                })
            else:
                # Raw array format [timestamp, open, high, low, close, volume, ...]
                parsed_data.append({
                    'timestamp': kline[0],
                    'symbol': symbol,
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'quote_volume': float(kline[7]) if len(kline) > 7 else 0.0,
                    'trades_count': int(kline[8]) if len(kline) > 8 else 0,
                })
        
        df = pd.DataFrame(parsed_data)
        
        # Sort by timestamp
        if not df.empty:
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def fetch_historical(
        self,
        symbol: str,
        interval: str,
        days: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical data with automatic pagination.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval ("1h", "4h", "1d")
            days: Number of days to fetch. If None, uses HISTORICAL_PERIODS defaults.
            
        Returns:
            DataFrame with historical OHLCV data
        """
        # Determine days based on interval if not specified
        if days is None:
            # Map interval to timeframe key in HISTORICAL_PERIODS
            interval_to_key = {
                "1d": "D1",
                "4h": "H4",
                "1h": "H1",
            }
            key = interval_to_key.get(interval, "H1")
            days = HISTORICAL_PERIODS.get(key, 90)
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_dfs = []
        current_start = start_time
        
        logger.debug(f"Fetching {days} days of {interval} data for {symbol}")
        
        while current_start < end_time:
            chunk_df = self.fetch_klines(
                symbol,
                interval,
                limit=self.MAX_KLINES_PER_REQUEST,
                start_time=current_start,
                end_time=end_time,
            )
            
            if chunk_df.empty:
                break
            
            all_dfs.append(chunk_df)
            
            # Update start time for next iteration (add 1ms to last timestamp)
            current_start = int(chunk_df['timestamp'].iloc[-1]) + 1
            
            # Rate limiting between paginated requests
            time.sleep(0.2)
        
        if not all_dfs:
            logger.warning(f"No historical data fetched for {symbol} {interval}")
            return pd.DataFrame(columns=[
                'timestamp', 'symbol', 'open', 'high', 'low', 'close',
                'volume', 'quote_volume', 'trades_count'
            ])
        
        # Concatenate all chunks
        df = pd.concat(all_dfs, ignore_index=True)
        
        # Remove duplicates and sort
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        logger.debug(f"Fetched {len(df)} {interval} candles for {symbol}")
        return df
    
    def fetch_all_symbols(
        self,
        interval: str,
        limit: int = 500,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for all configured symbols.
        
        Args:
            interval: Kline interval
            limit: Number of klines per symbol
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        result = {}
        
        for symbol in ALL_SYMBOLS:
            try:
                df = self.fetch_klines(symbol, interval, limit)
                result[symbol] = df
                
                # Rate limiting between symbols
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {e}")
                result[symbol] = pd.DataFrame()
        
        logger.info(f"Fetched data for {len(result)} symbols")
        return result
    
    def validate_data(
        self,
        df: pd.DataFrame,
        interval: str,
    ) -> tuple[bool, list[str]]:
        """
        Validate OHLCV data for integrity issues.
        
        NEVER interpolates missing data - only reports issues.
        
        Args:
            df: DataFrame to validate
            interval: Interval string for gap detection
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        if df.empty:
            issues.append("DataFrame is empty")
            return False, issues
        
        # Check for null values
        null_cols = df.columns[df.isnull().any()].tolist()
        if null_cols:
            issues.append(f"Null values found in columns: {null_cols}")
        
        # Check for negative values in price/volume columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
        for col in numeric_cols:
            if col in df.columns:
                if (df[col] < 0).any():
                    issues.append(f"Negative values found in {col}")
        
        # Check for timestamp gaps
        if len(df) > 1:
            expected_diff_ms = self.INTERVAL_MS.get(interval)
            
            if expected_diff_ms:
                df_sorted = df.sort_values('timestamp')
                timestamps = df_sorted['timestamp'].values
                diffs = timestamps[1:] - timestamps[:-1]
                
                # Allow 50% tolerance for gaps
                max_allowed_diff = expected_diff_ms * 1.5
                gaps = diffs > max_allowed_diff
                
                if gaps.any():
                    gap_count = gaps.sum()
                    issues.append(
                        f"Found {gap_count} timestamp gaps (>{max_allowed_diff}ms) in {interval} data"
                    )
        
        is_valid = len(issues) == 0
        
        if issues:
            logger.warning(f"Data validation issues: {', '.join(issues)}")
        else:
            logger.debug("Data validation passed")
        
        return is_valid, issues
