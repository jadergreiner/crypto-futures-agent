#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# add repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance_common.configuration import ConfigurationRestAPI
from binance_sdk_derivatives_trading_usds_futures.rest_api.rest_api import DerivativesTradingUsdsFuturesRestAPI
from core.model2.live_exchange import Model2LiveExchange

# load env
env_path = Path('.env')
if not env_path.exists():
    raise SystemExit('.env not found')
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
BASE_PATH = os.getenv('BINANCE_BASE_PATH') or 'https://fapi.binance.com'

config = ConfigurationRestAPI(api_key=API_KEY, api_secret=API_SECRET, base_path=BASE_PATH)
rest_api = DerivativesTradingUsdsFuturesRestAPI(config)
client = type('C', (), {'rest_api': rest_api})()
exchange = Model2LiveExchange(client)

symbol = 'BIGTIMEUSDT'
print('--- Adapter list_open_positions ---')
try:
    pos_list = exchange.list_open_positions(symbol)
    print(pos_list)
except Exception as e:
    print('Adapter error:', e)

print('\n--- Adapter get_open_position ---')
try:
    pos = exchange.get_open_position(symbol)
    print(pos)
except Exception as e:
    print('get_open_position error:', e)

print('\n--- Raw REST position_information_v2 ---')
try:
    resp = client.rest_api.position_information_v2(symbol=symbol)
    try:
        data = resp.data()
    except Exception:
        data = resp
    print(data)
except Exception as e:
    print('REST error:', e)

print('\n--- Raw account positions list (no symbol) ---')
try:
    resp_all = client.rest_api.position_information_v2()
    try:
        data_all = resp_all.data()
    except Exception:
        data_all = resp_all
    print(type(data_all))
    # print only entries with non-zero position_amt-like fields
    for item in (data_all or []):
        try:
            print(item)
        except Exception:
            pass
except Exception as e:
    print('REST all error:', e)
