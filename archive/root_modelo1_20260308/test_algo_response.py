#!/usr/bin/env python3
"""Test new_algo_order response structure."""

from binance_sdk_derivatives_trading_usds_futures.rest_api.models import NewAlgoOrderResponse

# Get fields
print("=" * 80)
print("NewAlgoOrderResponse Fields (from model_fields):")
print("=" * 80)

for field_name, field_info in NewAlgoOrderResponse.model_fields.items():
    print(f"  • {field_name}: {field_info.annotation}")

print("\n\nDone!")
