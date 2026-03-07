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
                    (used for other operations, not for sentiment data)
        """
        # Main client (for trading operations in whatever mode)
        self._client = client
        
        # Data client (ALWAYS production for reading market data)
        # Even in paper trading mode, we read real data from production
        from data.binance_client import create_data_client
        self._data_client = create_data_client()
        
        self._api_diagnostic_logged = False
        # Track endpoints that are unavailable (not supported in testnet, etc)
        self._disabled_endpoints = set()  # Set[str] - endpoint names to skip
        logger.info("SentimentCollector initialized with dual clients:")
        logger.info("  - Main client for trading operations")
        logger.info("  - Data client for market data (always production)")

    def _retry_request(self, func, *args, endpoint_name: str = None, **kwargs):
        """
        Execute request with retry logic and exponential backoff.

        Defensive against JSON parsing errors from SDK when API returns
        empty responses or invalid JSON.

        Args:
            func: Function to call
            endpoint_name: Name of endpoint (for tracking disabled endpoints)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result on success, or None on persistent API failures
        """
        # Check if endpoint is disabled (not supported in this mode)
        if endpoint_name and endpoint_name in self._disabled_endpoints:
            logger.debug(f"[ENDPOINT DISABLED] Skipping {endpoint_name} - not supported in this mode")
            return None
        
        last_error = None
        empty_response_count = 0

        for attempt in range(API_MAX_RETRIES):
            try:
                result = func(*args, **kwargs)

                # Check if response is empty (indicates endpoint may not be supported)
                is_empty = False
                if result is None:
                    is_empty = True
                elif hasattr(result, 'data'):
                    raw_data = result.data
                    if callable(raw_data):
                        raw_data = raw_data()
                    logger.debug(f"[DEBUG RESPONSE] Raw response type: {type(raw_data)}, content: {raw_data}")
                    if not raw_data or (isinstance(raw_data, (list, dict)) and len(raw_data) == 0):
                        is_empty = True
                        empty_response_count += 1
                
                # If getting empty responses consistently from an endpoint, disable it
                if is_empty and empty_response_count >= 2 and endpoint_name:
                    logger.warning(
                        f"[ENDPOINT UNSUPPORTED] {endpoint_name} returning empty responses consistently. "
                        f"Disabling endpoint for this session."
                    )
                    self._disabled_endpoints.add(endpoint_name)
                    return None

                # Success - log and return
                if attempt > 0:
                    logger.debug(f"Sentiment request succeeded on retry (attempt {attempt + 1}/{API_MAX_RETRIES})")
                return result
            except Exception as e:
                last_error = e
                error_msg = str(e)

                # Detect JSON parsing errors from SDK
                is_json_error = "Expecting value" in error_msg or "JSON" in error_msg
                is_rate_limit = "429" in error_msg or "rate" in error_msg.lower()

                if attempt < API_MAX_RETRIES - 1:
                    backoff_time = API_RETRY_DELAYS[attempt]

                    # More detailed logging for diagnostics
                    logger.warning(
                        f"Sentiment request failed (attempt {attempt + 1}/{API_MAX_RETRIES}): {error_msg}. "
                        f"Will retry in {backoff_time}s... "
                        f"[JSON error: {is_json_error}, Rate limit: {is_rate_limit}]"
                    )
                    time.sleep(backoff_time)
                else:
                    # Final attempt failed - check if endpoint should be disabled
                    if endpoint_name and is_json_error:
                        logger.warning(
                            f"[ENDPOINT DISABLED] {endpoint_name} consistently returns invalid JSON. "
                            f"Disabling endpoint for this session."
                        )
                        self._disabled_endpoints.add(endpoint_name)
                    
                    logger.error(
                        f"Sentiment request failed after {API_MAX_RETRIES} attempts. "
                        f"Last error: {error_msg}"
                    )

        # Return None on persistent failure - allows graceful degradation
        return None

    def diagnose_api(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Diagnostic method to test sentiment API connectivity and identify issues.

        Attempts each sentiment endpoint individually to identify which are failing.

        Args:
            symbol: Test symbol

        Returns:
            Diagnostic results with status of each endpoint
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'endpoints': {}
        }

        # Test long_short_ratio
        try:
            logger.info(f"[DIAGNOSTIC] Testing long_short_ratio for {symbol}...")
            endpoint_result = self.fetch_long_short_ratio(symbol, period="4h")
            results['endpoints']['long_short_ratio'] = {
                'status': 'success' if endpoint_result else 'empty_response',
                'data': endpoint_result
            }
        except Exception as e:
            results['endpoints']['long_short_ratio'] = {
                'status': 'failure',
                'error': str(e)
            }
            logger.error(f"[DIAGNOSTIC] long_short_ratio failed: {e}")

        # Test open_interest
        try:
            logger.info(f"[DIAGNOSTIC] Testing open_interest for {symbol}...")
            endpoint_result = self.fetch_open_interest(symbol)
            results['endpoints']['open_interest'] = {
                'status': 'success' if endpoint_result else 'empty_response',
                'data': endpoint_result
            }
        except Exception as e:
            results['endpoints']['open_interest'] = {
                'status': 'failure',
                'error': str(e)
            }
            logger.error(f"[DIAGNOSTIC] open_interest failed: {e}")

        # Test funding_rate
        try:
            logger.info(f"[DIAGNOSTIC] Testing funding_rate for {symbol}...")
            endpoint_result = self.fetch_funding_rate(symbol)
            results['endpoints']['funding_rate'] = {
                'status': 'success' if endpoint_result else 'empty_response',
                'data': endpoint_result
            }
        except Exception as e:
            results['endpoints']['funding_rate'] = {
                'status': 'failure',
                'error': str(e)
            }
            logger.error(f"[DIAGNOSTIC] funding_rate failed: {e}")

        # Summary
        success_count = sum(1 for ep in results['endpoints'].values() if ep['status'] == 'success')
        results['summary'] = {
            'working_endpoints': success_count,
            'total_endpoints': len(results['endpoints']),
            'all_ok': success_count == len(results['endpoints'])
        }

        logger.info(f"[DIAGNOSTIC] Results: {success_count}/{len(results['endpoints'])} endpoints working")

        return results

    def _extract_data(self, response):
        """
        Extrai dados do wrapper ApiResponse do SDK e converte SDK objects em dicts.

        Defensive against:
        - None responses (when API calls fail completely)
        - Empty responses from API
        - JSON parsing errors that weren't caught by retry logic

        O SDK Binance retorna objetos com atributos snake_case mas o código pode
        esperar dicts com método .get() e chaves camelCase.

        Esta função:
        1. Extrai .data do ApiResponse wrapper
        2. Converte SDK objects em dicts Python
        3. Mapeia atributos snake_case → camelCase para compatibilidade
        4. Trata listas de SDK objects recursivamente
        """
        if response is None:
            logger.debug("API response was None - API call failed or returned empty result")
            return None

        try:
            # Verificar se é uma string vazia (indica resposta corrupta)
            if isinstance(response, str) and response.strip() == "":
                logger.warning("API returned empty string response (likely 204 No Content)")
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

            # Verificar se data é vazia após extração
            if data is None or (isinstance(data, str) and data.strip() == ""):
                logger.debug("Extracted data from response is None or empty")
                return None

            # Passo 2: Converter SDK objects para dicts
            return self._convert_sdk_object_to_dict(data)

        except (ValueError, TypeError, AttributeError) as e:
            # Catch JSON parsing errors, type errors, or attribute access issues
            logger.warning(f"Error extracting data from response: {e}. Response type: {type(response)}")
            return None
        except Exception as e:
            # Catch any unexpected errors
            logger.warning(f"Unexpected error while extracting sentiment data: {e}")
            return None

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
                logger.debug(f"[SENTIMENT] SDK object convertido para dict: {type(obj).__name__} → {len(camel_dict)} campos")

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
        # Mapeamento explícito dos campos comuns da API Binance
        snake_to_camel = {
            'funding_rate': 'fundingRate',
            'funding_time': 'fundingTime',
            'mark_price': 'markPrice',
            'index_price': 'indexPrice',
            'estimated_settle_price': 'estimatedSettlePrice',
            'last_funding_rate': 'lastFundingRate',
            'next_funding_time': 'nextFundingTime',
            'interest_rate': 'interestRate',
            'open_interest': 'openInterest',
            'open_time': 'openTime',
            'sum_open_interest': 'sumOpenInterest',
            'sum_open_interest_value': 'sumOpenInterestValue',
        }

        result = dict(data)  # Cópia para não modificar original

        # Adicionar versões camelCase das chaves snake_case
        for snake_key, camel_key in snake_to_camel.items():
            if snake_key in result and camel_key not in result:
                result[camel_key] = result[snake_key]

        return result

    def _safe_getattr(self, obj, key, default=0):
        """
        Safely get attribute from dict or object, trying both snake_case and camelCase.

        Args:
            obj: Dict or object with attributes
            key: Key or attribute name (in snake_case)
            default: Default value if key/attr not found

        Returns:
            Value from dict/object, or default if not found
        """
        try:
            if isinstance(obj, dict):
                # Try both snake_case and camelCase versions
                if key in obj:
                    value = obj[key]
                else:
                    # Convert snake_case to camelCase
                    camel_key = self._snake_to_camel(key)
                    value = obj.get(camel_key, default)

                # Handle string values (convert to float if numeric)
                if isinstance(value, str) and value and value[0].isdigit():
                    try:
                        return float(value)
                    except (ValueError, AttributeError):
                        return value
                return value
            else:
                # Try object attribute - both snake_case and camelCase
                if hasattr(obj, key):
                    return getattr(obj, key)
                else:
                    camel_key = self._snake_to_camel(key)
                    return getattr(obj, camel_key, default)
        except (AttributeError, KeyError, TypeError):
            return default

    def _snake_to_camel(self, snake_str: str) -> str:
        """
        Convert snake_case to camelCase.

        Args:
            snake_str: String in snake_case format

        Returns:
            String in camelCase format
        """
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])

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
            Empty dict on failure (logged as warning, never raises)
        """
        period_enum = self.PERIOD_MAP_LS.get(period)
        if not period_enum:
            raise ValueError(f"Invalid period: {period}. Must be one of {list(self.PERIOD_MAP_LS.keys())}")

        try:
            def _fetch():
                return self._data_client.rest_api.long_short_ratio(
                    symbol=symbol,
                    period=period_enum,
                    limit=limit,
                )

            response = self._retry_request(_fetch, endpoint_name="long_short_ratio")

            # Handle None response from _retry_request
            if response is None:
                logger.debug(f"Long/short ratio fetch returned None for {symbol}")
                return {}

            data = self._extract_data(response)

            if data:
                # Se é uma lista, pegar o primeiro item
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                else:
                    latest = data

                result = {
                    'long_short_ratio': float(self._safe_getattr(latest, 'long_short_ratio', 0)),
                    'long_account': float(self._safe_getattr(latest, 'long_account', 0)),
                    'short_account': float(self._safe_getattr(latest, 'short_account', 0)),
                    'timestamp': int(self._safe_getattr(latest, 'timestamp', 0)),
                }
                logger.debug(f"Fetched long/short ratio for {symbol}: {result['long_short_ratio']}")
                return result

            return {}
        except Exception as e:
            logger.warning(f"Failed to fetch long/short ratio for {symbol}: {e}")
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
            Empty dict on failure (logged as warning, never raises)
        """
        period_enum = self.PERIOD_MAP_TOP_TRADER.get(period)
        if not period_enum:
            raise ValueError(f"Invalid period: {period}. Must be one of {list(self.PERIOD_MAP_TOP_TRADER.keys())}")

        try:
            def _fetch():
                return self._data_client.rest_api.top_trader_long_short_ratio_positions(
                    symbol=symbol,
                    period=period_enum,
                    limit=limit,
                )

            response = self._retry_request(_fetch)

            # Handle None response from _retry_request
            if response is None:
                logger.debug(f"Top trader ratio fetch returned None for {symbol}")
                return {}

            data = self._extract_data(response)

            if data:
                # Se é uma lista, pegar o primeiro item
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                else:
                    latest = data

                result = {
                    'top_long_short_ratio': float(self._safe_getattr(latest, 'long_short_ratio', 0)),
                    'top_long_account': float(self._safe_getattr(latest, 'long_account', 0)),
                    'top_short_account': float(self._safe_getattr(latest, 'short_account', 0)),
                    'timestamp': int(self._safe_getattr(latest, 'timestamp', 0)),
                }
                logger.debug(f"Fetched top trader L/S ratio for {symbol}: {result['top_long_short_ratio']}")
                return result

            return {}
        except Exception as e:
            logger.warning(f"Failed to fetch top trader L/S ratio for {symbol}: {e}")
            return {}

    def fetch_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current open interest.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dict with open interest data
            Empty dict on failure (logged as warning, never raises)
        """
        try:
            def _fetch():
                return self._data_client.rest_api.open_interest(symbol=symbol)

            response = self._retry_request(_fetch)

            # Handle None response from _retry_request
            if response is None:
                logger.debug(f"Open interest fetch returned None for {symbol}")
                return {}

            data = self._extract_data(response)

            if data:
                result = {
                    'open_interest': float(self._safe_getattr(data, 'open_interest', 0)),
                    'symbol': self._safe_getattr(data, 'symbol', symbol),
                    'timestamp': int(self._safe_getattr(data, 'time', 0)),
                }
                logger.debug(f"Fetched open interest for {symbol}: {result['open_interest']}")
                return result

            return {}
        except Exception as e:
            logger.warning(f"Failed to fetch open interest for {symbol}: {e}")
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
            Empty dict on failure (logged as warning, never raises)
        """
        try:
            def _fetch():
                return self._data_client.rest_api.get_funding_rate_history(
                    symbol=symbol,
                    limit=limit,
                )

            response = self._retry_request(_fetch)

            # Handle None response from _retry_request
            if response is None:
                logger.debug(f"Funding rate fetch returned None for {symbol}")
                return {}

            data = self._extract_data(response)

            if data:
                # Se é uma lista, pegar o primeiro item
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                else:
                    latest = data

                result = {
                    'funding_rate': float(self._safe_getattr(latest, 'funding_rate', 0)),
                    'funding_time': int(self._safe_getattr(latest, 'funding_time', 0)),
                    'symbol': self._safe_getattr(latest, 'symbol', symbol),
                }
                logger.debug(f"Fetched funding rate for {symbol}: {result['funding_rate']}")
                return result

            return {}
        except Exception as e:
            logger.warning(f"Failed to fetch funding rate for {symbol}: {e}")
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
            Empty dict on failure (logged as warning, never raises)

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
                return self._data_client.rest_api.taker_buy_sell_volume(
                    symbol=symbol,
                    period=period_enum,
                    limit=limit,
                )

            response = self._retry_request(_fetch)

            # Handle None response from _retry_request
            if response is None:
                logger.debug(f"Taker volume fetch returned None for {symbol}")
                return {}

            data = self._extract_data(response)

            if data:
                # Se é uma lista, pegar o primeiro item
                if isinstance(data, list) and len(data) > 0:
                    latest = data[0]
                else:
                    latest = data

                result = {
                    'buy_sell_ratio': float(self._safe_getattr(latest, 'buy_sell_ratio', 0)),
                    'buy_vol': float(self._safe_getattr(latest, 'buy_vol', 0)),
                    'sell_vol': float(self._safe_getattr(latest, 'sell_vol', 0)),
                    'timestamp': int(self._safe_getattr(latest, 'timestamp', 0)),
                }
                logger.debug(f"Fetched taker volume for {symbol}: {result['buy_sell_ratio']}")
                return result

            return {}
        except Exception as e:
            logger.warning(f"Failed to fetch taker volume for {symbol}: {e}")
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
