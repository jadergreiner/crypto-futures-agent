import os
import time
from dotenv import load_dotenv
from pathlib import Path

from binance_common.configuration import ConfigurationRestAPI
from binance_sdk_derivatives_trading_usds_futures.rest_api.rest_api import DerivativesTradingUsdsFuturesRestAPI

from core.model2.repository import Model2ThesisRepository
from core.model2.live_exchange import Model2LiveExchange

# Load .env
env_path = Path('.env')
load_dotenv(dotenv_path=env_path)
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
BASE_PATH = os.getenv('BINANCE_BASE_PATH') or 'https://fapi.binance.com'

if not API_KEY or not API_SECRET:
    raise SystemExit('API credentials not found in .env')

config = ConfigurationRestAPI(api_key=API_KEY, api_secret=API_SECRET, base_path=BASE_PATH, timeout=120000, retries=2, backoff=1000)
rest_api = DerivativesTradingUsdsFuturesRestAPI(config)
client = type('C', (), {'rest_api': rest_api})()
exchange = Model2LiveExchange(client, recv_window=60_000)

repo = Model2ThesisRepository(db_path='db/modelo2.db')
execution_id = 15
execution = repo.get_signal_execution(execution_id)
if not execution:
    print('execution not found')
    raise SystemExit(1)

symbol = execution.get('symbol')
exchange_order_id = execution.get('exchange_order_id')
client_order_id = execution.get('client_order_id')

print('execution:', execution_id, 'symbol:', symbol, 'exchange_order_id:', exchange_order_id, 'client_order_id:', client_order_id)

results = {}

# Try query_order via adapter
try:
    q = exchange.query_order(symbol=symbol, order_id=exchange_order_id or client_order_id)
    results['query_order'] = q
    print('query_order result:', q)
except Exception as e:
    results['query_order_error'] = str(e)
    print('query_order error:', str(e))

# Try all_orders
try:
    ao = rest_api.all_orders(symbol=symbol, limit=500)
    ao_data = ao.data() if hasattr(ao, 'data') else ao
    results['all_orders'] = ao_data
    print('all_orders count:', len(ao_data) if isinstance(ao_data, list) else 'single')
except Exception as e:
    results['all_orders_error'] = str(e)
    print('all_orders error:', str(e))

# Try account_trade_list (last trades)
try:
    # if we have order id, pass it
    order_id_param = None
    try:
        order_id_param = int(exchange_order_id)
    except Exception:
        order_id_param = None
    at = rest_api.account_trade_list(symbol=symbol, order_id=order_id_param, limit=500)
    at_data = at.data() if hasattr(at, 'data') else at
    results['account_trade_list'] = at_data
    print('account_trade_list count:', len(at_data) if isinstance(at_data, list) else 'single')
except Exception as e:
    results['account_trade_list_error'] = str(e)
    print('account_trade_list error:', str(e))

# Save results to file
import json
out_path = Path('logs')
out_path.mkdir(parents=True, exist_ok=True)
with open(out_path / f'order_trades_{execution_id}_{int(time.time())}.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print('Saved results to logs')
