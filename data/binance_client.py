"""
Binance USDS-M Futures client factory using official SDK.
"""

from __future__ import annotations

import os
import logging
from typing import Optional
from pathlib import Path

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import (
    DerivativesTradingUsdsFutures,
    ConfigurationRestAPI,
    ConfigurationWebSocketAPI,
    ConfigurationWebSocketStreams,
    DERIVATIVES_TRADING_USDS_FUTURES_REST_API_PROD_URL,
    DERIVATIVES_TRADING_USDS_FUTURES_WS_API_PROD_URL,
    DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_PROD_URL,
)
from config.settings import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    BINANCE_PRIVATE_KEY_PATH,
    BINANCE_PRIVATE_KEY_PASSPHRASE,
    BINANCE_TESTNET_REST_URL,
    BINANCE_TESTNET_WS_URL,
    TRADING_MODE,
)

logger = logging.getLogger(__name__)


class BinanceClientFactory:
    """
    Factory for creating Binance USDS-M Futures client instances.
    
    Supports both HMAC (api_key + api_secret) and Ed25519 (private_key) authentication.
    Automatically configures testnet URLs for paper trading mode.
    """

    def __init__(self, mode: Optional[str] = None):
        """
        Initialize the client factory.
        
        Args:
            mode: Trading mode - "paper" for testnet, "live" for production.
                  If None, uses TRADING_MODE from settings.
        """
        self.mode = mode or TRADING_MODE
        self.api_key = BINANCE_API_KEY
        self.api_secret = BINANCE_API_SECRET
        self.private_key_path = BINANCE_PRIVATE_KEY_PATH
        self.private_key_passphrase = BINANCE_PRIVATE_KEY_PASSPHRASE
        
        logger.info(f"Initializing Binance client factory in {self.mode} mode")

    def _get_rest_url(self) -> str:
        """
        Get REST API URL based on trading mode.
        
        Returns:
            REST API base URL
        """
        if self.mode == "paper":
            return BINANCE_TESTNET_REST_URL
        return DERIVATIVES_TRADING_USDS_FUTURES_REST_API_PROD_URL

    def _get_ws_api_url(self) -> str:
        """
        Get WebSocket API URL based on trading mode.
        
        Returns:
            WebSocket API URL
        """
        if self.mode == "paper":
            return BINANCE_TESTNET_WS_URL
        return DERIVATIVES_TRADING_USDS_FUTURES_WS_API_PROD_URL

    def _get_ws_streams_url(self) -> str:
        """
        Get WebSocket Streams URL based on trading mode.
        
        Returns:
            WebSocket Streams URL
        """
        if self.mode == "paper":
            return BINANCE_TESTNET_WS_URL
        return DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_PROD_URL

    def _use_ed25519_auth(self) -> bool:
        """
        Check if Ed25519 authentication should be used.
        
        Returns:
            True if private key file exists and path is configured
        """
        if not self.private_key_path:
            return False
        
        key_path = Path(self.private_key_path)
        if key_path.exists():
            logger.info("Using Ed25519 authentication with private key")
            return True
        
        logger.warning(f"Private key path configured but file not found: {self.private_key_path}")
        return False

    def create_client(self) -> DerivativesTradingUsdsFutures:
        """
        Create and configure a Binance USDS-M Futures client.
        
        Returns:
            Configured DerivativesTradingUsdsFutures client instance
        
        Raises:
            ValueError: If neither HMAC nor Ed25519 credentials are properly configured
        """
        rest_url = self._get_rest_url()
        ws_api_url = self._get_ws_api_url()
        ws_streams_url = self._get_ws_streams_url()

        # Configure REST API
        if self._use_ed25519_auth():
            config_rest_api = ConfigurationRestAPI(
                api_key=self.api_key,
                private_key=self.private_key_path,
                private_key_pass=self.private_key_passphrase if self.private_key_passphrase else None,
                base_path=rest_url,
            )
            logger.info("Configured REST API with Ed25519 authentication")
        else:
            if not self.api_key or not self.api_secret:
                raise ValueError(
                    "Either provide BINANCE_API_KEY + BINANCE_API_SECRET for HMAC auth, "
                    "or BINANCE_PRIVATE_KEY_PATH for Ed25519 auth"
                )
            
            config_rest_api = ConfigurationRestAPI(
                api_key=self.api_key,
                api_secret=self.api_secret,
                base_path=rest_url,
            )
            logger.info("Configured REST API with HMAC authentication")

        # Configure WebSocket API
        config_ws_api = ConfigurationWebSocketAPI(
            api_key=self.api_key,
            api_secret=self.api_secret,
            stream_url=ws_api_url,
        )
        logger.info(f"Configured WebSocket API: {ws_api_url}")

        # Configure WebSocket Streams
        config_ws_streams = ConfigurationWebSocketStreams(
            stream_url=ws_streams_url,
        )
        logger.info(f"Configured WebSocket Streams: {ws_streams_url}")

        # Create client
        client = DerivativesTradingUsdsFutures(
            config_rest_api=config_rest_api,
            config_ws_api=config_ws_api,
            config_ws_streams=config_ws_streams,
        )
        
        logger.info(f"Binance client created successfully in {self.mode} mode")
        return client


def create_binance_client(mode: Optional[str] = None) -> DerivativesTradingUsdsFutures:
    """
    Helper function to create a Binance USDS-M Futures client.
    
    Args:
        mode: Trading mode - "paper" for testnet, "live" for production.
              If None, uses TRADING_MODE from settings.
    
    Returns:
        Configured DerivativesTradingUsdsFutures client instance
    
    Example:
        >>> client = create_binance_client("paper")
        >>> # Use client.rest_api, client.websocket_api, or client.websocket_streams
    """
    factory = BinanceClientFactory(mode=mode)
    return factory.create_client()
