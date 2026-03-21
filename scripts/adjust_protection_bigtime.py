#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# ensure repo root is on sys.path when running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance_common.configuration import ConfigurationRestAPI
from binance_sdk_derivatives_trading_usds_futures.rest_api.rest_api import DerivativesTradingUsdsFuturesRestAPI

from core.model2.live_exchange import Model2LiveExchange

# Load env
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

symbol = 'BIGTIMEUSDT'

print('Fetching mark price for', symbol)
try:
    mp = client.rest_api.mark_price(symbol=symbol)
    data = None
    try:
        data = mp.data()
    except Exception:
        data = mp
    price = None
    if hasattr(data, 'actual_instance') and data.actual_instance and hasattr(data.actual_instance, 'mark_price'):
        price = float(data.actual_instance.mark_price)
    elif isinstance(data, dict) and 'markPrice' in data:
        price = float(data.get('markPrice'))
    else:
        # try common keys
        price = float(getattr(data, 'markPrice', None) or getattr(data, 'mark_price', None) or 0)
    print('Mark price:', price)
except Exception as e:
    print('Failed to fetch mark price:', e)
    price = None

print('Checking open position')
pos = None
try:
    pos = exchange.get_open_position(symbol)
    print('Open position:', pos)
except Exception as e:
    print('Error fetching position:', e)

if pos is None or price is None:
    print('No position or no price available, aborting')
    raise SystemExit(1)

direction = pos.get('direction')
print('Detected direction:', direction)

# Define candidate multipliers
if direction == 'SHORT':
    sl_multipliers = [1.05, 1.08, 1.10, 1.20]
    tp_multipliers = [0.90, 0.85, 0.80]
else:
    # LONG
    sl_multipliers = [0.95, 0.92, 0.90, 0.85]
    tp_multipliers = [1.10, 1.15, 1.20]

results = {'sl': None, 'tp': None}

# Try SL
for mult in sl_multipliers:
    trigger = round(price * mult, 8)
    print(f'Trying SL trigger {trigger} (mult {mult})')
    try:
        resp = exchange.place_protective_order(symbol=symbol, signal_side=direction, trigger_price=trigger, order_type='STOP_MARKET')
        oid = exchange.extract_order_identifier(resp)
        print('SL placed, id:', oid)
        results['sl'] = {'trigger': trigger, 'id': oid, 'resp': resp}
        break
    except Exception as e:
        text = str(e)
        print('SL attempt failed:', text)
        if 'Order would immediately trigger' in text or 'would immediately trigger' in text:
            # try next multiplier
            time.sleep(0.5)
            continue
        else:
            # other error, record and stop trying
            results['sl'] = {'error': text}
            break

# Try TP
for mult in tp_multipliers:
    trigger = round(price * mult, 8)
    print(f'Trying TP trigger {trigger} (mult {mult})')
    try:
        resp = exchange.place_protective_order(symbol=symbol, signal_side=direction, trigger_price=trigger, order_type='TAKE_PROFIT_MARKET')
        oid = exchange.extract_order_identifier(resp)
        print('TP placed, id:', oid)
        results['tp'] = {'trigger': trigger, 'id': oid, 'resp': resp}
        break
    except Exception as e:
        text = str(e)
        print('TP attempt failed:', text)
        if 'Order would immediately trigger' in text or 'would immediately trigger' in text:
            time.sleep(0.5)
            continue
        else:
            results['tp'] = {'error': text}
            break

print('Final results:', results)

# If placed, show protection state
try:
    state = exchange.get_protection_state(symbol=symbol, signal_side=direction)
    print('Protection state:', state)
except Exception as e:
    print('Error fetching protection state:', e)
