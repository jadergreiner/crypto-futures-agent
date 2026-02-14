"""
WebSocket manager for real-time Binance Futures data streams using official SDK.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime, timedelta
from collections import deque

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import (
    DerivativesTradingUsdsFutures,
)
from config.settings import (
    FLASH_CRASH_THRESHOLD_PCT,
    FLASH_CRASH_WINDOW_MINUTES,
    LIQUIDATION_ALERT_MULTIPLIER,
)
from config.symbols import ALL_SYMBOLS

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections to Binance Futures streams using official SDK.
    
    Handles mark price updates, kline data for flash crash detection,
    and liquidation monitoring for cascade detection.
    """

    def __init__(self, client: DerivativesTradingUsdsFutures):
        """
        Initialize WebSocket manager with SDK client.
        
        Args:
            client: Configured DerivativesTradingUsdsFutures client
        """
        self._client = client
        self._connection = None
        self._active_streams: List[str] = []
        
        # State management
        self._mark_prices: Dict[str, float] = {}
        self._kline_buffer: Dict[str, deque] = {}  # symbol -> deque of last N 1m candles
        self._liquidation_buffer: Dict[str, deque] = {}  # symbol -> 24h liquidations
        
        # Callback registries
        self._on_price_update: List[Callable] = []
        self._on_flash_event: List[Callable] = []
        self._on_liquidation_cascade: List[Callable] = []
        
        logger.info("WebSocketManager initialized with SDK client")

    def register_price_callback(self, callback: Callable) -> None:
        """
        Register callback for price updates (Camada 2).
        
        Args:
            callback: Function to call on price update, signature: callback(symbol: str, price: float)
        """
        self._on_price_update.append(callback)
        logger.info("Registered price update callback")

    def register_flash_event_callback(self, callback: Callable) -> None:
        """
        Register callback for flash crash/pump events.
        
        Args:
            callback: Function to call on flash event, signature: callback(symbol: str, event_type: str, change_pct: float)
        """
        self._on_flash_event.append(callback)
        logger.info("Registered flash event callback")

    def register_liquidation_callback(self, callback: Callable) -> None:
        """
        Register callback for liquidation cascade events.
        
        Args:
            callback: Function to call on liquidation cascade, signature: callback(symbol: str, data: dict)
        """
        self._on_liquidation_cascade.append(callback)
        logger.info("Registered liquidation cascade callback")

    def get_mark_price(self, symbol: str) -> Optional[float]:
        """
        Get current mark price for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Current mark price or None if not available
        """
        return self._mark_prices.get(symbol)

    def get_all_mark_prices(self) -> Dict[str, float]:
        """
        Get all cached mark prices.
        
        Returns:
            Dictionary mapping symbol to mark price
        """
        return self._mark_prices.copy()

    def _handle_mark_price(self, symbol: str, data: Dict[str, Any]) -> None:
        """
        Handle mark price update.
        
        Args:
            symbol: Trading pair symbol
            data: Mark price data from WebSocket
        """
        try:
            # Extract mark price from data
            # Data format: {'s': 'BTCUSDT', 'p': '50000.00', 'E': 1234567890}
            price = float(data.get('p', 0))
            
            if price > 0:
                self._mark_prices[symbol] = price
                
                # Call registered callbacks
                for callback in self._on_price_update:
                    try:
                        callback(symbol, price)
                    except Exception as e:
                        logger.error(f"Error in price update callback: {e}")
        except Exception as e:
            logger.error(f"Error handling mark price for {symbol}: {e}")

    def _handle_kline_1m(self, symbol: str, data: Dict[str, Any]) -> None:
        """
        Handle 1-minute kline update for flash crash detection.
        
        Buffers last N candles and detects >5% price change in 5 minutes.
        
        Args:
            symbol: Trading pair symbol
            data: Kline data from WebSocket
        """
        try:
            kline = data.get('k', {})
            
            # Only process closed candles
            if not kline.get('x', False):
                return
            
            candle_data = {
                'timestamp': kline.get('t', 0),
                'open': float(kline.get('o', 0)),
                'high': float(kline.get('h', 0)),
                'low': float(kline.get('l', 0)),
                'close': float(kline.get('c', 0)),
                'volume': float(kline.get('v', 0)),
            }
            
            # Initialize buffer for symbol if needed
            if symbol not in self._kline_buffer:
                self._kline_buffer[symbol] = deque(maxlen=FLASH_CRASH_WINDOW_MINUTES)
            
            self._kline_buffer[symbol].append(candle_data)
            
            # Check for flash event if we have enough candles
            if len(self._kline_buffer[symbol]) >= FLASH_CRASH_WINDOW_MINUTES:
                self._check_flash_event(symbol)
                
        except Exception as e:
            logger.error(f"Error handling kline for {symbol}: {e}")

    def _check_flash_event(self, symbol: str) -> None:
        """
        Check for flash crash or pump (>5% move in 5 minutes).
        
        Args:
            symbol: Trading pair symbol
        """
        try:
            candles = list(self._kline_buffer[symbol])
            
            if len(candles) < FLASH_CRASH_WINDOW_MINUTES:
                return
            
            start_price = candles[0]['open']
            end_price = candles[-1]['close']
            
            if start_price == 0:
                return
            
            change_pct = (end_price - start_price) / start_price
            
            if abs(change_pct) >= FLASH_CRASH_THRESHOLD_PCT:
                event_type = "FLASH_PUMP" if change_pct > 0 else "FLASH_CRASH"
                
                logger.warning(
                    f"⚠️  {event_type} detected on {symbol}: "
                    f"{abs(change_pct) * 100:.2f}% in {FLASH_CRASH_WINDOW_MINUTES} min"
                )
                
                # Call registered callbacks
                for callback in self._on_flash_event:
                    try:
                        callback(symbol, event_type, abs(change_pct))
                    except Exception as e:
                        logger.error(f"Error in flash event callback: {e}")
        except Exception as e:
            logger.error(f"Error checking flash event for {symbol}: {e}")

    def _handle_liquidation(self, symbol: str, data: Dict[str, Any]) -> None:
        """
        Handle liquidation order stream.
        
        Buffers 24h of liquidations and detects cascades (>2x average volume).
        
        Args:
            symbol: Trading pair symbol
            data: Liquidation data from WebSocket
        """
        try:
            order_data = data.get('o', {})
            
            liq_data = {
                'timestamp': data.get('E', 0),
                'side': order_data.get('S', ''),
                'quantity': float(order_data.get('q', 0)),
                'price': float(order_data.get('p', 0)),
            }
            
            # Initialize buffer for symbol if needed (24h rolling buffer for liquidation events)
            if symbol not in self._liquidation_buffer:
                self._liquidation_buffer[symbol] = deque(maxlen=1440)  # 1440 = 24h assuming ~1 event/min avg
            
            self._liquidation_buffer[symbol].append(liq_data)
            
            # Check for cascade
            self._check_liquidation_cascade(symbol)
            
        except Exception as e:
            logger.error(f"Error handling liquidation for {symbol}: {e}")

    def _check_liquidation_cascade(self, symbol: str) -> None:
        """
        Check for liquidation cascade (recent volume > 2x average).
        
        Args:
            symbol: Trading pair symbol
        """
        try:
            liquidations = list(self._liquidation_buffer.get(symbol, []))
            
            if len(liquidations) < 60:  # Need at least 1 hour of data
                return
            
            # Calculate volumes
            now = datetime.now().timestamp() * 1000
            recent_window = 5 * 60 * 1000  # Last 5 minutes
            
            recent_vol = sum(
                liq['quantity'] for liq in liquidations
                if now - liq['timestamp'] <= recent_window
            )
            
            total_vol = sum(liq['quantity'] for liq in liquidations)
            avg_vol_per_5min = total_vol / (len(liquidations) / 5) if liquidations else 0
            
            if avg_vol_per_5min > 0 and recent_vol > avg_vol_per_5min * LIQUIDATION_ALERT_MULTIPLIER:
                logger.warning(
                    f"⚠️  Liquidation cascade detected on {symbol}: "
                    f"Recent volume {recent_vol:.2f} is {recent_vol / avg_vol_per_5min:.1f}x average"
                )
                
                # Call registered callbacks
                cascade_data = {
                    'recent_volume': recent_vol,
                    'average_volume': avg_vol_per_5min,
                    'multiplier': recent_vol / avg_vol_per_5min,
                }
                
                for callback in self._on_liquidation_cascade:
                    try:
                        callback(symbol, cascade_data)
                    except Exception as e:
                        logger.error(f"Error in liquidation cascade callback: {e}")
        except Exception as e:
            logger.error(f"Error checking liquidation cascade for {symbol}: {e}")

    async def start(self) -> None:
        """
        Start WebSocket connections for all configured symbols.
        
        Subscribes to:
        - Mark price stream (1s updates)
        - Kline 1m stream (for flash detection)
        - Liquidation order stream
        - Global liquidation stream
        """
        try:
            logger.info("Starting WebSocket streams...")
            
            # Create WebSocket connection
            self._connection = await self._client.websocket_streams.create_connection()
            
            # Subscribe to streams for each symbol
            for symbol in ALL_SYMBOLS:
                symbol_lower = symbol.lower()
                
                # Mark price stream
                mark_price_stream = self._connection.mark_price_stream(
                    symbol=symbol_lower,
                    update_speed="1s"
                )
                mark_price_stream.on("message", lambda data, s=symbol: self._handle_mark_price(s, data))
                self._active_streams.append(f"{symbol_lower}@markPrice@1s")
                
                # Kline 1m stream
                kline_stream = self._connection.kline_candlestick_streams(
                    symbol=symbol_lower,
                    interval="1m"
                )
                kline_stream.on("message", lambda data, s=symbol: self._handle_kline_1m(s, data))
                self._active_streams.append(f"{symbol_lower}@kline_1m")
                
                # Liquidation stream for specific symbol
                liq_stream = self._connection.liquidation_order_streams(symbol=symbol_lower)
                liq_stream.on("message", lambda data, s=symbol: self._handle_liquidation(s, data))
                self._active_streams.append(f"{symbol_lower}@forceOrder")
                
                # Small delay between subscriptions to avoid rate limits
                await asyncio.sleep(0.1)
            
            # Subscribe to global liquidation stream
            global_liq_stream = self._connection.all_market_liquidation_order_streams()
            global_liq_stream.on("message", lambda data: self._handle_liquidation("ALL", data))
            self._active_streams.append("!forceOrder@arr")
            
            logger.info(f"WebSocket manager started with {len(self._active_streams)} streams")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket manager: {e}")
            raise

    async def stop(self) -> None:
        """
        Stop WebSocket connections and cleanup.
        """
        try:
            if self._connection:
                # Unsubscribe from all streams
                for stream in self._active_streams:
                    try:
                        # Note: Actual unsubscribe method depends on SDK implementation
                        logger.debug(f"Unsubscribing from {stream}")
                    except Exception as e:
                        logger.warning(f"Error unsubscribing from {stream}: {e}")
                
                # Close connection
                await self._connection.close()
                self._connection = None
                self._active_streams.clear()
                
                logger.info("WebSocket manager stopped")
        except Exception as e:
            logger.error(f"Error stopping WebSocket manager: {e}")

    def is_connected(self) -> bool:
        """
        Check if WebSocket is connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connection is not None
