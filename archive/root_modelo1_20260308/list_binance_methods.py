#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.binance_client import BinanceClientFactory

factory = BinanceClientFactory(mode="live")
client = factory.create_client()

# Ver métodos disponíveis
rest_api_methods = [method for method in dir(client.rest_api) if not method.startswith('_')]
print("Métodos disponíveis em REST API:")
for method in sorted(rest_api_methods):
    print(f"  • {method}")
