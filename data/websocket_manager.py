"""
WebSocket manager for real-time Binance Futures data streams.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime, timedelta
import websockets
from config.settings import (
    BINANCE_WS_URL, WS_RECONNECT_BACKOFF, WS_MAX_RECONNECT_DELAY,
    FLASH_CRASH_THRESHOLD_PCT, FLASH_CRASH_WINDOW_MINUTES
)

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections to Binance Futures streams.
    Handles mark price, liquidations, and 1-minute candles for multiple symbols.
    """
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self.base_url = BINANCE_WS_URL
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.callbacks: Dict[str, List[Callable]] = {
            'mark_price': [],
            'force_order': [],
            'kline_1m': []
        }
        self.running = False
        self.reconnect_delay = WS_RECONNECT_BACKOFF[0]
        self.m1_candles: Dict[str, List[Dict[str, Any]]] = {}  # Buffer for flash crash detection
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register a callback for specific event type.
        
        Args:
            event_type: "mark_price", "force_order", or "kline_1m"
            callback: Function to call when event occurs
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.info(f"Registered callback for {event_type}")
        else:
            logger.warning(f"Unknown event type: {event_type}")
    
    async def _connect_stream(self, stream_name: str) -> None:
        """
        Connect to a specific stream with auto-reconnect.
        
        Args:
            stream_name: WebSocket stream name
        """
        url = f"{self.base_url}{stream_name}"
        
        while self.running:
            try:
                async with websockets.connect(url) as websocket:
                    logger.info(f"Connected to {stream_name}")
                    self.reconnect_delay = WS_RECONNECT_BACKOFF[0]  # Reset on successful connection
                    
                    async for message in websocket:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            await self._handle_message(stream_name, data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse message: {e}")
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket error on {stream_name}: {e}")
                if self.running:
                    await self._handle_reconnect()
            except Exception as e:
                logger.error(f"Unexpected error on {stream_name}: {e}")
                if self.running:
                    await self._handle_reconnect()
    
    async def _handle_reconnect(self) -> None:
        """Handle reconnection with exponential backoff."""
        await asyncio.sleep(self.reconnect_delay)
        
        # Exponential backoff
        idx = WS_RECONNECT_BACKOFF.index(self.reconnect_delay) if self.reconnect_delay in WS_RECONNECT_BACKOFF else -1
        if idx >= 0 and idx < len(WS_RECONNECT_BACKOFF) - 1:
            self.reconnect_delay = WS_RECONNECT_BACKOFF[idx + 1]
        else:
            self.reconnect_delay = min(self.reconnect_delay * 2, WS_MAX_RECONNECT_DELAY)
        
        logger.info(f"Attempting reconnect in {self.reconnect_delay}s...")
    
    async def _handle_message(self, stream_name: str, data: Dict[str, Any]) -> None:
        """
        Route message to appropriate handler.
        
        Args:
            stream_name: Stream name that generated the message
            data: Message data
        """
        if '@markPrice' in stream_name:
            await self._handle_mark_price(data)
        elif '@forceOrder' in stream_name:
            await self._handle_force_order(data)
        elif '@kline_1m' in stream_name:
            await self._handle_kline_1m(data)
    
    async def _handle_mark_price(self, data: Dict[str, Any]) -> None:
        """Handle mark price updates."""
        try:
            symbol = data.get('s', '')
            price = float(data.get('p', 0))
            
            # Call registered callbacks
            for callback in self.callbacks['mark_price']:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(symbol, price)
                    else:
                        callback(symbol, price)
                except Exception as e:
                    logger.error(f"Error in mark_price callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling mark price: {e}")
    
    async def _handle_force_order(self, data: Dict[str, Any]) -> None:
        """Handle liquidation orders."""
        try:
            order_data = data.get('o', {})
            symbol = order_data.get('s', '')
            side = order_data.get('S', '')
            quantity = float(order_data.get('q', 0))
            price = float(order_data.get('p', 0))
            
            liq_info = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'timestamp': data.get('E', 0)
            }
            
            # Call registered callbacks
            for callback in self.callbacks['force_order']:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(symbol, liq_info)
                    else:
                        callback(symbol, liq_info)
                except Exception as e:
                    logger.error(f"Error in force_order callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling force order: {e}")
    
    async def _handle_kline_1m(self, data: Dict[str, Any]) -> None:
        """Handle 1-minute kline updates for flash crash detection."""
        try:
            kline = data.get('k', {})
            symbol = kline.get('s', '')
            
            if kline.get('x', False):  # Candle closed
                candle_data = {
                    'symbol': symbol,
                    'timestamp': kline.get('t', 0),
                    'open': float(kline.get('o', 0)),
                    'high': float(kline.get('h', 0)),
                    'low': float(kline.get('l', 0)),
                    'close': float(kline.get('c', 0)),
                    'volume': float(kline.get('v', 0))
                }
                
                # Buffer for flash crash detection
                if symbol not in self.m1_candles:
                    self.m1_candles[symbol] = []
                
                self.m1_candles[symbol].append(candle_data)
                
                # Keep only last window
                max_candles = FLASH_CRASH_WINDOW_MINUTES
                if len(self.m1_candles[symbol]) > max_candles:
                    self.m1_candles[symbol] = self.m1_candles[symbol][-max_candles:]
                
                # Check for flash crash/pump
                self._check_flash_event(symbol)
                
                # Call registered callbacks
                for callback in self.callbacks['kline_1m']:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(symbol, candle_data)
                        else:
                            callback(symbol, candle_data)
                    except Exception as e:
                        logger.error(f"Error in kline_1m callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error handling kline_1m: {e}")
    
    def _check_flash_event(self, symbol: str) -> None:
        """
        Check for flash crash or pump (>5% move in 5 minutes).
        
        Args:
            symbol: Trading pair symbol
        """
        if symbol not in self.m1_candles or len(self.m1_candles[symbol]) < FLASH_CRASH_WINDOW_MINUTES:
            return
        
        candles = self.m1_candles[symbol]
        start_price = candles[0]['open']
        end_price = candles[-1]['close']
        
        if start_price == 0:
            return
        
        change_pct = abs((end_price - start_price) / start_price)
        
        if change_pct >= FLASH_CRASH_THRESHOLD_PCT:
            direction = "PUMP" if end_price > start_price else "CRASH"
            logger.warning(f"⚠️  Flash {direction} detected on {symbol}: {change_pct*100:.2f}% in {FLASH_CRASH_WINDOW_MINUTES} min")
            
            # Could trigger alert here
    
    def subscribe_symbol(self, symbol: str) -> List[str]:
        """
        Generate stream names for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            List of stream names
        """
        symbol_lower = symbol.lower()
        return [
            f"{symbol_lower}@markPrice@1s",
            f"{symbol_lower}@forceOrder",
            f"{symbol_lower}@kline_1m"
        ]
    
    async def subscribe_all(self, symbols: List[str]) -> None:
        """
        Subscribe to all streams for multiple symbols.
        
        Args:
            symbols: List of trading pair symbols
        """
        self.running = True
        
        # Combine all streams
        all_streams = []
        for symbol in symbols:
            all_streams.extend(self.subscribe_symbol(symbol))
        
        # Create combined stream URL
        combined_stream = '/'.join(all_streams)
        
        # Start connection task
        logger.info(f"Starting WebSocket for {len(symbols)} symbols...")
        await self._connect_stream(combined_stream)
    
    async def start(self, symbols: List[str]) -> None:
        """
        Start WebSocket manager.
        
        Args:
            symbols: List of trading pair symbols
        """
        await self.subscribe_all(symbols)
    
    def stop(self) -> None:
        """Stop WebSocket manager."""
        self.running = False
        logger.info("WebSocket manager stopped")
