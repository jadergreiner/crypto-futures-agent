#!/usr/bin/env python3
"""Check new_algo_order signature."""

import inspect
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

# Get new_algo_order method
method = rest_api.new_algo_order

print("=" * 80)
print("new_algo_order() Method Signature and Documentation")
print("=" * 80)

# Get signature
sig = inspect.signature(method)
print(f"\nSignature: new_algo_order{sig}")

# Get docstring
if method.__doc__:
    print(f"\n\nDocumentation:")
    print(method.__doc__)
else:
    print("\nNo docstring available")

print("\n\n" + "=" * 80)
print("Parameters:")
print("=" * 80)
for param_name, param in sig.parameters.items():
    if param_name not in ['self']:
        default = f" = {param.default}" if param.default != inspect.Parameter.empty else ""
        annotation = f": {param.annotation}" if param.annotation != inspect.Parameter.empty else ""
        print(f"  {param_name}{annotation}{default}")

print("\n\nDone!")
