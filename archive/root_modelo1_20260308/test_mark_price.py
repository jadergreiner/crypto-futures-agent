#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from data.binance_client import BinanceClientFactory
import json

factory = BinanceClientFactory(mode='live')
client = factory.create_client()

print("Testing mark_price API...")
result = client.rest_api.mark_price(symbol='ANKRUSDT')

print(f"\nType: {type(result)}")

# Try data()
price_data = result.data()
print(f"\ndata() result type: {type(price_data)}")
print(f"data() result: {price_data}")

# Try actual_instance
if hasattr(result, 'actual_instance'):
    actual = result.actual_instance
    print(f"\nactual_instance type: {type(actual)}")
    print(f"actual_instance: {actual}")
    if hasattr(actual, 'mark_price'):
        print(f"actual_instance.mark_price: {actual.mark_price}")

# Try to access mark_price directly from data()
if hasattr(price_data, 'mark_price'):
    print(f"\ndata().mark_price: {price_data.mark_price}")
if hasattr(price_data, 'markPrice'):
    print(f"\ndata().markPrice: {price_data.markPrice}")

# Print all attributes
print(f"\nAll attributes of data():")
for attr in sorted(dir(price_data)):
    if not attr.startswith('_'):
        try:
            val = getattr(price_data, attr)
            if not callable(val):
                print(f"  {attr}: {val}")
        except:
            pass


