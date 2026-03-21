#!/usr/bin/env python3
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# ensure repo root on path
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

if not API_KEY or not API_SECRET:
    raise SystemExit('API credentials not found in .env')

config = ConfigurationRestAPI(api_key=API_KEY, api_secret=API_SECRET, base_path=BASE_PATH)
rest_api = DerivativesTradingUsdsFuturesRestAPI(config)
client = type('C', (), {'rest_api': rest_api})()
exchange = Model2LiveExchange(client)

order_ids = [5685734068, 5685734948, 5685734974]
symbol = 'BIGTIMEUSDT'

out = {
    'timestamp': int(time.time()*1000),
    'symbol': symbol,
    'orders': {},
    'open_orders': None,
    'position': None,
    'protection_state': None,
}

for oid in order_ids:
    try:
        o = exchange.query_order(symbol=symbol, order_id=oid)
        out['orders'][str(oid)] = o
    except Exception as e:
        out['orders'][str(oid)] = {'error': str(e)}

try:
    out['open_orders'] = exchange._list_open_standard_orders(symbol)
except Exception as e:
    out['open_orders'] = {'error': str(e)}

try:
    out['position'] = exchange.get_open_position(symbol)
except Exception as e:
    out['position'] = {'error': str(e)}

try:
    out['protection_state'] = exchange.get_protection_state(symbol=symbol, signal_side=(out['position'] or {}).get('direction') or 'SHORT')
except Exception as e:
    out['protection_state'] = {'error': str(e)}

logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)
file_path = logs_dir / f'audit_bigtime_{int(time.time())}.json'
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print('Audit written to', file_path)
