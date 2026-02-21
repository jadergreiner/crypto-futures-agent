#!/usr/bin/env python3
"""Check Binance SDK available methods for conditional orders."""

# Just import and list methods
from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import (
    DerivativesTradingUsdsFutures,
    ConfigurationRestAPI,
    ConfigurationWebSocketAPI,
    ConfigurationWebSocketStreams,
)

# Create minimal config
config_rest = ConfigurationRestAPI(api_key="test", api_secret="test")
config_ws_api = ConfigurationWebSocketAPI(api_key="test", api_secret="test", stream_url="ws://test")
config_ws_streams = ConfigurationWebSocketStreams(stream_url="ws://test")

# Create client
client = DerivativesTradingUsdsFutures(
    config_rest_api=config_rest,
    config_ws_api=config_ws_api,
    config_ws_streams=config_ws_streams,
)

# Get REST API
rest_api = client.rest_api

print("=" * 80)
print("Available REST API Methods:")
print("=" * 80)

# Filter for relevant methods
relevant_methods = [m for m in dir(rest_api) if not m.startswith('_')]

for method_name in sorted(relevant_methods):
    if any(keyword in method_name.lower() for keyword in ['order', 'market', 'stop', 'condition']):
        print(f"  ✓ {method_name}")

print("\n" + "=" * 80)
print("ALL available methods:")
print("=" * 80)
for method_name in sorted(relevant_methods):
    print(f"  • {method_name}")

print("\n\nDone!")

